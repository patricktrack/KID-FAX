#!/usr/bin/env python3
"""Shared e-ink display utilities for Kid Fax (Inky pHAT)."""
from __future__ import annotations

import logging
import os
import textwrap
from typing import Optional

LOG = logging.getLogger("kidfax.eink")

# Environment configuration
EINK_ENABLED = os.getenv("EINK_STATUS_ENABLED", "false").lower() in {"1", "true", "yes"}
EINK_COLOR = os.getenv("EINK_COLOR", "black")  # "black", "red", "yellow"
HEADER_TEXT = os.getenv("KIDFAX_HEADER", "Kid Fax")


class InkyWrapper:
    """Wrapper to provide consistent API for Inky pHAT displays."""
    
    def __init__(self, display):
        self._display = display
        self.width = display.width
        self.height = display.height
    
    def Clear(self, color=0xFF):
        """Clear display (compatibility method)."""
        pass  # Will be cleared when new image is set
    
    def display(self, image):
        """Display image on screen."""
        self._display.set_image(image)
        self._display.show()
    
    def getbuffer(self, image):
        """Return image (Inky handles conversion internally)."""
        return image
    
    def sleep(self):
        """No-op for Inky (no sleep mode needed)."""
        pass
    
    def init(self):
        """No-op for Inky (already initialized)."""
        pass


def _is_enabled() -> bool:
    """Check if e-ink display is enabled."""
    return EINK_ENABLED


def init_display():
    """
    Initialize Inky pHAT e-ink display.

    Returns:
        Display object, or None if disabled or failed
    """
    if not _is_enabled():
        LOG.debug("E-ink display disabled (EINK_STATUS_ENABLED=false)")
        return None

    try:
        from inky import InkyPHAT_SSD1608 as InkyPHAT
        inky_display = InkyPHAT(EINK_COLOR)
        LOG.info("InkyPHAT initialized (%sx%s, %s)", inky_display.width, inky_display.height, EINK_COLOR)
        return InkyWrapper(inky_display)
    except Exception as exc:
        LOG.warning("Failed to initialize InkyPHAT: %s", exc)
        return None


def render_polling_status(
    epd,
    new_count: int,
    sender_label: Optional[str] = None,
    subtitle: Optional[str] = None,
) -> None:
    """Render message status on e-ink display."""
    if epd is None or new_count <= 0:
        return

    try:
        from PIL import Image, ImageDraw, ImageFont

        width, height = epd.width, epd.height
        image = Image.new('P', (width, height), 0)
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()

        # Header
        draw.text((10, 10), HEADER_TEXT, font=font, fill=1)

        # Subtitle
        subtitle_text = subtitle or os.getenv("KIDFAX_SUBTITLE", "Messages from family")
        draw.text((10, 26), subtitle_text, font=font, fill=1)

        # New message count
        draw.text((10, 44), f"New: {new_count}", font=font, fill=1)

        # Last sender
        if sender_label:
            draw.text((10, 62), f"Last: {sender_label[:20]}", font=font, fill=1)

        # Bottom accent line
        draw.rectangle((10, height - 15, width - 10, height - 12), fill=1)

        epd.display(epd.getbuffer(image))
    except Exception as exc:
        LOG.debug("Failed to update e-ink display: %s", exc)


def render_contact_list(epd, fkey_map: dict[str, str]) -> None:
    """Render contact selection screen showing F-key mappings."""
    if epd is None:
        return

    try:
        from PIL import Image, ImageDraw, ImageFont

        width, height = epd.width, epd.height
        image = Image.new('P', (width, height), 0)
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()

        # Header
        draw.text((10, 5), f"{HEADER_TEXT} - Reply", font=font, fill=1)
        draw.line((10, 18, width - 10, 18), fill=1)

        # Contact list
        y = 24
        line_height = 10
        for i, (fkey, contact_name) in enumerate(sorted(fkey_map.items())[:8]):
            if y > height - 20:
                break
            text = f"{fkey} {contact_name.title()[:12]}"
            draw.text((10, y), text, font=font, fill=1)
            y += line_height

        # Footer
        draw.text((10, height - 12), "Press F-key", font=font, fill=1)

        epd.display(epd.getbuffer(image))
    except Exception as exc:
        LOG.debug("Failed to render contact list: %s", exc)


