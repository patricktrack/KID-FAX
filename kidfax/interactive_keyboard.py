#!/usr/bin/env python3
"""Interactive keyboard messaging for Kid Fax (headless, using evdev)."""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Optional

import evdev
from evdev import ecodes
import requests

from kidfax.eink_display import (
    init_display,
    render_contact_list,
    render_keyboard_mode,
    render_send_confirmation,
)
from kidfax.keyboard_input import (
    MessageComposer,
    load_contacts,
)

LOG = logging.getLogger("kidfax.interactive")

# Sent message tracking for conversation mode
# Use absolute path so root (keyboard) and patricktrack (poller) share the same file
SENT_MESSAGES_FILE = "/home/patricktrack/.kidfax_sent_messages.json"
LAST_RECIPIENT_FILE = "/home/patricktrack/.kidfax_last_recipient.json"

# Load .env file
def _load_env():
    """Load environment variables from .env file."""
    from pathlib import Path
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    os.environ.setdefault(key.strip(), value.strip())

_load_env()

# Configuration
Telegram_CHAR_LIMIT = int(os.getenv("TELEGRAM_CHAR_LIMIT", "4096"))


def _save_last_recipient(name: str, chat_id: str) -> None:
    """Save the last messaged recipient."""
    try:
        with open(LAST_RECIPIENT_FILE, 'w') as f:
            json.dump({'name': name, 'chat_id': chat_id}, f)
    except Exception as exc:
        LOG.debug(f"Failed to save last recipient: {exc}")


def _load_last_recipient() -> Optional[tuple]:
    """Load the last messaged recipient. Returns (name, chat_id) or None."""
    try:
        if os.path.exists(LAST_RECIPIENT_FILE):
            with open(LAST_RECIPIENT_FILE, 'r') as f:
                data = json.load(f)
                return (data.get('name'), data.get('chat_id'))
    except Exception as exc:
        LOG.debug(f"Failed to load last recipient: {exc}")
    return None


