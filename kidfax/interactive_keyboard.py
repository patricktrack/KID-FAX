#!/usr/bin/env python3
"""Interactive keyboard messaging for Kid Fax via Telegram."""
from __future__ import annotations

import logging
import os
import sys
import time
from typing import Optional

from pynput import keyboard

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
from kidfax.send_telegram import send_message

LOG = logging.getLogger("kidfax.interactive")

# Configuration
CHAR_LIMIT = int(os.getenv("TELEGRAM_CHAR_LIMIT", "4096"))
PRINT_RECEIPTS = os.getenv("PRINT_SEND_RECEIPTS", "false").lower() in {"1", "true", "yes"}


def _required_env(name: str) -> str:
    """Get required environment variable or raise error."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required")
    return value


def send_telegram(recipient_name: str, chat_id: str, message_text: str) -> bool:
    """
    Send Telegram message using Bot API.

    Args:
        recipient_name: Contact name (for logging)
        chat_id: Telegram chat ID
        message_text: Message body

    Returns:
        True if sent successfully, False otherwise
    """
    try:
        bot_token = _required_env("TELEGRAM_BOT_TOKEN")
        success = send_message(bot_token, int(chat_id), message_text)
        if success:
            LOG.info("Message sent to %s (chat %s)", recipient_name, chat_id)
        return success
    except Exception as exc:
        LOG.error("Failed to send message to %s: %s", recipient_name, exc)
        return False


def print_send_receipt(recipient_name: str, message_text: str) -> None:
    """
    Print optional receipt confirmation on thermal printer.

    Args:
        recipient_name: Contact name message was sent to
        message_text: Message body that was sent
    """
    if not PRINT_RECEIPTS:
        return

    try:
        from kidfax.printer import get_printer
        import datetime as dt

        allow_dummy = os.getenv("ALLOW_DUMMY_PRINTER", "false").lower() in {"1", "true", "yes"}
        printer = get_printer(allow_dummy=allow_dummy)

        if printer is None:
            LOG.debug("Printer not available for receipt")
            return

        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        line_width = int(os.getenv("PRINTER_LINE_WIDTH", "32"))

        # Header
        printer.set(align='center', font='a', width=2, height=2, bold=True)
        printer.text("MESSAGE SENT\n")

        # Metadata
        printer.set(align='center', font='a', width=1, height=1, bold=False)
        printer.text(f"{now}\n")
        printer.text("-" * line_width + "\n")

        # Recipient
        printer.set(align='left', font='a', width=1, height=1, bold=True)
        printer.text(f"To: {recipient_name.title()}\n\n")

        # Message
        printer.set(align='left', font='a', width=1, height=1, bold=False)

        # Wrap message text
        import textwrap
        for line in textwrap.wrap(message_text, width=line_width):
            printer.text(line + "\n")

        # Footer
        printer.text("\n")
        printer.text("-" * line_width + "\n")
        printer.set(align='center', font='a', width=1, height=1, bold=False)
        printer.text("✓ Delivered via Telegram\n")
        printer.text("\n")

        # Cut
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
    # Validate Telegram token early
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
    composer = MessageComposer(contacts, char_limit=CHAR_LIMIT)

    # Show initial contact list
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
                    print(f"Type your message (max {CHAR_LIMIT} chars), then press Enter to send:")
                    render_keyboard_mode(
                        epd,
                        composer.selected_recipient,
                        composer.get_message(),
                        CHAR_LIMIT
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

                    # Optional: Print receipt
                    print_send_receipt(recipient_name, message_text)

                    # Wait 2 seconds for user to see confirmation
                    time.sleep(2)
                else:
                    print(f"✗ Failed to send message to {recipient_name}")
                    render_send_confirmation(epd, recipient_name, "Error!")
                    time.sleep(2)

                # Reset and return to contact list
                composer.reset()
                render_contact_list(epd, composer.fkey_map)
                print("\n" + "="*50)
                print("Kid Fax - Reply Mode")
                print("="*50)
                print("Press F1-F12 to select a recipient:")
                for fkey, name in sorted(composer.fkey_map.items()):
                    print(f"  {fkey}: {name.title()}")
                print("\nPress ESC to exit")
                print("="*50)

                return

            # Backspace: Delete character
            if key == keyboard.Key.backspace:
                if composer.selected_recipient:
                    if composer.delete_character():
                        # Visual feedback in terminal only (e-ink too slow)
                        sys.stdout.write('\b \b')
                        sys.stdout.flush()
                return

            # Space key: Add space to message
            if key == keyboard.Key.space:
                if not composer.selected_recipient:
                    print("\n✗ Select a recipient first (press F1-F12)")
                    return
                if composer.add_character(' '):
                    sys.stdout.write(' ')
                    sys.stdout.flush()
                return

            # Regular character: Add to message
            if hasattr(key, 'char') and key.char:
                if not composer.selected_recipient:
                    print("\n✗ Select a recipient first (press F1-F12)")
                    return

                if composer.add_character(key.char):
                    # Echo character to terminal only (e-ink too slow for per-char updates)
                    sys.stdout.write(key.char)
                    sys.stdout.flush()
                else:
                    # Character limit reached
                    print(f"\n✗ Character limit reached ({CHAR_LIMIT})")

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
