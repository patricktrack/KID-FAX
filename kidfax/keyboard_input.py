#!/usr/bin/env python3
"""Keyboard input handling for Kid Fax interactive messaging."""
from __future__ import annotations

import logging
import os
from typing import Dict, Optional

LOG = logging.getLogger("kidfax.keyboard")


def _parse_contacts(raw: str) -> Dict[str, str]:
    """
    Parse CONTACTS environment variable into name→number mapping.

    Args:
        raw: Comma-separated contacts in format "name:+15551234567,..."

    Returns:
        Dictionary mapping contact names to phone numbers

    Example:
        >>> _parse_contacts("grandma:+15551112222,uncle:+15553334444")
        {'grandma': '+15551112222', 'uncle': '+15553334444'}
    """
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


def load_contacts(limit: int = 12) -> Dict[str, str]:
    """
    Load contacts from CONTACTS environment variable.

    Args:
        limit: Maximum number of contacts to load (default 12 for F1-F12)

    Returns:
        Dictionary of contact name → phone number (limited to first N contacts)

    Raises:
        RuntimeError: If CONTACTS environment variable is not set or empty
    """
    raw = os.getenv("CONTACTS", "")
    if not raw:
        raise RuntimeError(
            "CONTACTS environment variable required for keyboard mode. "
            "Example: CONTACTS=grandma:+15551112222,uncle:+15553334444"
        )

    contacts = _parse_contacts(raw)
    if not contacts:
        raise RuntimeError(
            f"No valid contacts parsed from CONTACTS={raw}. "
            "Expected format: name:+15551234567,name2:+15559998888"
        )

    # Limit to first N contacts (F1-F12 constraint)
    limited = dict(list(contacts.items())[:limit])

    LOG.info("Loaded %d contacts (limit=%d): %s",
             len(limited), limit, ", ".join(limited.keys()))

    return limited


def map_fkeys_to_contacts(contacts: Dict[str, str]) -> Dict[str, str]:
    """
    Map function keys (F1-F12) to contact names in order.

    Args:
        contacts: Dictionary of contact name → phone number

    Returns:
        Dictionary mapping F-key names to contact names
        Example: {"F1": "grandma", "F2": "uncle", ...}

    Note:
        Maximum 12 contacts supported (F1-F12).
        If more than 12 contacts provided, only first 12 are mapped.
    """
    fkey_map: Dict[str, str] = {}
    contact_names = sorted(contacts.keys())[:12]  # Max 12 for F1-F12

    for i, contact_name in enumerate(contact_names, start=1):
        fkey = f"F{i}"
        fkey_map[fkey] = contact_name

    LOG.debug("F-key mapping: %s", fkey_map)

    return fkey_map


def get_contact_from_fkey(
    fkey_name: str,
    fkey_map: Dict[str, str],
    contacts: Dict[str, str],
) -> Optional[tuple[str, str]]:
    """
    Get contact name and phone number from F-key press.

    Args:
        fkey_name: Function key name (e.g., "F1", "F2")
        fkey_map: Dictionary mapping F-keys to contact names
        contacts: Dictionary mapping contact names to phone numbers

    Returns:
        Tuple of (contact_name, phone_number) or None if not found

    Example:
        >>> fkey_map = {"F1": "grandma"}
        >>> contacts = {"grandma": "+15551112222"}
        >>> get_contact_from_fkey("F1", fkey_map, contacts)
        ('grandma', '+15551112222')
    """
    contact_name = fkey_map.get(fkey_name)
    if not contact_name:
        LOG.warning("No contact mapped to %s", fkey_name)
        return None

    phone_number = contacts.get(contact_name)
    if not phone_number:
        LOG.error("Contact %s has no phone number", contact_name)
        return None

    return (contact_name, phone_number)


