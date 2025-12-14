#!/usr/bin/env python3
"""Poll Twilio for inbound SMS messages and print them."""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import textwrap
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

from twilio.rest import Client

from kidfax.printer import get_printer
from kidfax.eink_display import init_display, render_polling_status

LOG = logging.getLogger("kidfax.sms")

DEFAULT_STATE_FILE = Path.home() / ".kidfax_state.json"
ENCODING = os.getenv("PRINTER_ENCODING", "cp437")
LINE_WIDTH = int(os.getenv("PRINTER_LINE_WIDTH", "32"))
ALLOW_DUMMY = os.getenv("ALLOW_DUMMY_PRINTER", "false").lower() in {"1", "true", "yes"}


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required")
    return value


def _parse_contact_map(raw: str) -> Dict[str, str]:
    contacts: Dict[str, str] = {}
    for chunk in raw.split(','):
        if ':' not in chunk:
            continue
        name, number = chunk.split(':', 1)
        name = name.strip()
        number = number.strip()
        if name and number:
            contacts[name] = number
    return contacts


CONTACTS = _parse_contact_map(os.getenv("CONTACTS", ""))
ALLOWLIST = {item.strip() for item in os.getenv("ALLOWLIST", "").split(',') if item.strip()}
STATE_FILE = Path(os.getenv("KIDFAX_STATE_FILE", DEFAULT_STATE_FILE))
MAX_STATE = int(os.getenv("KIDFAX_STATE_LIMIT", "5000"))
FETCH_LIMIT = int(os.getenv("TWILIO_FETCH_LIMIT", "40"))
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "15"))
HEADER_TEXT = os.getenv("KIDFAX_HEADER", "Kid Fax")
SUBTITLE_TEXT = os.getenv("KIDFAX_SUBTITLE", "Messages from family")


def _contact_label(number: str) -> str:
    for name, stored in CONTACTS.items():
        if stored == number:
            return f"{name} ({number})"
    return number


def _wrap_text(value: str) -> List[str]:
    lines: List[str] = []
    for para in value.splitlines() or [""]:
        wrapped = textwrap.wrap(para, width=LINE_WIDTH) or [""]
        lines.extend(wrapped)
    return lines


def _sanitize(value: str) -> str:
    return value.encode(ENCODING, "ignore").decode(ENCODING)


def _load_state() -> tuple[List[str], Set[str]]:
    if not STATE_FILE.exists():
        return [], set()
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        order = data.get("seen_sids", [])
        return list(order), set(order)
    except Exception as exc:
        LOG.warning("Could not read state file (%s), starting fresh", exc)
        return [], set()


def _save_state(order: List[str]) -> None:
    payload = {"seen_sids": order[-MAX_STATE:]}
    STATE_FILE.write_text(json.dumps(payload), encoding="utf-8")


def _print_message(printer: object, sender: str, body: str) -> None:
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    printer.set(align='center', font='a', width=2, height=2, bold=True)
    printer.text(f"{HEADER_TEXT}\n")

    printer.set(align='center', font='a', width=1, height=1, bold=False)
    printer.text(f"{now}\n")
    printer.text("-" * LINE_WIDTH + "\n")

    printer.set(align='left', font='a', width=1, height=1, bold=True)
    printer.text(f"From: {_contact_label(sender)}\n\n")

    printer.set(align='left', font='a', width=1, height=1, bold=False)
    for line in _wrap_text(_sanitize(body)):
        printer.text(line + "\n")

    printer.text("\n")
    try:
        printer.cut()
    except Exception:
        printer.text("\n\n\n")


def _fetch_messages(client: Client, target: str, seen: Set[str]) -> List[object]:
    messages = client.messages.list(to=target, limit=FETCH_LIMIT)
    unread = []
    for msg in reversed(messages):
        if msg.sid in seen:
            continue
        direction = getattr(msg, "direction", "") or ""
        if not direction.startswith("inbound"):
            continue
        unread.append(msg)
    return unread


def _should_print(sender: str) -> bool:
    if not ALLOWLIST:
        return True
    return sender in ALLOWLIST


def poll_loop() -> None:
    account_sid = _required_env("TWILIO_ACCOUNT_SID")
    auth_token = _required_env("TWILIO_AUTH_TOKEN")
    twilio_number = _required_env("TWILIO_NUMBER")

    logging.basicConfig(
        level=os.getenv("KIDFAX_LOG_LEVEL", "INFO").upper(),
        format="[%(asctime)s] %(levelname)s: %(message)s",
    )

    client = Client(account_sid, auth_token)
    seen_order, seen = _load_state()
    last_sender: Optional[str] = None

    LOG.info("Kid Fax SMS poller started (polling every %ss)", POLL_SECONDS)

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

            new_messages = _fetch_messages(client, twilio_number, seen)
            printed_now = 0
            state_dirty = False
            for message in new_messages:
                sender = message.from_ or "Unknown"
                if not _should_print(sender):
                    LOG.info("Ignoring message from %s (not in allowlist)", sender)
                    seen.add(message.sid)
                    seen_order.append(message.sid)
                    state_dirty = True
                    continue

                body = message.body or ""
                _print_message(printer, sender, body)
                LOG.info("Printed message from %s", sender)
                seen.add(message.sid)
                seen_order.append(message.sid)
                printed_now += 1
                last_sender = _contact_label(sender)
                state_dirty = True

            if printed_now:
                render_polling_status(epd, printed_now, last_sender)
            if state_dirty:
                overflow = len(seen_order) - MAX_STATE
                if overflow > 0:
                    for _ in range(overflow):
                        oldest = seen_order.pop(0)
                        seen.discard(oldest)
                _save_state(seen_order)

        except Exception as exc:
            LOG.warning("Polling error: %s", exc)
            printer = None  # force re-init next loop
        finally:
            try:
                time.sleep(POLL_SECONDS)
            except KeyboardInterrupt:
                LOG.info("Stopping Kid Fax poller")
                _save_state(seen_order)
                return


def main() -> None:
    try:
        poll_loop()
    except KeyboardInterrupt:
        LOG.info("Stopping Kid Fax poller")


if __name__ == "__main__":
    main()