def render_keyboard_mode(
    epd,
    recipient: str,
    message: str,
    char_limit: int = 160,
) -> None:
    """Render keyboard mode with avatar and message text in larger font."""
    if epd is None:
        return

    try:
        from PIL import Image, ImageDraw, ImageFont
        from pathlib import Path

        width, height = epd.width, epd.height
        image = Image.new('P', (width, height), 0)
        draw = ImageDraw.Draw(image)

        # Try to load larger fonts
        try:
            name_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
            text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
        except (IOError, OSError):
            name_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
            small_font = ImageFont.load_default()

        # Avatar on left side (smaller to leave room for text)
        avatar_size = 48
        avatar_x = 4
        avatar_y = 4

        # Try to load pre-processed e-ink avatar
        eink_avatar_dir = Path.home() / ".kidfax_avatars" / "eink"
        avatar_name = f"{recipient.lower().replace(' ', '_')}.png"
        avatar_path = eink_avatar_dir / avatar_name

        if avatar_path.exists():
            try:
                avatar = Image.open(avatar_path)
                # Resize if needed
                if avatar.size != (avatar_size, avatar_size):
                    avatar = avatar.resize((avatar_size, avatar_size))
                image.paste(avatar, (avatar_x, avatar_y))
            except Exception:
                draw.ellipse((avatar_x, avatar_y, avatar_x + avatar_size, avatar_y + avatar_size), outline=1, width=2)
        else:
            # Draw circle with first letter
            draw.ellipse((avatar_x, avatar_y, avatar_x + avatar_size, avatar_y + avatar_size), outline=1, width=2)
            letter = recipient[0].upper() if recipient else "?"
            draw.text((avatar_x + 16, avatar_y + 14), letter, font=name_font, fill=1)

        # Recipient name next to avatar
        name_x = avatar_x + avatar_size + 8
        draw.text((name_x, 8), f"To: {recipient.title()[:12]}", font=name_font, fill=1)

        # Character count next to name
        char_count = f"{len(message)}/{char_limit}"
        draw.text((name_x, 28), char_count, font=small_font, fill=1)

        # Divider line
        divider_y = avatar_y + avatar_size + 4
        draw.line((4, divider_y, width - 4, divider_y), fill=1, width=1)

        # Message text area (below avatar, full width, larger font)
        text_start_y = divider_y + 6
        text_x = 6
        line_height = 18
        chars_per_line = 28  # Wider chars for larger font

        if message:
            wrapped_lines = textwrap.wrap(message, width=chars_per_line)
            y = text_start_y
            max_lines = (height - text_start_y - 4) // line_height
            for line in wrapped_lines[:max_lines]:
                draw.text((text_x, y), line, font=text_font, fill=1)
                y += line_height
        else:
            # Show cursor/prompt
            draw.text((text_x, text_start_y), "Type message...", font=text_font, fill=1)

        epd.display(epd.getbuffer(image))
    except Exception as exc:
        LOG.debug("Failed to render keyboard mode: %s", exc)


def render_send_confirmation(
    epd,
    recipient: str,
    status: str,
    duration_seconds: int = 2,
) -> None:
    """Render message send confirmation or error."""
    if epd is None:
        return

    try:
        from PIL import Image, ImageDraw, ImageFont

        width, height = epd.width, epd.height
        image = Image.new('P', (width, height), 0)
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()

        # Center-aligned status
        y_center = height // 2 - 15

        # Status symbol
        if status == "Sent!":
            symbol = "OK"
        elif "Sending" in str(status):
            symbol = "..."
        else:
            symbol = "X"

        draw.text((width // 2 - 10, y_center), symbol, font=font, fill=1)
        draw.text((width // 2 - 20, y_center + 15), str(status)[:10], font=font, fill=1)
        draw.text((width // 2 - 30, y_center + 30), f"To: {recipient.title()[:10]}", font=font, fill=1)

        epd.display(epd.getbuffer(image))
    except Exception as exc:
        LOG.debug("Failed to render send confirmation: %s", exc)


def clear_display(epd) -> None:
    """Clear e-ink display to white."""
    if epd is None:
        return

    try:
        from PIL import Image
        width, height = epd.width, epd.height
        image = Image.new('P', (width, height), 0)
        epd.display(epd.getbuffer(image))
    except Exception as exc:
        LOG.debug("Failed to clear display: %s", exc)
