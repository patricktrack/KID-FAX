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

from PIL import Image, ImageDraw, ImageFont

from kidfax.avatar_manager import ensure_avatar_dir, get_avatar_path, _process_image
from kidfax.eink_display import init_display, render_polling_status
from kidfax.printer import get_printer

LOG = logging.getLogger("kidfax.telegram")

DEFAULT_STATE_FILE = Path.home() / ".kidfax_state.json"
ENCODING = os.getenv("PRINTER_ENCODING", "cp437")
LINE_WIDTH = int(os.getenv("PRINTER_LINE_WIDTH", "32"))
ALLOW_DUMMY = os.getenv("ALLOW_DUMMY_PRINTER", "false").lower() in {"1", "true", "yes"}



# Conversation tracking - show kid's message if family responds within 10 min
SENT_MESSAGES_FILE = Path.home() / ".kidfax_sent_messages.json"
CONVERSATION_WINDOW_MINUTES = 10

def _get_recent_sent_message(chat_id: int) -> Optional[tuple]:
    """Get sent message to this chat_id if within conversation window.
    
    Returns:
        Tuple of (message_text, timestamp_str) or None
    """
    try:
        if not SENT_MESSAGES_FILE.exists():
            return None
        
        with open(SENT_MESSAGES_FILE, 'r') as f:
            data = json.load(f)
        
        chat_data = data.get(str(chat_id))
        if not chat_data:
            return None
        
        sent_time = dt.datetime.fromisoformat(chat_data['timestamp'])
        now = dt.datetime.now()
        diff = (now - sent_time).total_seconds() / 60
        
        if diff <= CONVERSATION_WINDOW_MINUTES:
            # Clear this entry so it doesn't print again
            del data[str(chat_id)]
            with open(SENT_MESSAGES_FILE, 'w') as f:
                json.dump(data, f)
            
            return (chat_data['message'], sent_time.strftime("%m/%d/%y %I:%M %p"))
        
        return None
    except Exception as exc:
        LOG.debug(f"Error getting sent message: {exc}")
        return None

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


def _create_speech_bubble(text: str, max_width: int = 360, timestamp: str = None) -> Image.Image:
    """
    Create a speech bubble image with the message text inside.
    Bubble width adapts to text length. Left-justified, no tail.

    Args:
        text: Message text to display
        max_width: Maximum width in pixels (thermal printer width)
        timestamp: Optional timestamp to display below bubble (left-aligned with bubble)

    Returns:
        PIL Image with speech bubble
    """
    # Settings - LARGER text
    padding = 16
    corner_radius = 18
    line_height = 28
    font_size = 20
    timestamp_font_size = 14
    min_bubble_width = 80  # Minimum width for short messages

    # Try to load a font, fall back to default
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        timestamp_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", timestamp_font_size)
    except (IOError, OSError):
        try:
            font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans.ttf", font_size)
            timestamp_font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans.ttf", timestamp_font_size)
        except (IOError, OSError):
            font = ImageFont.load_default()
            timestamp_font = ImageFont.load_default()

    # Calculate available width for text
    max_text_width = max_width - (padding * 2) - 10

    # Wrap text to fit
    chars_per_line = max_text_width // 11  # Approximate chars for larger font
    wrapped_lines = []
    for paragraph in text.split('\n'):
        if paragraph.strip():
            wrapped_lines.extend(textwrap.wrap(paragraph, width=chars_per_line))
        else:
            wrapped_lines.append('')

    if not wrapped_lines:
        wrapped_lines = ['']

    # Measure actual text width for responsive bubble
    max_line_width = 0
    for line in wrapped_lines:
        try:
            bbox = font.getbbox(line)
            line_width = bbox[2] - bbox[0]
        except AttributeError:
            # Fallback for older PIL
            line_width = len(line) * 11
        max_line_width = max(max_line_width, line_width)

    # Calculate responsive bubble width
    content_width = max_line_width + (padding * 2)
    bubble_width = max(min_bubble_width, min(content_width, max_width - 4))

    # Calculate bubble dimensions
    text_height = len(wrapped_lines) * line_height
    bubble_height = text_height + (padding * 2)
    total_width = bubble_width + 4
    timestamp_height = 24 if timestamp else 0
    total_height = bubble_height + 4 + timestamp_height

    # Create image (white background)
    img = Image.new('1', (total_width, total_height), 1)  # 1-bit, white
    draw = ImageDraw.Draw(img)

    # Bubble position (left-justified, no tail offset)
    bx = 2
    by = 2
    bw = bubble_width
    bh = bubble_height

    # Draw rounded rectangle outline
    # Top edge
    draw.line([(bx + corner_radius, by), (bx + bw - corner_radius, by)], fill=0, width=2)
    # Bottom edge
    draw.line([(bx + corner_radius, by + bh), (bx + bw - corner_radius, by + bh)], fill=0, width=2)
    # Left edge
    draw.line([(bx, by + corner_radius), (bx, by + bh - corner_radius)], fill=0, width=2)
    # Right edge
    draw.line([(bx + bw, by + corner_radius), (bx + bw, by + bh - corner_radius)], fill=0, width=2)

    # Corners (quarter circles as arcs)
    draw.arc([(bx, by), (bx + corner_radius*2, by + corner_radius*2)], 180, 270, fill=0, width=2)
    draw.arc([(bx + bw - corner_radius*2, by), (bx + bw, by + corner_radius*2)], 270, 360, fill=0, width=2)
    draw.arc([(bx, by + bh - corner_radius*2), (bx + corner_radius*2, by + bh)], 90, 180, fill=0, width=2)
    draw.arc([(bx + bw - corner_radius*2, by + bh - corner_radius*2), (bx + bw, by + bh)], 0, 90, fill=0, width=2)

    # Draw text inside bubble
    text_x = bx + padding
    text_y = by + padding
    for i, line in enumerate(wrapped_lines):
        draw.text((text_x, text_y + i * line_height), line, font=font, fill=0)

    # Draw timestamp below bubble, aligned with left edge
    if timestamp:
        draw.text((bx, by + bh + 6), timestamp, font=timestamp_font, fill=0)

    return img



