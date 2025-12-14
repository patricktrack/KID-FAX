#!/usr/bin/env python3
"""Configuration management for Kid Fax .env files."""
from __future__ import annotations

import logging
import os
import re
import shutil
from pathlib import Path
from typing import Dict, Set, Tuple

LOG = logging.getLogger("kidfax.config")

# Phone number validation regex (E.164 format)
PHONE_REGEX = re.compile(r'^\+[1-9]\d{1,14}$')


def parse_contacts(raw: str) -> Dict[str, str]:
    """
    Parse CONTACTS environment variable into name→number mapping.

    Args:
        raw: Comma-separated contacts in format "name:+15551234567,..."

    Returns:
        Dictionary mapping contact names to phone numbers

    Example:
        >>> parse_contacts("grandma:+15551112222,uncle:+15553334444")
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


def serialize_contacts(contacts: Dict[str, str]) -> str:
    """
    Convert contacts dict to CONTACTS env var format.

    Args:
        contacts: Dictionary mapping contact names to phone numbers

    Returns:
        Comma-separated string "name:number,name2:number2"

    Example:
        >>> serialize_contacts({"grandma": "+15551112222"})
        'grandma:+15551112222'
    """
    return ','.join(f"{name}:{number}" for name, number in contacts.items())


def parse_allowlist(raw: str) -> Set[str]:
    """
    Parse ALLOWLIST environment variable into set of phone numbers.

    Args:
        raw: Comma-separated phone numbers

    Returns:
        Set of phone numbers

    Example:
        >>> parse_allowlist("+15551112222,+15553334444")
        {'+15551112222', '+15553334444'}
    """
    return {item.strip() for item in raw.split(',') if item.strip()}


def serialize_allowlist(numbers: Set[str]) -> str:
    """
    Convert phone number set to ALLOWLIST env var format.

    Args:
        numbers: Set of phone numbers

    Returns:
        Comma-separated string

    Example:
        >>> serialize_allowlist({"+15551112222", "+15553334444"})
        '+15551112222,+15553334444'
    """
    return ','.join(sorted(numbers))


def validate_phone_number(number: str) -> Tuple[bool, str]:
    """
    Validate phone number in E.164 format.

    Args:
        number: Phone number string

    Returns:
        Tuple of (valid: bool, error_message: str)

    Example:
        >>> validate_phone_number("+15551234567")
        (True, '')
        >>> validate_phone_number("555-123-4567")
        (False, 'Phone number must start with + (E.164 format)')
    """
    if not number:
        return (False, "Phone number is required")

    if not number.startswith('+'):
        return (False, "Phone number must start with + (E.164 format)")

    if not PHONE_REGEX.match(number):
        return (False, "Invalid phone format. Use E.164: +1234567890 (1-15 digits)")

    return (True, "")


def validate_contact_name(name: str) -> Tuple[bool, str]:
    """
    Validate contact name.

    Args:
        name: Contact name string

    Returns:
        Tuple of (valid: bool, error_message: str)
    """
    if not name:
        return (False, "Contact name is required")

    if ':' in name or ',' in name:
        return (False, "Contact name cannot contain ':' or ','")

    if len(name) > 50:
        return (False, "Contact name too long (max 50 characters)")

    return (True, "")


def load_env_config(env_path: str = ".env") -> Dict[str, str]:
    """
    Load .env file into dictionary.

    Args:
        env_path: Path to .env file (default: ".env")

    Returns:
        Dictionary of environment variables

    Raises:
        FileNotFoundError: If .env file doesn't exist
    """
    path = Path(env_path)
    if not path.exists():
        raise FileNotFoundError(f".env file not found at {path}")

    config = {}
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            # Parse KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()

    LOG.debug(f"Loaded {len(config)} variables from {env_path}")
    return config


def save_env_config(
    contacts: Dict[str, str],
    allowlist: Set[str],
    env_path: str = ".env"
) -> None:
    """
    Safely update .env file while preserving structure.

    Strategy:
    1. Read entire .env file line by line
    2. Identify lines to update (CONTACTS=..., ALLOWLIST=...)
    3. Replace only those lines
    4. Preserve all other lines and comments
    5. Write to temp file
    6. Atomic rename to .env

    Args:
        contacts: Dictionary of contact name → phone number
        allowlist: Set of allowed phone numbers
        env_path: Path to .env file (default: ".env")

    Raises:
        FileNotFoundError: If .env file doesn't exist
    """
    path = Path(env_path)
    if not path.exists():
        raise FileNotFoundError(f".env file not found at {path}")

    # Backup original
    backup_path = Path(f"{env_path}.backup")
    shutil.copy(path, backup_path)
    LOG.info(f"Created backup at {backup_path}")

    # Serialize new values
    contacts_str = serialize_contacts(contacts)
    allowlist_str = serialize_allowlist(allowlist)

    # Read original lines
    with open(path, 'r') as f:
        lines = f.readlines()

    # Update specific lines
    updated_lines = []
    contacts_found = False
    allowlist_found = False

    for line in lines:
        if line.strip().startswith('CONTACTS='):
            updated_lines.append(f"CONTACTS={contacts_str}\n")
            contacts_found = True
        elif line.strip().startswith('ALLOWLIST='):
            updated_lines.append(f"ALLOWLIST={allowlist_str}\n")
            allowlist_found = True
        else:
            updated_lines.append(line)

    # If CONTACTS or ALLOWLIST not found, append them
    if not contacts_found:
        updated_lines.append(f"\nCONTACTS={contacts_str}\n")
        LOG.warning("CONTACTS not found in .env, appending")

    if not allowlist_found:
        updated_lines.append(f"ALLOWLIST={allowlist_str}\n")
        LOG.warning("ALLOWLIST not found in .env, appending")

    # Atomic write
    temp_path = Path(f"{env_path}.tmp")
    with open(temp_path, 'w') as f:
        f.writelines(updated_lines)

    # Rename temp to final
    temp_path.rename(path)

    LOG.info(f"Saved .env config (backup at {backup_path})")


def get_contacts_from_env(env_path: str = ".env") -> Dict[str, str]:
    """
    Load contacts from .env file.

    Args:
        env_path: Path to .env file

    Returns:
        Dictionary of contact name → phone number
    """
    config = load_env_config(env_path)
    contacts_raw = config.get("CONTACTS", "")
    return parse_contacts(contacts_raw)


def get_allowlist_from_env(env_path: str = ".env") -> Set[str]:
    """
    Load allowlist from .env file.

    Args:
        env_path: Path to .env file

    Returns:
        Set of allowed phone numbers
    """
    config = load_env_config(env_path)
    allowlist_raw = config.get("ALLOWLIST", "")
    return parse_allowlist(allowlist_raw)
