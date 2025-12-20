"""Avatar management for Kid Fax contact images.

This module handles storage, processing, and retrieval of contact avatar images
for printing on SMS receipts.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from PIL import Image

__all__ = ["get_avatar_path", "process_avatar", "delete_avatar", "ensure_avatar_dir", "_process_image"]

LOGGER = logging.getLogger(__name__)


def get_avatar_dir() -> Path:
    """Get the avatar storage directory path from environment or default."""
    default_dir = Path.home() / ".kidfax_avatars"
    avatar_dir = os.getenv("AVATAR_DIR", str(default_dir))
    return Path(avatar_dir)


def get_avatar_size() -> int:
    """Get the target avatar size from environment or default."""
    size_str = os.getenv("AVATAR_SIZE", "96")
    try:
        size = int(size_str)
        # Validate size is reasonable (between 32 and 256 pixels)
        if 32 <= size <= 256:
            return size
        LOGGER.warning(f"AVATAR_SIZE {size} out of range, using default 96")
        return 96
    except ValueError:
        LOGGER.warning(f"Invalid AVATAR_SIZE '{size_str}', using default 96")
        return 96


def ensure_avatar_dir() -> None:
    """Create avatar directory if it doesn't exist."""
    avatar_dir = get_avatar_dir()
    avatar_dir.mkdir(parents=True, exist_ok=True)
    LOGGER.info(f"Avatar directory: {avatar_dir}")


def get_avatar_path(contact_name: str) -> Optional[Path]:
    """
    Get path to avatar image for a contact.

    Args:
        contact_name: Name of the contact (case-insensitive lookup)

    Returns:
        Path to avatar PNG file if exists, None otherwise
    """
    if not contact_name:
        return None

    avatar_dir = get_avatar_dir()
    if not avatar_dir.exists():
        return None

    # Try exact match first
    exact_path = avatar_dir / f"{contact_name}.png"
    if exact_path.exists():
        return exact_path

    # Try case-insensitive match
    contact_lower = contact_name.lower()
    for avatar_file in avatar_dir.glob("*.png"):
        if avatar_file.stem.lower() == contact_lower:
            return avatar_file

    return None


def _process_image(source: Image.Image, target_size: int = 96) -> Image.Image:
    """
    Process any PIL image for thermal printing (dithering, resizing).

    This is a reusable image processing pipeline used by both avatar uploads
    and Telegram photo printing. Converts images to 1-bit monochrome with
    Floyd-Steinberg dithering for optimal thermal printer output.

    Args:
        source: PIL Image object
        target_size: Target dimension in pixels (creates square image)

    Returns:
        Processed 1-bit PNG Image ready for printing
    """
    # Step 1: Convert to RGB (remove alpha/transparency)
    if source.mode not in ("RGB", "L"):
        img = source.convert("RGB")
    elif source.mode == "L":
        # Grayscale images convert to RGB for consistent processing
        img = source.convert("RGB")
    else:
        img = source

    # Step 2: Resize maintaining aspect ratio
    img.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)

    # Step 3: Center on white canvas
    canvas = Image.new("RGB", (target_size, target_size), (255, 255, 255))
    offset_x = (target_size - img.width) // 2
    offset_y = (target_size - img.height) // 2
    canvas.paste(img, (offset_x, offset_y))

    # Step 4: Dither to monochrome (thermal printer)
    # This creates the pixel art aesthetic perfect for thermal printers
    dithered = canvas.convert("1", dither=Image.Dither.FLOYDSTEINBERG)

    return dithered


def process_avatar(uploaded_file, contact_name: str) -> Path:
    """
    Process uploaded image for thermal printer.

    Converts any image to a 1-bit monochrome PNG optimized for thermal printing
    with a retro pixel art aesthetic.

    Processing steps:
    1. Load image with PIL
    2. Convert to RGB (remove alpha channel)
    3. Resize to target size, preserving aspect ratio
    4. Center on square canvas if not square
    5. Convert to 1-bit monochrome using Floyd-Steinberg dithering
    6. Save to avatar directory

    Args:
        uploaded_file: File-like object or path to image
        contact_name: Name of the contact (used for filename)

    Returns:
        Path to the saved avatar image

    Raises:
        ValueError: If image cannot be processed
        OSError: If avatar directory cannot be created
    """
    if not contact_name:
        raise ValueError("Contact name is required")

    # Get target size
    target_size = get_avatar_size()

    try:
        # Load image
        img = Image.open(uploaded_file)
        LOGGER.info(
            f"Processing avatar for '{contact_name}': "
            f"{img.size} {img.mode} → {target_size}x{target_size} 1-bit"
        )

        # Process using shared pipeline
        processed = _process_image(img, target_size=target_size)

        # Ensure avatar directory exists
        avatar_dir = get_avatar_dir()
        avatar_dir.mkdir(parents=True, exist_ok=True)

        # Save to avatar directory
        avatar_path = avatar_dir / f"{contact_name}.png"
        processed.save(avatar_path, "PNG")

        LOGGER.info(f"Avatar saved: {avatar_path} ({avatar_path.stat().st_size} bytes)")
        return avatar_path

    except Exception as exc:
        LOGGER.error(f"Failed to process avatar for '{contact_name}': {exc}")
        raise ValueError(f"Could not process image: {exc}") from exc


def delete_avatar(contact_name: str) -> bool:
    """
    Delete avatar image for a contact.

    Args:
        contact_name: Name of the contact

    Returns:
        True if avatar was deleted, False if it didn't exist
    """
    avatar_path = get_avatar_path(contact_name)

    if not avatar_path or not avatar_path.exists():
        LOGGER.warning(f"No avatar found for '{contact_name}'")
        return False

    try:
        avatar_path.unlink()
        LOGGER.info(f"Deleted avatar: {avatar_path}")
        return True
    except Exception as exc:
        LOGGER.error(f"Failed to delete avatar for '{contact_name}': {exc}")
        return False


def list_avatars() -> dict[str, Path]:
    """
    List all available avatars.

    Returns:
        Dictionary mapping contact names to avatar paths
    """
    avatar_dir = get_avatar_dir()
    if not avatar_dir.exists():
        return {}

    avatars = {}
    for avatar_file in avatar_dir.glob("*.png"):
        contact_name = avatar_file.stem
        avatars[contact_name] = avatar_file

    return avatars
