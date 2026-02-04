# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Configuration types for anonymization."""

from enum import StrEnum


class AnonymizeMode(StrEnum):
    """Anonymization mode for a configurable field."""

    KEEP = "keep"
    REMOVE = "remove"
    RANDOMIZE = "randomize"
    REPLACE = "replace"


# Fields that can be configured (from ANONYMIZED_PROPERTIES)
CONFIGURABLE_FIELDS = frozenset(
    {
        "SUMMARY",
        "DESCRIPTION",
        "LOCATION",
        "COMMENT",
        "CONTACT",
        "RESOURCES",
        "CATEGORIES",
        "ATTENDEE",
        "ORGANIZER",
        "UID",
    }
)

# Default placeholders for REPLACE mode
DEFAULT_PLACEHOLDERS = {
    "SUMMARY": "[Redacted]",
    "DESCRIPTION": "[Content removed]",
    "LOCATION": "[Location removed]",
    "COMMENT": "[Comment removed]",
    "CONTACT": "[Contact removed]",
    "RESOURCES": "[Resources removed]",
    "CATEGORIES": "REDACTED",
    "ATTENDEE": "mailto:redacted@example.local",
    "ORGANIZER": "mailto:redacted@example.local",
    # UID handled specially with counter
}


def validate_field_modes(
    field_modes: dict[str, str] | None,
) -> dict[str, AnonymizeMode] | None:
    """Validate and normalize field_modes dict.

    Args:
        field_modes: Dict mapping field name to mode string

    Returns:
        Normalized dict with uppercase keys and AnonymizeMode values

    Raises:
        ValueError: If invalid field name, invalid mode, or UID set to remove
        TypeError: If field_modes is not a dict or None
    """
    if field_modes is None:
        return None

    if not isinstance(field_modes, dict):
        raise TypeError(f"field_modes must be dict or None, got {type(field_modes).__name__}")

    result = {}
    for field, mode in field_modes.items():
        upper_field = field.upper()

        if upper_field not in CONFIGURABLE_FIELDS:
            raise ValueError(f"Unknown field '{field}'. Valid: {sorted(CONFIGURABLE_FIELDS)}")

        try:
            mode_enum = AnonymizeMode(mode.lower())
        except ValueError:
            valid = [m.value for m in AnonymizeMode]
            raise ValueError(f"Invalid mode '{mode}'. Valid: {valid}") from None

        if upper_field == "UID" and mode_enum == AnonymizeMode.REMOVE:
            raise ValueError("UID cannot be removed (would break recurring events)")

        result[upper_field] = mode_enum

    return result or None
