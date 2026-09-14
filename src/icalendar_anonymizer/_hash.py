# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Hash-based anonymization utilities.

Provides deterministic hashing functions that preserve structure while
removing personal information. Uses SHA-256 for consistent output.
"""

import hashlib
import secrets


def generate_salt() -> bytes:
    """Generate a random salt for this anonymization session.

    Returns:
        32 bytes of random data
    """
    return secrets.token_bytes(32)


def _hash_with_salt(data: str, salt: bytes) -> str:
    """Hash data with salt using SHA-256.

    Args:
        data: The string to hash
        salt: Salt bytes for this anonymization session

    Returns:
        Hexadecimal hash string
    """
    h = hashlib.sha256()
    h.update(salt)
    h.update(data.encode("utf-8"))
    return h.hexdigest()


def hash_text(text: str, salt: bytes) -> str:
    """Hash text while preserving word count.

    Each word is hashed separately, maintaining the structure of the text.
    Single-word inputs return a single hash word.

    Args:
        text: The text to anonymize
        salt: Salt bytes for this anonymization session

    Returns:
        Anonymized text with same word count
    """
    if not text or not text.strip():
        return text

    words = text.split()
    hashed_words = []

    for word in words:
        # Hash the word and take first 16 hex characters (64 bits) to reduce collision probability
        word_hash = _hash_with_salt(word, salt)[:16]
        hashed_words.append(word_hash)

    return " ".join(hashed_words)


def hash_email(email: str, salt: bytes) -> str:
    """Hash email while preserving structure (keeps @ and domain-like format).

    Args:
        email: The email address to anonymize
        salt: Salt bytes for this anonymization session

    Returns:
        Anonymized email with structure preserved
    """
    if not email or "@" not in email:
        # Not a valid email, just hash as text
        return _hash_with_salt(email, salt)[:16]

    local, domain = email.rsplit("@", 1)

    # Hash the local part
    local_hash = _hash_with_salt(local, salt)[:16]

    # Hash the domain but keep TLD-like structure
    if "." in domain:
        domain_parts = domain.split(".")
        # Hash the main domain, use .local per RFC 6761
        domain_hash = _hash_with_salt(domain_parts[0], salt)[:16]
        tld = "local"  # RFC 6761 reserved TLD for local/testing use
        domain_anon = f"{domain_hash}.{tld}"
    else:
        domain_anon = _hash_with_salt(domain, salt)[:16]

    return f"{local_hash}@{domain_anon}"


def hash_mailto_address(email: str, salt: bytes) -> str:
    """Hash an email address, preserving a leading mailto: if present.

    Args:
        email: The address to anonymize, with or without a mailto: prefix
        salt: Salt bytes for this anonymization session

    Returns:
        Anonymized address with the mailto: prefix preserved if it was present

    Examples:
        >>> salt = b"test_salt"
        >>> hash_mailto_address("mailto:alice@example.com", salt).startswith("mailto:")
        True
        >>> hash_mailto_address("alice@example.com", salt).startswith("mailto:")
        False
        >>> hash_mailto_address("MAILTO:Alice@Example.com", salt).startswith("MAILTO:")
        True
    """
    if email.lower().startswith("mailto:"):
        return email[:7] + hash_email(email[7:], salt)
    return hash_email(email, salt)


def hash_uid(uid: str, salt: bytes, uid_map: dict[str, str]) -> str:
    """Hash UID while maintaining uniqueness across the calendar.

    Same UID always produces the same hash within a calendar (for recurring
    events). Different UIDs produce different hashes.

    Args:
        uid: The UID to hash
        salt: Salt bytes for this anonymization session
        uid_map: Dictionary mapping original UIDs to hashed UIDs

    Returns:
        Anonymized UID (consistent for same input UID)

    Examples:
        >>> salt = b"test_salt"
        >>> uid_map = {}
        >>> uid1 = hash_uid("event1@example.com", salt, uid_map)
        >>> uid2 = hash_uid("event1@example.com", salt, uid_map)
        >>> uid1 == uid2  # Same UID produces same hash
        True
        >>> uid3 = hash_uid("event2@example.com", salt, uid_map)
        >>> uid1 != uid3  # Different UIDs produce different hashes
        True
    """
    if uid in uid_map:
        return uid_map[uid]

    # Hash the UID and create a new unique identifier
    uid_hash = _hash_with_salt(uid, salt)

    # Format as a UID (take 32 chars and add @anonymous.local)
    hashed_uid = f"{uid_hash[:32]}@anonymous.local"
    uid_map[uid] = hashed_uid

    return hashed_uid


def hash_caladdress_cn(cn: str, salt: bytes) -> str:
    """Hash the CN (Common Name) parameter of ATTENDEE/ORGANIZER.

    Args:
        cn: The common name to hash
        salt: Salt bytes for this anonymization session

    Returns:
        Anonymized common name preserving word count
    """
    return hash_text(cn, salt)
