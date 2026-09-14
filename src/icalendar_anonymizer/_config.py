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
"""Set of field names that can be configured with field_modes parameter.

Contains 10 fields: SUMMARY, DESCRIPTION, LOCATION, COMMENT, CONTACT,
RESOURCES, CATEGORIES, ATTENDEE, ORGANIZER, and UID.
"""

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
}
"""Default placeholder values used in REPLACE mode.

Maps field names to their placeholder strings. UID uses a counter for
uniqueness: redacted-1@anonymous.local, redacted-2@anonymous.local, etc.
"""


def validate_field_modes_against(
    field_modes: dict[str, str] | None,
    allowed_fields: frozenset[str],
    forbid_remove_fields: frozenset[str] = frozenset(),
) -> dict[str, AnonymizeMode] | None:
    """Validate and normalize a field_modes dict against a given field vocabulary.

    Shared by `validate_field_modes` (iCalendar fields) and JSCalendar's
    own field-mode validator, since the normalization algorithm is the
    same, only the allowed field names differ.

    Args:
        field_modes: Dict mapping field name to mode string
        allowed_fields: Set of valid field names (uppercase)
        forbid_remove_fields: Fields that cannot use REMOVE mode

    Returns:
        Normalized dict with uppercase keys and AnonymizeMode values

    Raises:
        ValueError: If invalid field name, invalid mode, or a forbidden
            field/mode combination
        TypeError: If field_modes is not a dict or None
    """
    if field_modes is None:
        return None

    if not isinstance(field_modes, dict):
        raise TypeError(f"field_modes must be dict or None, got {type(field_modes).__name__}")

    result = {}
    for field, mode in field_modes.items():
        upper_field = field.upper()

        if upper_field not in allowed_fields:
            raise ValueError(f"Unknown field '{field}'. Valid: {sorted(allowed_fields)}")

        try:
            mode_enum = AnonymizeMode(mode.lower())
        except ValueError:
            valid = [m.value for m in AnonymizeMode]
            raise ValueError(f"Invalid mode '{mode}'. Valid: {valid}") from None

        if upper_field in forbid_remove_fields and mode_enum == AnonymizeMode.REMOVE:
            raise ValueError(f"{upper_field} cannot be removed (would break recurring events)")

        result[upper_field] = mode_enum

    return result or None


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
    return validate_field_modes_against(
        field_modes, CONFIGURABLE_FIELDS, forbid_remove_fields=frozenset({"UID"})
    )