def _save_sent_message(chat_id: str, message: str) -> None:
    """Save sent message with timestamp for conversation tracking."""
    import datetime as dt
    try:
        data = {}
        if os.path.exists(SENT_MESSAGES_FILE):
            with open(SENT_MESSAGES_FILE, 'r') as f:
                data = json.load(f)

        data[str(chat_id)] = {
            'message': message,
            'timestamp': dt.datetime.now().isoformat()
        }

        with open(SENT_MESSAGES_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as exc:
        LOG.debug(f"Failed to save sent message: {exc}")


def _required_env(name: str) -> str:
    """Get required environment variable or raise error."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required")
    return value


def send_telegram(recipient_name: str, chat_id: str, message_text: str) -> bool:
    """Send Telegram message using Telegram API."""
    try:
        bot_token = _required_env("TELEGRAM_BOT_TOKEN")
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {'chat_id': chat_id, 'text': message_text}
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()

        if data.get('ok'):
            LOG.info("Message sent to %s (chat_id=%s)", recipient_name, chat_id)
            return True
        else:
            LOG.error("Failed to send to %s: %s", recipient_name, data)
            return False

    except Exception as exc:
        LOG.error("Failed to send message to %s: %s", recipient_name, exc)
        return False


def find_keyboard_device():
    """Find the keyboard input device."""
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    for device in devices:
        caps = device.capabilities()
        # Look for device with key events that has letter keys
        if ecodes.EV_KEY in caps:
            keys = caps[ecodes.EV_KEY]
            # Check if it has typical keyboard keys (letters, F-keys)
            if ecodes.KEY_A in keys and ecodes.KEY_F1 in keys:
                LOG.info(f"Found keyboard: {device.name} at {device.path}")
                return device

    # Fallback: return first device with key events
    for device in devices:
        caps = device.capabilities()
        if ecodes.EV_KEY in caps:
            LOG.info(f"Using input device: {device.name} at {device.path}")
            return device

    return None


# Key code to character mapping (US keyboard layout)
KEY_MAP = {
    ecodes.KEY_A: 'a', ecodes.KEY_B: 'b', ecodes.KEY_C: 'c', ecodes.KEY_D: 'd',
    ecodes.KEY_E: 'e', ecodes.KEY_F: 'f', ecodes.KEY_G: 'g', ecodes.KEY_H: 'h',
    ecodes.KEY_I: 'i', ecodes.KEY_J: 'j', ecodes.KEY_K: 'k', ecodes.KEY_L: 'l',
    ecodes.KEY_M: 'm', ecodes.KEY_N: 'n', ecodes.KEY_O: 'o', ecodes.KEY_P: 'p',
    ecodes.KEY_Q: 'q', ecodes.KEY_R: 'r', ecodes.KEY_S: 's', ecodes.KEY_T: 't',
    ecodes.KEY_U: 'u', ecodes.KEY_V: 'v', ecodes.KEY_W: 'w', ecodes.KEY_X: 'x',
    ecodes.KEY_Y: 'y', ecodes.KEY_Z: 'z',
    ecodes.KEY_1: '1', ecodes.KEY_2: '2', ecodes.KEY_3: '3', ecodes.KEY_4: '4',
    ecodes.KEY_5: '5', ecodes.KEY_6: '6', ecodes.KEY_7: '7', ecodes.KEY_8: '8',
    ecodes.KEY_9: '9', ecodes.KEY_0: '0',
    ecodes.KEY_MINUS: '-', ecodes.KEY_EQUAL: '=',
    ecodes.KEY_LEFTBRACE: '[', ecodes.KEY_RIGHTBRACE: ']',
    ecodes.KEY_SEMICOLON: ';', ecodes.KEY_APOSTROPHE: "'",
    ecodes.KEY_GRAVE: '`', ecodes.KEY_BACKSLASH: '\\',
    ecodes.KEY_COMMA: ',', ecodes.KEY_DOT: '.', ecodes.KEY_SLASH: '/',
}

# Shift key mapping for symbols
SHIFT_KEY_MAP = {
    ecodes.KEY_1: '!', ecodes.KEY_2: '@', ecodes.KEY_3: '#', ecodes.KEY_4: '$',
    ecodes.KEY_5: '%', ecodes.KEY_6: '^', ecodes.KEY_7: '&', ecodes.KEY_8: '*',
    ecodes.KEY_9: '(', ecodes.KEY_0: ')',
    ecodes.KEY_MINUS: '_', ecodes.KEY_EQUAL: '+',
    ecodes.KEY_LEFTBRACE: '{', ecodes.KEY_RIGHTBRACE: '}',
    ecodes.KEY_SEMICOLON: ':', ecodes.KEY_APOSTROPHE: '"',
    ecodes.KEY_GRAVE: '~', ecodes.KEY_BACKSLASH: '|',
    ecodes.KEY_COMMA: '<', ecodes.KEY_DOT: '>', ecodes.KEY_SLASH: '?',
}

# F-key mapping
FKEY_MAP = {
    ecodes.KEY_F1: 'F1', ecodes.KEY_F2: 'F2', ecodes.KEY_F3: 'F3', ecodes.KEY_F4: 'F4',
    ecodes.KEY_F5: 'F5', ecodes.KEY_F6: 'F6', ecodes.KEY_F7: 'F7', ecodes.KEY_F8: 'F8',
    ecodes.KEY_F9: 'F9', ecodes.KEY_F10: 'F10', ecodes.KEY_F11: 'F11', ecodes.KEY_F12: 'F12',
}


def interactive_loop() -> None:
    """Main interactive keyboard messaging loop using evdev."""

    # Validate Telegram bot token early
    try:
        _required_env("TELEGRAM_BOT_TOKEN")
    except RuntimeError as exc:
        LOG.error("Telegram configuration error: %s", exc)
        print(f"Error: {exc}")
        sys.exit(1)

    # Load contacts
    try:
        contacts = load_contacts(limit=12)
    except RuntimeError as exc:
        LOG.error("Contact configuration error: %s", exc)
        print(f"Error: {exc}")
        sys.exit(1)

    # Find keyboard device
    keyboard = find_keyboard_device()
    if keyboard is None:
        LOG.error("No keyboard device found!")
        print("Error: No keyboard device found")
        sys.exit(1)

    # Initialize e-ink display
    epd = init_display()
    if epd is None:
        LOG.warning("E-ink display not available")

    # Initialize message composer
    composer = MessageComposer(contacts, char_limit=Telegram_CHAR_LIMIT)

    # Check for last recipient and show on e-ink
    last_recipient = _load_last_recipient()
    if last_recipient and last_recipient[0]:
        last_name, last_chat_id = last_recipient
        render_keyboard_mode(epd, last_name, "", Telegram_CHAR_LIMIT)
        LOG.info(f"Ready to message: {last_name}")
        composer.select_recipient_by_name(last_name)
    else:
        render_contact_list(epd, composer.fkey_map)

    LOG.info("Interactive keyboard mode started (headless)")

    shift_pressed = False

    try:
        # Grab exclusive access to keyboard
        keyboard.grab()

        for event in keyboard.read_loop():
            if event.type != ecodes.EV_KEY:
                continue

            key_code = event.code
            key_state = event.value  # 0=release, 1=press, 2=hold

            # Track shift key state
            if key_code in (ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT):
                shift_pressed = (key_state != 0)
                continue

            # Only process key presses (not releases or holds)
            if key_state != 1:
                continue

            # ESC: Exit
            if key_code == ecodes.KEY_ESC:
                LOG.info("ESC pressed, exiting")
                render_contact_list(epd, composer.fkey_map)
                break

            # F-key: Select recipient
            if key_code in FKEY_MAP:
                fkey_name = FKEY_MAP[key_code]
                if composer.select_recipient_by_fkey(fkey_name):
                    LOG.info(f"Selected: {composer.selected_recipient}")
                    render_keyboard_mode(
                        epd,
                        composer.selected_recipient,
                        composer.get_message(),
                        Telegram_CHAR_LIMIT
                    )
                continue

            # Enter: Send message
            if key_code == ecodes.KEY_ENTER:
                if not composer.is_ready_to_send():
                    continue

                recipient_name = composer.selected_recipient
                chat_id = composer.selected_number
                message_text = composer.get_message()

                LOG.info(f"Sending to {recipient_name}...")
                render_send_confirmation(epd, recipient_name, "Sending...")

                success = send_telegram(recipient_name, chat_id, message_text)

                if success:
                    LOG.info(f"Message sent to {recipient_name}")
                    render_send_confirmation(epd, recipient_name, "Sent!")
                    _save_sent_message(chat_id, message_text)
                    _save_last_recipient(recipient_name, chat_id)
                    time.sleep(2)
                else:
                    LOG.error(f"Failed to send to {recipient_name}")
                    render_send_confirmation(epd, recipient_name, "Error!")
                    time.sleep(2)

                # Stay on same recipient, ready to type again
                composer.clear_message()
                render_keyboard_mode(epd, recipient_name, "", Telegram_CHAR_LIMIT)
                continue

            # Backspace: Delete character and refresh e-ink
            if key_code == ecodes.KEY_BACKSPACE:
                if composer.selected_recipient and composer.delete_character():
                    render_keyboard_mode(
                        epd,
                        composer.selected_recipient,
                        composer.get_message(),
                        Telegram_CHAR_LIMIT
                    )
                continue

            # Space: Add space and update e-ink every 4 chars
            if key_code == ecodes.KEY_SPACE:
                if composer.selected_recipient and composer.add_character(' '):
                    if len(composer.get_message()) % 4 == 0:
                        render_keyboard_mode(
                            epd,
                            composer.selected_recipient,
                            composer.get_message(),
                            Telegram_CHAR_LIMIT
                        )
                continue

            # Regular character
            if key_code in KEY_MAP:
                if not composer.selected_recipient:
                    continue

                if shift_pressed:
                    # Check for shifted symbol first
                    if key_code in SHIFT_KEY_MAP:
                        char = SHIFT_KEY_MAP[key_code]
                    elif key_code in KEY_MAP:
                        char = KEY_MAP[key_code].upper()
                    else:
                        continue
                else:
                    char = KEY_MAP[key_code]

                composer.add_character(char)
                # Update e-ink every 4 characters
                if len(composer.get_message()) % 4 == 0:
                    render_keyboard_mode(
                        epd,
                        composer.selected_recipient,
                        composer.get_message(),
                        Telegram_CHAR_LIMIT
                    )
                continue

    except KeyboardInterrupt:
        LOG.info("Interrupted")
    finally:
        keyboard.ungrab()
        LOG.info("Keyboard released")


def main() -> None:
    """Entry point for interactive keyboard mode."""
    logging.basicConfig(
        level=os.getenv("KIDFAX_LOG_LEVEL", "INFO").upper(),
        format="[%(asctime)s] %(levelname)s: %(message)s",
    )

    try:
        interactive_loop()
    except Exception as exc:
        LOG.error("Fatal error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
