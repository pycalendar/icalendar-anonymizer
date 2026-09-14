# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""jCal (RFC 7265) anonymization support.

jCal is a lossless JSON encoding of iCalendar's own property model, so
anonymization is delegated entirely to the existing `anonymize()` engine:
parse jCal into a `Calendar`, anonymize unchanged, serialize back to jCal.
No jCal-specific anonymization logic exists or is needed.
"""

from icalendar import Calendar
from icalendar.error import JCalParsingError

from icalendar_anonymizer.anonymizer import anonymize


def anonymize_jcal(
    data: list,
    salt: bytes | None = None,
    field_modes: dict[str, str] | None = None,
) -> list:
    """Anonymize a jCal (RFC 7265) document.

    jCal is a direct JSON encoding of iCalendar's property model, so this
    reuses the same field names and modes as `anonymize()` for .ics input
    (SUMMARY, DESCRIPTION, ATTENDEE, etc.). jCal property names are
    lowercase per RFC 7265, but `anonymize()` already treats field names
    case-insensitively.

    Args:
        data: Parsed jCal document, e.g. `["vcalendar", [...], [...]]` as
            produced by `json.loads()` of jCal JSON text, or an
            equivalent Python list structure.
        salt: Optional salt for hashing. If None, generates random salt.
        field_modes: Optional dict mapping field names to anonymization
            modes. Same shape and vocabulary as `anonymize()`'s field_modes.

    Returns:
        New anonymized jCal document (same list-of-lists shape).

    Raises:
        TypeError: If data is not a list, or salt is not bytes.
        ValueError: If data is not a valid jCal document, or field_modes
            contains invalid fields/modes.
    """
    if not isinstance(data, list):
        raise TypeError(f"data must be a list (jCal document), got {type(data).__name__}")

    try:
        cal = Calendar.from_jcal(data)
    except JCalParsingError as e:
        raise ValueError(f"Invalid jCal document: {e}") from e

    # Calendar.from_jcal() is typed to return the base Component (it can in
    # principle parse a bare subcomponent), but a well-formed jCal document
    # for anonymize_jcal's own documented input shape always starts with
    # "vcalendar" and comes back as a Calendar; anonymize() itself already
    # enforces this with a runtime isinstance check.
    if not isinstance(cal, Calendar):
        raise ValueError(  # noqa: TRY004
            f"Invalid jCal document: expected a vcalendar, got {cal.name}"
        )

    anonymized_cal = anonymize(cal, salt=salt, field_modes=field_modes)

    return anonymized_cal.to_jcal()
