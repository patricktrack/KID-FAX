#!/usr/bin/env python3
"""Poll Telegram for inbound messages and print them."""
from __future__ import annotations

import datetime as dt
from io import BytesIO
import json
import logging
import os
import requests
import textwrap
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from PIL import Image

from kidfax.avatar_manager import ensure_avatar_dir, get_avatar_path, _process_image
from kidfax.eink_display import init_display, render_polling_status
from kidfax.printer import get_printer

LOG = logging.getLogger("kidfax.telegram")

DEFAULT_STATE_FILE = Path.home() / ".kidfax_state.json"
ENCODING = os.getenv("PRINTER_ENCODING", "cp437")
LINE_WIDTH = int(os.getenv("PRINTER_LINE_WIDTH", "32"))
ALLOW_DUMMY = os.getenv("ALLOW_DUMMY_PRINTER", "false").lower() in {"1", "true", "yes"}


def _required_env(name: str) -> str:
    """Get required environment variable."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required")
    return value


def _parse_contact_map(raw: str) -> Dict[str, int]:
    """Parse CONTACTS env var into name->chat_id mapping."""
    contacts: Dict[str, int] = {}
    for chunk in raw.split(','):
        if ':' not in chunk:
            continue
        name, chat_id = chunk.split(':', 1)
        name = name.strip()
        chat_id = chat_id.strip()
        if name and chat_id:
            try:
                contacts[name] = int(chat_id)
            except ValueError:
                LOG.warning(f"Invalid chat ID for {name}: {chat_id}")
    return contacts


# Telegram-specific configuration
BOT_TOKEN = _required_env("TELEGRAM_BOT_TOKEN")
POLL_TIMEOUT = int(os.getenv("TELEGRAM_POLL_TIMEOUT", "30"))
DOWNLOAD_PHOTOS = os.getenv("TELEGRAM_DOWNLOAD_PHOTOS", "true").lower() in {"1", "true", "yes"}
MAX_PHOTO_SIZE = int(os.getenv("TELEGRAM_MAX_PHOTO_SIZE", "5")) * 1024 * 1024  # MB to bytes

CONTACTS = _parse_contact_map(os.getenv("CONTACTS", ""))
ALLOWLIST = {int(item.strip()) for item in os.getenv("ALLOWLIST", "").split(',') if item.strip().isdigit()}
STATE_FILE = Path(os.getenv("KIDFAX_STATE_FILE", DEFAULT_STATE_FILE))
MAX_STATE = int(os.getenv("KIDFAX_STATE_LIMIT", "5000"))
HEADER_TEXT = os.getenv("KIDFAX_HEADER", "Kid Fax")


def _contact_label(chat_id: int) -> str:
    """Convert chat ID to human-readable label."""
    for name, stored_id in CONTACTS.items():
        if stored_id == chat_id:
            return f"{name} ({chat_id})"
    return str(chat_id)


def _extract_contact_name(chat_id: int) -> Optional[str]:
    """Extract contact name from chat ID."""
    for name, stored_id in CONTACTS.items():
        if stored_id == chat_id:
            return name
    return None


def _wrap_text(value: str) -> List[str]:
    """Wrap text to printer line width."""
    lines: List[str] = []
    for para in value.splitlines() or [""]:
        wrapped = textwrap.wrap(para, width=LINE_WIDTH) or [""]
        lines.extend(wrapped)
    return lines


def _sanitize(value: str) -> str:
    """Sanitize text for printer encoding."""
    return value.encode(ENCODING, "ignore").decode(ENCODING)


def _load_state() -> tuple[List[int], Set[int]]:
    """Load seen update IDs from state file."""
    if not STATE_FILE.exists():
        return [], set()
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        order = data.get("seen_update_ids", [])
        return list(order), set(order)
    except Exception as exc:
        LOG.warning("Could not read state file (%s), starting fresh", exc)
        return [], set()


def _save_state(order: List[int]) -> None:
    """Save seen update IDs to state file."""
    payload = {"seen_update_ids": order[-MAX_STATE:]}
    STATE_FILE.write_text(json.dumps(payload), encoding="utf-8")


def _get_updates(bot_token: str, offset: Optional[int] = None, timeout: int = 30) -> List[Dict[str, Any]]:
    """Poll Telegram for new updates (messages)."""
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    params = {
        'offset': offset,
        'timeout': timeout,
        'allowed_updates': ['message']  # Only messages, not other update types
    }
    try:
        resp = requests.get(url, params=params, timeout=timeout + 5)
        resp.raise_for_status()
        data = resp.json()
        if not data.get('ok'):
            LOG.warning(f"Telegram API error: {data}")
            return []
        return data.get('result', [])
    except Exception as exc:
        LOG.warning(f"Failed to get updates: {exc}")
        return []


def _download_photo(bot_token: str, file_id: str) -> Optional[Image.Image]:
    """Download photo from Telegram and return PIL Image."""
    try:
        # Step 1: Get file path
        url = f"https://api.telegram.org/bot{bot_token}/getFile"
        resp = requests.get(url, params={'file_id': file_id})
        resp.raise_for_status()
        data = resp.json()
        if not data.get('ok'):
            return None

        file_path = data['result']['file_path']
        file_size = data['result'].get('file_size', 0)

        # Check size limit
        if file_size > MAX_PHOTO_SIZE:
            LOG.warning(f"Photo too large: {file_size} bytes (max {MAX_PHOTO_SIZE})")
            return None

        # Step 2: Download file
        file_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
        resp = requests.get(file_url, timeout=30)
        resp.raise_for_status()

        # Step 3: Convert to PIL Image
        img = Image.open(BytesIO(resp.content))
        return img
    except Exception as exc:
        LOG.warning(f"Failed to download photo: {exc}")
        return None


def _extract_message_data(update: Dict) -> Optional[Dict]:
    """Extract relevant message data from Telegram update."""
    if 'message' not in update:
        return None

    msg = update['message']
    chat_id = msg['chat']['id']
    update_id = update['update_id']

    # Extract text
    text = msg.get('text', msg.get('caption', ''))

    # Extract photo (if present)
    photo = None
    if 'photo' in msg:
        # Telegram sends multiple photo sizes, get largest
        photos = msg['photo']
        largest = max(photos, key=lambda p: p.get('file_size', 0))
        photo = largest['file_id']

    return {
        'update_id': update_id,
        'chat_id': chat_id,
        'text': text,
        'photo': photo,
        'sender_name': msg['chat'].get('first_name', 'Unknown')
    }


def _print_telegram_message(printer: object, sender_label: str, text: str, photo: Optional[Image.Image] = None) -> None:
    """Print Telegram message with optional photo."""
    # 1. Header
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    printer.set(align='center', font='a', width=2, height=2, bold=True)
    printer.text(f"{HEADER_TEXT}\n")

    printer.set(align='center', font='a', width=1, height=1, bold=False)
    printer.text(f"{now}\n")
    printer.text("-" * LINE_WIDTH + "\n")

    # 2. Avatar (existing contact avatar system)
    avatar_enabled = os.getenv("AVATAR_ENABLED", "true").lower() in {"1", "true", "yes"}
    if avatar_enabled:
        # Extract chat_id from sender_label (format: "name (chat_id)")
        chat_id_str = sender_label.split('(')[-1].rstrip(')')
        try:
            chat_id = int(chat_id_str)
            contact_name = _extract_contact_name(chat_id)
            if contact_name:
                avatar_path = get_avatar_path(contact_name)
                if avatar_path and avatar_path.exists():
                    try:
                        img = Image.open(avatar_path)
                        printer.set(align='center')
                        printer.text("\n")
                        printer.image(img)
                        printer.text("\n")
                    except Exception as exc:
                        LOG.warning(f"Failed to print avatar: {exc}")
        except ValueError:
            pass

    # 3. Sender name
    printer.set(align='left', font='a', width=1, height=1, bold=True)
    printer.text(f"From: {sender_label}\n\n")

    # 4. Message text
    if text:
        printer.set(align='left', font='a', width=1, height=1, bold=False)
        for line in _wrap_text(_sanitize(text)):
            printer.text(line + "\n")
        printer.text("\n")

    # 5. Photo (if present) - REUSE AVATAR PROCESSING
    if photo:
        try:
            processed = _process_image(
                photo,
                target_size=int(os.getenv("AVATAR_SIZE", "96"))
            )
            printer.set(align='center')
            printer.text("\n")
            printer.image(processed)
            printer.text("\n")
        except Exception as exc:
            LOG.warning(f"Failed to print photo: {exc}")

    # 6. Footer
    printer.text("\n")
    try:
        printer.cut()
    except Exception:
        printer.text("\n\n\n")


def poll_loop() -> None:
    """Main polling loop for Telegram updates."""
    bot_token = _required_env("TELEGRAM_BOT_TOKEN")

    logging.basicConfig(
        level=os.getenv("KIDFAX_LOG_LEVEL", "INFO").upper(),
        format="[%(asctime)s] %(levelname)s: %(message)s",
    )

    seen_order, seen = _load_state()
    last_sender: Optional[str] = None
    last_update_id: Optional[int] = None

    LOG.info("Kid Fax Telegram poller started (long polling, timeout=%ss)", POLL_TIMEOUT)

    # Initialize avatar directory
    ensure_avatar_dir()

    # Initialize e-ink display
    epd = init_display()

    printer = None
    while True:
        try:
            if printer is None:
                printer = get_printer(allow_dummy=ALLOW_DUMMY)
                if printer is None:
                    LOG.error("Printer is not available. Retrying in 10 seconds...")
                    time.sleep(10)
                    continue

            # Get new updates
            offset = last_update_id + 1 if last_update_id else None
            updates = _get_updates(bot_token, offset=offset, timeout=POLL_TIMEOUT)

            printed_now = 0
            state_dirty = False

            for update in updates:
                update_id = update['update_id']
                last_update_id = update_id  # Track for offset

                if update_id in seen:
                    continue

                msg_data = _extract_message_data(update)
                if not msg_data:
                    seen.add(update_id)
                    seen_order.append(update_id)
                    state_dirty = True
                    continue

                chat_id = msg_data['chat_id']

                # Check allowlist
                if ALLOWLIST and chat_id not in ALLOWLIST:
                    LOG.info("Ignoring message from chat_id %s (not in allowlist)", chat_id)
                    seen.add(update_id)
                    seen_order.append(update_id)
                    state_dirty = True
                    continue

                # Resolve sender label
                sender_label = _contact_label(chat_id)

                # Download photo if present
                photo_img = None
                if DOWNLOAD_PHOTOS and msg_data['photo']:
                    photo_img = _download_photo(bot_token, msg_data['photo'])

                # Print message
                _print_telegram_message(
                    printer,
                    sender_label,
                    msg_data['text'],
                    photo=photo_img
                )

                LOG.info("Printed message from %s", sender_label)
                seen.add(update_id)
                seen_order.append(update_id)
                printed_now += 1
                last_sender = sender_label
                state_dirty = True

            # Update e-ink display
            if printed_now:
                render_polling_status(epd, printed_now, last_sender)

            # Save state
            if state_dirty:
                overflow = len(seen_order) - MAX_STATE
                if overflow > 0:
                    for _ in range(overflow):
                        oldest = seen_order.pop(0)
                        seen.discard(oldest)
                _save_state(seen_order)

        except Exception as exc:
            LOG.warning("Polling error: %s", exc)
            printer = None
        finally:
            try:
                # No explicit sleep needed - long polling handles timing
                pass
            except KeyboardInterrupt:
                LOG.info("Stopping Kid Fax Telegram poller")
                _save_state(seen_order)
                return


def main() -> None:
    """Main entry point."""
    try:
        poll_loop()
    except KeyboardInterrupt:
        LOG.info("Stopping Kid Fax Telegram poller")


if __name__ == "__main__":
    main()
