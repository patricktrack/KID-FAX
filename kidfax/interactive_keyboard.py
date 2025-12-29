#!/usr/bin/env python3
"""Interactive keyboard messaging for Kid Fax."""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Optional

from pynput import keyboard
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
    is_function_key,
)

LOG = logging.getLogger("kidfax.interactive")
# Sent message tracking for conversation mode
SENT_MESSAGES_FILE = os.path.expanduser("~/.kidfax_sent_messages.json")
LAST_RECIPIENT_FILE = os.path.expanduser("~/.kidfax_last_recipient.json")

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

# Configuration
Telegram_CHAR_LIMIT = int(os.getenv("Telegram_CHAR_LIMIT", "160"))
PRINT_RECEIPTS = os.getenv("PRINT_SEND_RECEIPTS", "false").lower() in {"1", "true", "yes"}


def _required_env(name: str) -> str:
    """Get required environment variable or raise error."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required")
    return value


def send_telegram(recipient_name: str, chat_id: str, message_text: str) -> bool:
    """
    Send Telegram message using Telegram API.

    Args:
        recipient_name: Contact name (for logging)
        chat_id: Phone number in E.164 format
        message_text: Message body

    Returns:
        True if sent successfully, False otherwise
    """
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


def print_send_receipt(recipient_name: str, message_text: str) -> None:
    """
    Print receipt with right-justified bubble for sent messages.
    """
    if not PRINT_RECEIPTS:
        return

    try:
        from kidfax.printer import get_printer
        from kidfax.telegram_poller import _create_speech_bubble_right
        import datetime as dt

        allow_dummy = os.getenv("ALLOW_DUMMY_PRINTER", "false").lower() in {"1", "true", "yes"}
        printer = get_printer(allow_dummy=allow_dummy)

        if printer is None:
            LOG.debug("Printer not available for receipt")
            return

        # To: recipient name (centered)
        printer.set(align='center', font='a', width=1, height=1, bold=True)
        printer.text(f"To: {recipient_name.title()}\n\n")

        # Message in right-justified bubble
        try:
            bubble_img = _create_speech_bubble_right(message_text)
            printer.set(align='right')
            printer.image(bubble_img)
        except Exception as exc:
            LOG.debug(f"Bubble failed: {exc}")
            import textwrap
            line_width = int(os.getenv("PRINTER_LINE_WIDTH", "32"))
            printer.set(align='right', font='a', width=1, height=1, bold=False)
            for line in textwrap.wrap(message_text, width=line_width):
                printer.text(line + "\n")

        # Timestamp (small, right-aligned)
        now = dt.datetime.now().strftime("%m/%d/%y %I:%M %p")
        printer.set(align='right', font='a', width=1, height=1, bold=False)
        printer.text(f"{now}  \n")

        printer.text("\n")
        try:
            printer.cut()
        except Exception:
            printer.text("\n\n\n")

        LOG.info("Receipt printed for message to %s", recipient_name)

    except Exception as exc:
        LOG.debug("Failed to print receipt: %s", exc)


def interactive_loop() -> None:
    """
    Main interactive keyboard messaging loop.

    Workflow:
    1. Show contact list on e-ink display
    2. Wait for F1-F12 press to select recipient
    3. Show recipient and typed message on e-ink
    4. Wait for Enter to send or ESC to cancel
    5. Send message via Telegram
    6. Show confirmation and optional receipt
    7. Return to contact list
    """
    # Validate Telegram bot token early
    try:
        _required_env("TELEGRAM_BOT_TOKEN")
    except RuntimeError as exc:
        LOG.error("Telegram configuration error: %s", exc)
        print(f"Error: {exc}")
        print("Please configure TELEGRAM_BOT_TOKEN in .env file")
        sys.exit(1)

    # Load contacts
    try:
        contacts = load_contacts(limit=12)
    except RuntimeError as exc:
        LOG.error("Contact configuration error: %s", exc)
        print(f"Error: {exc}")
        print("Please configure CONTACTS in .env file")
        print("Example: CONTACTS=grandma:+15551112222,uncle:+15553334444")
        sys.exit(1)

    # Initialize e-ink display
    epd = init_display()
    if epd is None:
        LOG.warning("E-ink display not available (continuing without display)")

    # Initialize message composer
    composer = MessageComposer(contacts, char_limit=Telegram_CHAR_LIMIT)

    # Check for last recipient and show their avatar, or show contact list
    last_recipient = _load_last_recipient()
    if last_recipient and last_recipient[0]:
        last_name, last_chat_id = last_recipient
        # Show last recipient ready to message
        render_keyboard_mode(epd, last_name, "")
        print(f"Ready to message: {last_name.title()}")
        print("Press any F-key to change recipient, or start typing...")
        # Pre-select this contact
        composer.select_recipient_by_name(last_name)
    else:
        render_contact_list(epd, composer.fkey_map)

    # Keyboard event handler
    def on_key_press(key):
        """Handle keyboard events."""
        try:
            # ESC: Exit application
            if key == keyboard.Key.esc:
                LOG.info("ESC pressed, exiting interactive mode")
                render_contact_list(epd, composer.fkey_map)
                print("\nExiting Kid Fax interactive keyboard mode...")
                return False  # Stop listener

            # Function key: Select recipient
            fkey_name = is_function_key(key)
            if fkey_name:
                if composer.select_recipient_by_fkey(fkey_name):
                    print(f"\n→ Selected: {composer.selected_recipient}")
                    print(f"Type your message (max {Telegram_CHAR_LIMIT} chars), then press Enter to send:")
                    render_keyboard_mode(
                        epd,
                        composer.selected_recipient,
                        composer.get_message(),
                        Telegram_CHAR_LIMIT
                    )
                else:
                    print(f"\n✗ No contact mapped to {fkey_name}")
                return

            # Enter: Send message
            if key == keyboard.Key.enter:
                if not composer.is_ready_to_send():
                    if not composer.selected_recipient:
                        print("\n✗ No recipient selected. Press F1-F12 to select a contact.")
                    elif not composer.message_buffer:
                        print("\n✗ Message is empty. Type a message first.")
                    return

                recipient_name = composer.selected_recipient
                chat_id = composer.selected_number
                message_text = composer.get_message()

                print(f"\n→ Sending to {recipient_name}...")

                # Show "Sending..." on e-ink
                render_send_confirmation(epd, recipient_name, "Sending...")

                # Send via Telegram
                success = send_telegram(recipient_name, chat_id, message_text)

                if success:
                    print(f"✓ Message sent to {recipient_name}!")

                    # Show "Sent!" confirmation
                    render_send_confirmation(epd, recipient_name, "Sent!")

                    # Save for conversation tracking (prints with response)
                    _save_sent_message(chat_id, message_text)
                    _save_last_recipient(recipient_name, chat_id)

                    # Wait 2 seconds for user to see confirmation
                    time.sleep(2)
                else:
                    print(f"✗ Failed to send message to {recipient_name}")
                    render_send_confirmation(epd, recipient_name, "Error!")
                    time.sleep(2)

                # Clear message but stay on same recipient, ready to type again
                composer.clear_message()
                render_keyboard_mode(epd, recipient_name, "", Telegram_CHAR_LIMIT)
                print(f"\nReady to message {recipient_name.title()} again (or press F-key to switch)")

                return

            # Backspace: Delete character
            if key == keyboard.Key.backspace:
                if composer.selected_recipient:
                    if composer.delete_character():
                        # Visual feedback in terminal only (e-ink too slow)
                        sys.stdout.write('\b \b')
                        sys.stdout.flush()
                return

            # Space key: Add space to message and update e-ink (after each word)
            if key == keyboard.Key.space:
                if not composer.selected_recipient:
                    print("\n✗ Select a recipient first (press F1-F12)")
                    return
                if composer.add_character(' '):
                    sys.stdout.write(' ')
                    sys.stdout.flush()
                    # Update e-ink after each word
                    render_keyboard_mode(
                        epd,
                        composer.selected_recipient,
                        composer.get_message(),
                        Telegram_CHAR_LIMIT
                    )
                return

            # Regular character: Add to message
            if hasattr(key, 'char') and key.char:
                if not composer.selected_recipient:
                    print("\n✗ Select a recipient first (press F1-F12)")
                    return

                if composer.add_character(key.char):
                    # Terminal echo only (e-ink too slow for per-char updates)
                    pass
                    # Echo character to console
                    sys.stdout.write(key.char)
                    sys.stdout.flush()
                else:
                    # Character limit reached
                    print(f"\n✗ Character limit reached ({Telegram_CHAR_LIMIT})")

        except Exception as exc:
            LOG.error("Error handling key press: %s", exc)

    # Start keyboard listener
    print("\n" + "="*50)
    print("Kid Fax - Interactive Keyboard Mode")
    print("="*50)
    print("Press F1-F12 to select a recipient:")
    for fkey, name in sorted(composer.fkey_map.items()):
        print(f"  {fkey}: {name.title()}")
    print("\nPress ESC to exit")
    print("="*50)

    LOG.info("Interactive keyboard mode started")

    with keyboard.Listener(on_press=on_key_press) as listener:
        listener.join()

    LOG.info("Interactive keyboard mode stopped")


def main() -> None:
    """Entry point for interactive keyboard mode."""
    # Configure logging
    logging.basicConfig(
        level=os.getenv("KIDFAX_LOG_LEVEL", "INFO").upper(),
        format="[%(asctime)s] %(levelname)s: %(message)s",
    )

    try:
        interactive_loop()
    except KeyboardInterrupt:
        LOG.info("Keyboard interrupt, exiting")
        print("\n\nExiting Kid Fax interactive keyboard mode...")
    except Exception as exc:
        LOG.error("Fatal error: %s", exc)
        print(f"\nError: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
