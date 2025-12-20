#!/usr/bin/env python3
"""Send a Telegram message from the Kid Fax setup."""
from __future__ import annotations

import os
import sys
import requests
from typing import Dict


def _required_env(name: str) -> str:
    """Get required environment variable."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required")
    return value


def _parse_contacts(raw: str) -> Dict[str, int]:
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
                continue
    return contacts


def _resolve_recipient(value: str, contacts: Dict[str, int]) -> int:
    """Resolve contact name or direct chat ID to chat ID."""
    if value in contacts:
        return contacts[value]
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"Unknown contact '{value}' and not a valid chat ID")


def send_message(bot_token: str, chat_id: int, text: str) -> bool:
    """Send text message via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get('ok'):
            msg_id = data['result']['message_id']
            print(f"Sent message (ID: {msg_id}) to chat {chat_id}")
            return True
        else:
            print(f"Failed to send: {data}")
            return False
    except Exception as exc:
        print(f"Error sending message: {exc}")
        return False


def main(argv: list[str] | None = None) -> int:
    """Main entry point for sending Telegram messages."""
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) < 2:
        print("Usage: python -m kidfax.send_telegram <name|chat_id> <message text>")
        print("\nExamples:")
        print("  python -m kidfax.send_telegram grandma 'Hello!'")
        print("  python -m kidfax.send_telegram 123456789 'Direct chat ID'")
        return 1

    recipient_key = argv[0]
    body = " ".join(argv[1:]).strip()
    if not body:
        print("Message body cannot be empty.")
        return 1

    contacts = _parse_contacts(os.getenv("CONTACTS", ""))

    try:
        chat_id = _resolve_recipient(recipient_key, contacts)
    except ValueError as exc:
        print(f"Error: {exc}")
        print(f"\nAvailable contacts: {', '.join(contacts.keys())}")
        return 1

    bot_token = _required_env("TELEGRAM_BOT_TOKEN")

    success = send_message(bot_token, chat_id, body)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