def _create_speech_bubble_right(text: str, max_width: int = 360, timestamp: str = None) -> Image.Image:
    """Create a RIGHT-justified speech bubble for sent messages."""
    padding = 16
    corner_radius = 18
    line_height = 28
    font_size = 20
    timestamp_font_size = 14
    min_bubble_width = 80

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        timestamp_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", timestamp_font_size)
    except (IOError, OSError):
        font = ImageFont.load_default()
        timestamp_font = ImageFont.load_default()

    max_text_width = max_width - (padding * 2) - 10
    chars_per_line = max_text_width // 11
    wrapped_lines = []
    for paragraph in text.split('\n'):
        if paragraph.strip():
            wrapped_lines.extend(textwrap.wrap(paragraph, width=chars_per_line))
        else:
            wrapped_lines.append('')
    if not wrapped_lines:
        wrapped_lines = ['']

    max_line_width = 0
    for line in wrapped_lines:
        try:
            bbox = font.getbbox(line)
            line_width = bbox[2] - bbox[0]
        except AttributeError:
            line_width = len(line) * 11
        max_line_width = max(max_line_width, line_width)

    content_width = max_line_width + (padding * 2)
    bubble_width = max(min_bubble_width, min(content_width, max_width - 4))
    text_height = len(wrapped_lines) * line_height
    bubble_height = text_height + (padding * 2)
    total_width = max_width
    timestamp_height = 24 if timestamp else 0
    total_height = bubble_height + 4 + timestamp_height

    img = Image.new('1', (total_width, total_height), 1)
    draw = ImageDraw.Draw(img)

    # Right-justify: bubble starts from right edge
    bx = total_width - bubble_width - 2
    by = 2
    bw = bubble_width
    bh = bubble_height

    # Draw rounded rectangle
    draw.line([(bx + corner_radius, by), (bx + bw - corner_radius, by)], fill=0, width=2)
    draw.line([(bx + corner_radius, by + bh), (bx + bw - corner_radius, by + bh)], fill=0, width=2)
    draw.line([(bx, by + corner_radius), (bx, by + bh - corner_radius)], fill=0, width=2)
    draw.line([(bx + bw, by + corner_radius), (bx + bw, by + bh - corner_radius)], fill=0, width=2)

    draw.arc([(bx, by), (bx + corner_radius*2, by + corner_radius*2)], 180, 270, fill=0, width=2)
    draw.arc([(bx + bw - corner_radius*2, by), (bx + bw, by + corner_radius*2)], 270, 360, fill=0, width=2)
    draw.arc([(bx, by + bh - corner_radius*2), (bx + corner_radius*2, by + bh)], 90, 180, fill=0, width=2)
    draw.arc([(bx + bw - corner_radius*2, by + bh - corner_radius*2), (bx + bw, by + bh)], 0, 90, fill=0, width=2)

    text_x = bx + padding
    text_y = by + padding
    for i, line in enumerate(wrapped_lines):
        draw.text((text_x, text_y + i * line_height), line, font=font, fill=0)

    # Draw timestamp below bubble, aligned with right edge of bubble
    if timestamp:
        try:
            ts_bbox = timestamp_font.getbbox(timestamp)
            ts_width = ts_bbox[2] - ts_bbox[0]
        except AttributeError:
            ts_width = len(timestamp) * 8
        # Right-align timestamp with bubble's right edge
        ts_x = bx + bw - ts_width
        draw.text((ts_x, by + bh + 6), timestamp, font=timestamp_font, fill=0)

    return img


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


