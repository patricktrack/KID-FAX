#!/usr/bin/env python3
"""Discover Telegram chat IDs for contact mapping."""
from __future__ import annotations

import os
import requests
from typing import Dict, List


def get_bot_token() -> str:
    """Get bot token from environment."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set")
    return token


def get_updates(bot_token: str, offset: int | None = None) -> List[Dict]:
    """Fetch updates from Telegram Bot API."""
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    params = {'offset': offset, 'timeout': 10}
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json().get('result', [])


def discover_chats() -> None:
    """List all chats that have messaged the bot."""
    token = get_bot_token()
    updates = get_updates(token)

    chats: Dict[int, Dict] = {}
    for update in updates:
        if 'message' in update:
            msg = update['message']
            chat = msg['chat']
            chat_id = chat['id']
            first_name = chat.get('first_name', 'Unknown')
            last_name = chat.get('last_name', '')
            username = chat.get('username', '')

            full_name = f"{first_name} {last_name}".strip()
            chats[chat_id] = {
                'name': full_name,
                'username': username,
                'last_message': msg.get('text', '')[:50]
            }

    print("=" * 60)
    print("TELEGRAM CHAT IDS DISCOVERED")
    print("=" * 60)
    for chat_id, info in chats.items():
        print(f"\nChat ID: {chat_id}")
        print(f"  Name: {info['name']}")
        if info['username']:
            print(f"  Username: @{info['username']}")
        print(f"  Last message: {info['last_message']}")

    print("\n" + "=" * 60)
    print("ADD TO YOUR .env FILE:")
    print("=" * 60)

    # Generate example CONTACTS mapping
    suggestions = []
    for chat_id, info in chats.items():
        # Suggest lowercase first name as contact key
        suggested_name = info['name'].split()[0].lower()
        suggestions.append(f"{suggested_name}:{chat_id}")

    print(f"CONTACTS={','.join(suggestions)}")
    print(f"ALLOWLIST={','.join(str(c) for c in chats.keys())}")


if __name__ == "__main__":
    discover_chats()