def is_function_key(key) -> Optional[str]:
    """
    Check if pressed key is a function key (F1-F12).

    Args:
        key: pynput keyboard key object

    Returns:
        F-key name (e.g., "F1") if function key, None otherwise

    Example:
        >>> from pynput import keyboard
        >>> is_function_key(keyboard.Key.f1)
        'F1'
        >>> is_function_key(keyboard.KeyCode.from_char('a'))
        None
    """
    try:
        # pynput represents function keys as keyboard.Key.f1, f2, etc.
        from pynput import keyboard

        if key in [
            keyboard.Key.f1,
            keyboard.Key.f2,
            keyboard.Key.f3,
            keyboard.Key.f4,
            keyboard.Key.f5,
            keyboard.Key.f6,
            keyboard.Key.f7,
            keyboard.Key.f8,
            keyboard.Key.f9,
            keyboard.Key.f10,
            keyboard.Key.f11,
            keyboard.Key.f12,
        ]:
            # Extract F-key number from key name
            # keyboard.Key.f1.name → "f1" → "F1"
            return key.name.upper()

        return None

    except Exception as exc:
        LOG.debug("Error checking function key: %s", exc)
        return None


class MessageComposer:
    """
    Interactive message composer with keyboard input.

    Handles:
    - Function key (F1-F12) recipient selection
    - Text input with character limit
    - Backspace for deletion
    - Enter to send
    - ESC to cancel
    """

    def __init__(self, contacts: Dict[str, str], char_limit: int = 160):
        """
        Initialize message composer.

        Args:
            contacts: Dictionary of contact name → phone number
            char_limit: SMS character limit (default 160)
        """
        self.contacts = contacts
        self.fkey_map = map_fkeys_to_contacts(contacts)
        self.char_limit = char_limit

        # State
        self.selected_recipient: Optional[str] = None
        self.selected_number: Optional[str] = None
        self.message_buffer: list[str] = []

        LOG.info("MessageComposer initialized with %d contacts", len(contacts))

    def select_recipient_by_fkey(self, fkey_name: str) -> bool:
        """
        Select recipient by function key.

        Args:
            fkey_name: Function key name (e.g., "F1")

        Returns:
            True if recipient selected, False if invalid key
        """
        result = get_contact_from_fkey(fkey_name, self.fkey_map, self.contacts)
        if result:
            self.selected_recipient, self.selected_number = result
            self.message_buffer = []  # Clear message buffer
            LOG.info("Selected recipient: %s (%s)",
                     self.selected_recipient, self.selected_number)
            return True
        return False

    def add_character(self, char: str) -> bool:
        """
        Add character to message buffer.

        Args:
            char: Single character to add

        Returns:
            True if added, False if at character limit
        """
        if len(self.message_buffer) >= self.char_limit:
            LOG.debug("Character limit reached (%d)", self.char_limit)
            return False

        self.message_buffer.append(char)
        return True

    def delete_character(self) -> bool:
        """
        Delete last character from message buffer (backspace).

        Returns:
            True if character deleted, False if buffer empty
        """
        if self.message_buffer:
            self.message_buffer.pop()
            return True
        return False

    def get_message(self) -> str:
        """Get current message text."""
        return ''.join(self.message_buffer)

    def clear_message(self) -> None:
        """Clear message buffer."""
        self.message_buffer = []

    def reset(self) -> None:
        """Reset composer state (clear recipient and message)."""
        self.selected_recipient = None
        self.selected_number = None
        self.message_buffer = []
        LOG.debug("Composer reset")

    def is_ready_to_send(self) -> bool:
        """Check if message is ready to send (has recipient and text)."""
        return bool(self.selected_recipient and self.message_buffer)

    def get_recipient_info(self) -> Optional[tuple[str, str]]:
        """
        Get selected recipient information.

        Returns:
            Tuple of (name, phone_number) or None if no recipient selected
        """
        if self.selected_recipient and self.selected_number:
            return (self.selected_recipient, self.selected_number)
        return None
