#!/usr/bin/env python3
"""Shared e-ink display utilities for Kid Fax."""
from __future__ import annotations

import importlib
import logging
import os
import textwrap
from typing import Optional

LOG = logging.getLogger("kidfax.eink")

# Environment configuration
EINK_ENABLED = os.getenv("EINK_STATUS_ENABLED", "false").lower() in {"1", "true", "yes"}
EINK_DRIVER_PACKAGE = os.getenv(
    "EINK_DRIVER_PACKAGE",
    "e-Paper.RaspberryPi_JetsonNano.python.lib.waveshare_epd",
)
EINK_DRIVER_MODULE = os.getenv("EINK_DRIVER_MODULE", "epd2in9d")
HEADER_TEXT = os.getenv("KIDFAX_HEADER", "Kid Fax")


def _is_enabled() -> bool:
    """Check if e-ink display is enabled."""
    return EINK_ENABLED


def init_display():
    """
    Initialize Waveshare e-Paper display.

    Returns:
        EPD display object, or None if disabled or failed

    Raises:
        Exception: If display initialization fails and EINK_ENABLED is True
    """
    if not _is_enabled():
        LOG.debug("E-ink display disabled (EINK_STATUS_ENABLED=false)")
        return None

    try:
        module = importlib.import_module(f"{EINK_DRIVER_PACKAGE}.{EINK_DRIVER_MODULE}")
        epd = module.EPD()
        epd.init()
        LOG.info("E-ink display initialized (%s x %s)", epd.width, epd.height)
        return epd
    except Exception as exc:
        LOG.warning("Failed to initialize e-ink display: %s", exc)
        return None


def render_polling_status(
    epd,
    new_count: int,
    sender_label: Optional[str] = None,
    subtitle: Optional[str] = None,
) -> None:
    """
    Render SMS polling status on e-ink display.

    Shows header, subtitle, new message count, and last sender.

    Args:
        epd: Initialized e-Paper display object
        new_count: Number of new messages printed
        sender_label: Label for last sender (e.g., "grandma (+15551234567)")
        subtitle: Optional subtitle text (default: "Messages from family")
    """
    if epd is None or new_count <= 0:
        return

    try:
        from PIL import Image, ImageDraw, ImageFont

        epd.Clear(0xFF)
        width, height = epd.width, epd.height
        image = Image.new('1', (width, height), 255)
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()

        # Header
        draw.text((10, 10), HEADER_TEXT, font=font, fill=0)

        # Subtitle
        subtitle_text = subtitle or os.getenv("KIDFAX_SUBTITLE", "Messages from family")
        draw.text((10, 26), subtitle_text, font=font, fill=0)

        # New message count
        draw.text((10, 44), f"New: {new_count}", font=font, fill=0)

        # Last sender
        if sender_label:
            draw.text((10, 62), f"Last: {sender_label}", font=font, fill=0)

        # Bottom accent line
        draw.rectangle((10, height - 20, width - 10, height - 18), fill=0)

        epd.display(epd.getbuffer(image))
        epd.sleep()
    except Exception as exc:
        LOG.debug("Failed to update e-ink display: %s", exc)


def render_contact_list(epd, fkey_map: dict[str, str]) -> None:
    """
    Render contact selection screen showing F-key mappings.

    Args:
        epd: Initialized e-Paper display object
        fkey_map: Dictionary mapping F-keys to contact names (e.g., {"F1": "grandma"})
    """
    if epd is None:
        return

    try:
        from PIL import Image, ImageDraw, ImageFont

        epd.Clear(0xFF)
        width, height = epd.width, epd.height
        image = Image.new('1', (width, height), 255)
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()

        # Header
        draw.text((10, 5), f"{HEADER_TEXT} - Reply Mode", font=font, fill=0)
        draw.line((10, 20, width - 10, 20), fill=0)

        # Contact list (max 8 visible on 2.9" screen)
        y = 28
        for i, (fkey, contact_name) in enumerate(sorted(fkey_map.items())[:8]):
            if y > height - 30:
                break
            text = f"{fkey}  {contact_name.title()}"
            draw.text((10, y), text, font=font, fill=0)
            y += 12

        # Footer instruction
        draw.text((10, height - 15), "Press F-key to reply", font=font, fill=0)

        epd.display(epd.getbuffer(image))
        epd.sleep()
    except Exception as exc:
        LOG.debug("Failed to render contact list: %s", exc)