def _create_avatar_header(avatar_path: Path, display_name: str, max_width: int = 360) -> Image.Image:
    """Create header image with avatar on left and name next to it."""
    avatar_size = 96
    padding = 8

    # Load font for name
    try:
        name_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    except (IOError, OSError):
        name_font = ImageFont.load_default()

    # Load avatar
    try:
        avatar = Image.open(avatar_path)
        if avatar.size != (avatar_size, avatar_size):
            avatar = avatar.resize((avatar_size, avatar_size))
        # Convert to 1-bit for thermal printer
        if avatar.mode != '1':
            avatar = avatar.convert('L').point(lambda x: 0 if x < 128 else 255, '1')
    except Exception:
        # Create placeholder
        avatar = Image.new('1', (avatar_size, avatar_size), 1)
        draw = ImageDraw.Draw(avatar)
        draw.rectangle([(0, 0), (avatar_size-1, avatar_size-1)], outline=0)

    # Calculate total dimensions
    total_height = avatar_size + padding
    total_width = max_width

    # Create image
    img = Image.new('1', (total_width, total_height), 1)

    # Paste avatar on left
    img.paste(avatar, (padding, 0))

    # Draw name next to avatar
    draw = ImageDraw.Draw(img)
    name_x = avatar_size + padding * 3
    name_y = (avatar_size - 24) // 2  # Center vertically
    draw.text((name_x, name_y), display_name, font=name_font, fill=0)

    return img


def _print_telegram_message(printer: object, sender_label: str, text: str, photo: Optional[Image.Image] = None) -> None:
    """Print Telegram message with optional photo."""
    # 1. Extract contact info
    avatar_enabled = os.getenv("AVATAR_ENABLED", "true").lower() in {"1", "true", "yes"}
    contact_name = None
    chat_id = None

    chat_id_str = sender_label.split('(')[-1].rstrip(')')
    try:
        chat_id = int(chat_id_str)
        contact_name = _extract_contact_name(chat_id)
    except ValueError:
        pass

    display_name = contact_name.title() if contact_name else sender_label.split('(')[0].strip()

    # Check for recent sent message (conversation mode)
    recent_sent = _get_recent_sent_message(chat_id) if chat_id else None

    if recent_sent:
        # Print kid's message first (right-justified bubble with timestamp)
        sent_text, sent_time = recent_sent
        try:
            sent_bubble = _create_speech_bubble_right(_sanitize(sent_text), timestamp=sent_time)
            printer.set(align='left')  # Image handles right-justification internally
            printer.image(sent_bubble)
            printer.text("\n")
        except Exception as exc:
            LOG.warning(f"Failed to print sent bubble: {exc}")
            printer.set(align='right', font='a', width=1, height=1, bold=False)
            printer.text(f"{sent_text}\n")
            printer.set(align='right', font='b', width=1, height=1, bold=False)
            printer.text(f"{sent_time}  \n\n")

    # 2. Avatar + Name header (left-justified, side by side)
    if avatar_enabled and contact_name:
        avatar_path = get_avatar_path(contact_name)
        if avatar_path and avatar_path.exists():
            try:
                header_img = _create_avatar_header(avatar_path, display_name)
                printer.set(align='left')
                printer.image(header_img)
            except Exception as exc:
                LOG.warning(f"Failed to print avatar header: {exc}")
                printer.set(align='left', font='a', width=1, height=1, bold=True)
                printer.text(f"{display_name}\n\n")
        else:
            printer.set(align='left', font='a', width=1, height=1, bold=True)
            printer.text(f"{display_name}\n\n")
    else:
        printer.set(align='left', font='a', width=1, height=1, bold=True)
        printer.text(f"{display_name}\n\n")

    # 3. Message text in speech bubble with timestamp (left-justified)
    now = dt.datetime.now().strftime("%m/%d/%y %I:%M %p")
    if text:
        try:
            bubble_img = _create_speech_bubble(_sanitize(text), timestamp=now)
            printer.set(align='left')
            printer.image(bubble_img)
        except Exception as exc:
            LOG.warning(f"Speech bubble failed, using plain text: {exc}")
            printer.set(align='left', font='a', width=1, height=1, bold=False)
            for line in _wrap_text(_sanitize(text)):
                printer.text(line + "\n")
            printer.set(align='left', font='b', width=1, height=1, bold=False)
            printer.text(f"{now}\n")

    # 6. Photo (if present)
    if photo:
        try:
            processed = _process_image(
                photo,
                target_size=int(os.getenv("AVATAR_SIZE", "96"))
            )
            printer.set(align='center')
            printer.text("\n")
            printer.image(processed)
        except Exception as exc:
            LOG.warning(f"Failed to print photo: {exc}")

    # 7. Footer
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
