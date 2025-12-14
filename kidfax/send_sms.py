#!/usr/bin/env python3
"""Send a text message via Twilio from the Kid Fax setup."""
from __future__ import annotations

import os
import sys
from typing import Dict

from twilio.rest import Client


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required")
    return value


def _parse_contacts(raw: str) -> Dict[str, str]:
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


def _resolve_recipient(value: str, contacts: Dict[str, str]) -> str:
    if value in contacts:
        return contacts[value]
    return value


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) < 2:
        print("Usage: python -m kidfax.send_sms <name|+number> <message text>")
        return 1

    recipient_key = argv[0]
    body = " ".join(argv[1:]).strip()
    if not body:
        print("Message body cannot be empty.")
        return 1

    contacts = _parse_contacts(os.getenv("CONTACTS", ""))
    to_number = _resolve_recipient(recipient_key, contacts)

    account_sid = _required_env("TWILIO_ACCOUNT_SID")
    auth_token = _required_env("TWILIO_AUTH_TOKEN")
    from_number = _required_env("TWILIO_NUMBER")

    client = Client(account_sid, auth_token)
    message = client.messages.create(to=to_number, from_=from_number, body=body)
    print(f"Sent message {message.sid} to {to_number}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