def render_keyboard_mode(
    epd,
    recipient: str,
    message: str,
    char_limit: int = 160,
) -> None:
    """
    Render interactive keyboard mode showing recipient and typed message.

    Layout:
        To: Grandma
        ─────────────────────
        Thanks for the cookies!
        They were delicious. Lo
        ve you! See you soon!

        [64/160]          ENTER

    Args:
        epd: Initialized e-Paper display object
        recipient: Contact name being messaged
        message: Current message text
        char_limit: SMS character limit (default 160)
    """
    if epd is None:
        return

    try:
        from PIL import Image, ImageDraw, ImageFont

        epd.Clear(0xFF)
        width, height = epd.width, epd.height
        image = Image.new('1', (width, height), 255)
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()

        # Recipient header (bold simulation with offset)
        recipient_text = f"To: {recipient.title()}"
        draw.text((10, 5), recipient_text, font=font, fill=0)
        draw.text((11, 5), recipient_text, font=font, fill=0)  # Bold effect

        # Separator line
        draw.line((10, 20, width - 10, 20), fill=0)

        # Message text (wrapped, max ~25 chars per line on 2.9" screen)
        y = 28
        wrapped_lines = textwrap.wrap(message, width=25) if message else [""]
        for line in wrapped_lines[:4]:  # Max 4 visible lines
            if y > height - 30:
                break
            draw.text((10, y), line, font=font, fill=0)
            y += 12

        # Footer: character count and send instruction
        char_count = f"[{len(message)}/{char_limit}]"
        draw.text((10, height - 15), char_count, font=font, fill=0)
        draw.text((width - 60, height - 15), "ENTER", font=font, fill=0)

        epd.display(epd.getbuffer(image))
        epd.sleep()
    except Exception as exc:
        LOG.debug("Failed to render keyboard mode: %s", exc)


def render_send_confirmation(
    epd,
    recipient: str,
    status: str,
    duration_seconds: int = 2,
) -> None:
    """
    Render message send confirmation or error.

    Args:
        epd: Initialized e-Paper display object
        recipient: Contact name message was sent to
        status: Status text ("Sending...", "Sent!", "Error!")
        duration_seconds: How long to display (not auto-cleared by this function)
    """
    if epd is None:
        return

    try:
        from PIL import Image, ImageDraw, ImageFont

        epd.Clear(0xFF)
        width, height = epd.width, epd.height
        image = Image.new('1', (width, height), 255)
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()

        # Center-aligned status
        y_center = height // 2 - 20

        # Status icon/text (large)
        if status == "Sent!":
            symbol = "✓"
        elif status == "Sending...":
            symbol = "→"
        else:  # Error
            symbol = "✗"

        draw.text((width // 2 - 20, y_center), symbol, font=font, fill=0)
        draw.text((width // 2 - 20 + 1, y_center), symbol, font=font, fill=0)  # Bold

        # Status text
        draw.text((width // 2 - 30, y_center + 20), status, font=font, fill=0)

        # Recipient
        recipient_text = f"To: {recipient.title()}"
        draw.text((width // 2 - 40, y_center + 40), recipient_text, font=font, fill=0)

        epd.display(epd.getbuffer(image))
        epd.sleep()
    except Exception as exc:
        LOG.debug("Failed to render send confirmation: %s", exc)


def clear_display(epd) -> None:
    """
    Clear e-ink display to white.

    Args:
        epd: Initialized e-Paper display object
    """
    if epd is None:
        return

    try:
        epd.Clear(0xFF)
        epd.sleep()
    except Exception as exc:
        LOG.debug("Failed to clear display: %s", exc)
