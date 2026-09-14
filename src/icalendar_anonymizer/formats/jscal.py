# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""JSCalendar (RFC 8984) anonymization support.

JSCalendar's JSON shape is structurally different from iCalendar's flat
property model (participants are a map keyed by role flags rather than
separate ATTENDEE/ORGANIZER properties, locations are a map rather than
a single value, and so on), so this module walks the JSCalendar document
directly rather than converting to iCalendar and reusing `anonymize()`.

Converting to iCalendar and back was considered and rejected: verified
directly against calendaring-jmap 1.0.0 that its converter silently
drops ATTACH/URL/CONFERENCE-equivalent data (links, virtualLocations) in
both directions, and loses participant/location changes on individual
recurrence-override instances, keeping only title/start/duration/
description (tracked upstream as calendaring-jmap issues #19 and #20).
A lossy round trip would delete real user data from anonymized output,
not just fail to anonymize it, which is unacceptable for a privacy tool.
"""

import copy

from icalendar_anonymizer._config import DEFAULT_PLACEHOLDERS, validate_field_modes_against
from icalendar_anonymizer._hash import (
    generate_salt,
    hash_email,
    hash_mailto_address,
    hash_text,
    hash_uid,
)

JSCAL_CONFIGURABLE_FIELDS = frozenset(
    {
        "TITLE",
        "DESCRIPTION",
        "LOCATIONS",
        "PARTICIPANTS",
        "KEYWORDS",
        "LINKS",
        "VIRTUALLOCATIONS",
        "UID",
    }
)
"""Set of JSCalendar field names that can be configured with field_modes.

Contains 8 fields: TITLE, DESCRIPTION, LOCATIONS, PARTICIPANTS, KEYWORDS,
LINKS, VIRTUALLOCATIONS, and UID. This is JSCalendar's own field
vocabulary, structurally different from iCalendar's CONFIGURABLE_FIELDS
in _config.py, since JSCalendar's property shapes differ (participants
is one map for both organizer and attendees, locations is a map rather
than a single value, and so on).
"""

_JSCAL_PRESERVED_FIELDS = frozenset(
    {
        # Shared by Event, Task, and Group (RFC 8984 sections 4, 5, 6)
        "START",
        "DURATION",
        "TIMEZONE",
        "SHOWWITHOUTTIME",
        "RECURRENCERULES",
        "EXCLUDEDRECURRENCERULES",
        "SEQUENCE",
        "STATUS",
        "PRIVACY",
        "FREEBUSYSTATUS",
        "COLOR",
        # Task-specific (RFC 8984 section 5.2)
        "DUE",
        "ESTIMATEDDURATION",
        "PERCENTCOMPLETE",
        "PROGRESS",
        "PROGRESSUPDATED",
    }
)

_JSCAL_PARTICIPANT_PRESERVED_FIELDS = frozenset(
    {"ROLES", "PARTICIPATIONSTATUS", "EXPECTREPLY", "SCHEDULEAGENT", "SCHEDULESTATUS", "KIND"}
)

_JSCAL_PLACEHOLDERS = {
    "PARTICIPANT_NAME": "[Redacted]",
    "LINK": "[Redacted]",
}
"""Placeholder text for REPLACE mode, for concepts with no iCalendar
equivalent in `_config.DEFAULT_PLACEHOLDERS` (a participant's free-text
name, and a link's title/description). Checked before DEFAULT_PLACEHOLDERS
so JSCalendar-only fields don't depend on falling through to its generic
default.
"""


def validate_jscal_field_modes(field_modes: dict[str, str] | None):
    """Validate and normalize a JSCalendar field_modes dict.

    Same validation algorithm as `_config.validate_field_modes`, applied
    to JSCalendar's own field vocabulary instead of iCalendar's.

    Args:
        field_modes: Dict mapping JSCalendar field name to mode string

    Returns:
        Normalized dict with uppercase keys and AnonymizeMode values

    Raises:
        ValueError: If invalid field name, invalid mode, or UID set to remove
        TypeError: If field_modes is not a dict or None
    """
    return validate_field_modes_against(
        field_modes, JSCAL_CONFIGURABLE_FIELDS, forbid_remove_fields=frozenset({"UID"})
    )


def anonymize_jscal(
    data: dict,
    salt: bytes | None = None,
    field_modes: dict[str, str] | None = None,
) -> dict:
    """Anonymize a JSCalendar (RFC 8984) document.

    Walks the JSCalendar JSON structure directly. Never converts to or
    from iCalendar, since round-tripping through iCalendar silently
    drops ATTACH/URL/CONFERENCE-equivalent data and per-instance
    recurrence override fields (verified against calendaring-jmap 1.0.0,
    tracked as calendaring-jmap issues #19 and #20).

    Args:
        data: Parsed JSCalendar document (a dict, e.g. an Event object
            per RFC 8984, as produced by `json.loads()`).
        salt: Optional salt for hashing. If None, generates random salt.
        field_modes: Optional dict mapping JSCalendar field names to
            anonymization modes. Fields: TITLE, DESCRIPTION, LOCATIONS,
            PARTICIPANTS, KEYWORDS, LINKS, VIRTUALLOCATIONS, UID.
            Modes: keep, remove, randomize, replace.

    Returns:
        New anonymized JSCalendar document (same dict shape).

    Raises:
        TypeError: If data is not a dict, or salt is not bytes.
        ValueError: If field_modes contains invalid fields/modes.
    """
    if not isinstance(data, dict):
        raise TypeError(f"data must be a dict (JSCalendar document), got {type(data).__name__}")
    if salt is None:
        salt = generate_salt()
    elif not isinstance(salt, bytes):
        raise TypeError(f"salt must be bytes, got {type(salt).__name__}")

    modes = validate_jscal_field_modes(field_modes) or {}
    uid_map: dict[str, str] = {}
    uid_counter = [0]

    return _anonymize_jscal_object(data, salt, modes, uid_map, uid_counter)


def _anonymize_jscal_object(
    obj: dict, salt: bytes, modes: dict, uid_map: dict[str, str], uid_counter: list[int]
) -> dict:
    """Recursively anonymize one JSCalendar object (an Event, or a patch)."""
    new_obj = dict(obj)

    for key, value in obj.items():
        upper_key = key.upper()

        if key == "@type":
            continue
        if upper_key == "UID":
            new_obj[key] = _apply_uid_mode(
                value, modes.get("UID", "randomize"), salt, uid_map, uid_counter
            )
        elif upper_key in ("TITLE", "DESCRIPTION"):
            placeholder_field = "SUMMARY" if upper_key == "TITLE" else "DESCRIPTION"
            new_obj[key] = _apply_text_mode(
                value, upper_key, placeholder_field, modes.get(upper_key, "randomize"), salt
            )
        elif upper_key == "LOCATIONS":
            new_obj[key] = _anonymize_locations(value, modes.get("LOCATIONS", "randomize"), salt)
        elif upper_key == "PARTICIPANTS":
            new_obj[key] = _anonymize_participants(
                value, modes.get("PARTICIPANTS", "randomize"), salt
            )
        elif upper_key == "KEYWORDS":
            new_obj[key] = _anonymize_keywords(
                value, "keywords", modes.get("KEYWORDS", "randomize"), salt
            )
        elif upper_key in ("LINKS", "VIRTUALLOCATIONS"):
            new_obj[key] = _anonymize_links(value, key, modes.get(upper_key, "randomize"), salt)
        elif upper_key == "RECURRENCEOVERRIDES":
            _require_dict(value, "recurrenceOverrides")
            new_obj[key] = {}
            for dt_key, patch in value.items():
                _require_dict(patch, f"recurrenceOverrides.{dt_key}")
                new_obj[key][dt_key] = _anonymize_jscal_object(
                    patch, salt, modes, uid_map, uid_counter
                )
        elif upper_key == "ENTRIES":
            # A Group's entries (RFC 8984 section 6.1) are full Event/Task
            # objects, not an arbitrary list, so each one needs the same
            # object-level anonymization as the top-level document, not the
            # generic key/value hashing _anonymize_unknown_value would give
            # an ordinary unrecognized list.
            if not isinstance(value, list):
                raise TypeError(f"entries must be an array, got {type(value).__name__}")
            new_obj[key] = []
            for index, entry in enumerate(value):
                _require_dict(entry, f"entries[{index}]")
                new_obj[key].append(
                    _anonymize_jscal_object(entry, salt, modes, uid_map, uid_counter)
                )
        elif upper_key in _JSCAL_PRESERVED_FIELDS:
            # Deep-copied, not left as the shallow dict(obj) copy above: a
            # preserved value like recurrenceRules is a list of dicts, and
            # anonymize()'s contract is that the result never shares mutable
            # state with the input, so mutating the result can't mutate it.
            new_obj[key] = copy.deepcopy(value)
        else:
            new_obj[key] = _anonymize_unknown_value(value, salt)

    return new_obj


def _anonymize_unknown_value(value, salt: bytes):
    """Recursively anonymize an unrecognized field of any JSON shape.

    Strings are hashed as text; dicts and lists are walked recursively
    so their own nested strings are hashed too; numbers, booleans, and
    None pass through unchanged, since they carry no free-text personal
    data by nature. Dict keys are hashed too, not just values: a vendor
    or future RFC 8984 extension property could put personal data (an
    email address, a name) in a key rather than a value, and the same
    default-deny reasoning applies to both.
    """
    if isinstance(value, str):
        return hash_text(value, salt)
    if isinstance(value, dict):
        return {
            (hash_text(k, salt) if isinstance(k, str) else k): _anonymize_unknown_value(v, salt)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_anonymize_unknown_value(v, salt) for v in value]
    return value


def _apply_uid_mode(
    value: str, mode: str, salt: bytes, uid_map: dict[str, str], uid_counter: list[int]
) -> str:
    if mode == "keep":
        return value
    _require_str(value, "uid")
    if mode == "replace":
        # A recurrenceOverrides patch may legitimately repeat the master
        # event's UID (RFC 8984 section 4.3.4), so the same original UID
        # must map to the same placeholder here too, exactly like the
        # randomize branch's hash_uid(uid_map=...) call below.
        if value in uid_map:
            return uid_map[value]
        uid_counter[0] += 1
        placeholder = f"redacted-{uid_counter[0]}@anonymous.local"
        uid_map[value] = placeholder
        return placeholder
    return hash_uid(value, salt, uid_map)


def _apply_text_mode(
    value: str, error_field: str, placeholder_field: str, mode: str, salt: bytes
) -> str:
    if mode == "keep":
        return value
    _require_str(value, error_field)
    if mode == "replace":
        if placeholder_field in _JSCAL_PLACEHOLDERS:
            return _JSCAL_PLACEHOLDERS[placeholder_field]
        return DEFAULT_PLACEHOLDERS.get(placeholder_field, "[Redacted]")
    return hash_text(value, salt)


def _require_str(value: object, field: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string, got {type(value).__name__}")


def _require_dict(value: object, field: str) -> None:
    if not isinstance(value, dict):
        raise TypeError(f"{field} must be an object, got {type(value).__name__}")


def _container_shortcut(container: dict, field_name: str, mode: str) -> dict | None:
    """Validate a map-shaped field and handle its keep/remove modes.

    Every map-shaped JSCalendar field (locations, participants, keywords,
    links, virtualLocations) validates its container type the same way and
    short-circuits identically for keep/remove, before diverging into
    field-specific per-entry handling. Returns the map to use as-is for
    keep/remove, or None when the caller should continue processing entries
    itself under randomize/replace.
    """
    _require_dict(container, field_name)
    if mode == "keep":
        return copy.deepcopy(container)
    if mode == "remove":
        return {}
    return None


_JSCAL_LOCATION_PRESERVED_FIELDS = frozenset({"RELATIVETO", "TIMEZONE"})


def _anonymize_locations(locations_map: dict, mode: str, salt: bytes) -> dict:
    shortcut = _container_shortcut(locations_map, "locations", mode)
    if shortcut is not None:
        return shortcut
    new_map = {}
    for uuid_key, location in locations_map.items():
        _require_dict(location, f"locations.{uuid_key}")
        new_location = {}
        for key, value in location.items():
            upper_key = key.upper()
            if key == "@type":
                new_location[key] = value
            elif key in ("name", "description"):
                new_location[key] = _apply_text_mode(
                    value, f"locations.{key}", "LOCATION", mode, salt
                )
            elif key == "coordinates":
                new_location[key] = _apply_text_mode(
                    value, "locations.coordinates", "LOCATION", mode, salt
                )
            elif key == "locationTypes":
                new_location[key] = _anonymize_keywords(
                    value, "locations.locationTypes", mode, salt
                )
            elif key == "links":
                new_location[key] = _anonymize_links(value, "locations.links", mode, salt)
            elif upper_key in _JSCAL_LOCATION_PRESERVED_FIELDS:
                new_location[key] = copy.deepcopy(value)
            else:
                new_location[key] = _anonymize_unknown_value(value, salt)
        new_map[uuid_key] = new_location
    return new_map


def _anonymize_participants(participants_map: dict, mode: str, salt: bytes) -> dict:
    shortcut = _container_shortcut(participants_map, "participants", mode)
    if shortcut is not None:
        return shortcut
    new_map = {}
    for uuid_key, participant in participants_map.items():
        _require_dict(participant, f"participants.{uuid_key}")
        new_participant = {}
        for key, value in participant.items():
            upper_key = key.upper()
            if key == "@type":
                new_participant[key] = value
            elif upper_key in _JSCAL_PARTICIPANT_PRESERVED_FIELDS:
                new_participant[key] = copy.deepcopy(value)
            elif key == "name":
                new_participant[key] = _apply_text_mode(
                    value, "participants.name", "PARTICIPANT_NAME", mode, salt
                )
            elif key == "email":
                new_participant[key] = _apply_email_mode(value, mode, salt)
            elif key == "sendTo":
                _require_dict(value, "participants.sendTo")
                new_participant[key] = {
                    protocol: _apply_scheme_uri_mode(address, mode, salt)
                    for protocol, address in value.items()
                }
            elif key == "invitedBy":
                # References another entry's key in this same participants
                # map (RFC 8984 4.4.1). Hashing it independently of that
                # key would corrupt the cross-reference. The referenced key
                # itself isn't personal data, only the surrounding names
                # and emails are, so it's preserved like the map's own keys.
                new_participant[key] = value
            else:
                new_participant[key] = _anonymize_unknown_value(value, salt)
        new_map[uuid_key] = new_participant
    return new_map


def _apply_email_mode(value: str, mode: str, salt: bytes) -> str:
    # Called only from _anonymize_participants, which already returns early
    # for "keep" and "remove" before reaching per-field helpers, mirroring
    # how anonymizer.py's _anonymize_caladdress has no KEEP/REMOVE handling
    # of its own either. Only "replace" and "randomize" (the default) can
    # reach here.
    if mode == "replace":
        return "redacted@example.local"
    _require_str(value, "email")
    return hash_email(value, salt)


def _apply_scheme_uri_mode(value: str, mode: str, salt: bytes) -> str:
    """Anonymize one sendTo address, preserving its URI scheme.

    sendTo values aren't always mailto: RFC 8984 allows tel:, xmpp:, and
    other schemes. Forcing every address into a mailto: URI on replace, or
    hashing a non-email address as if it had local@domain structure, would
    produce output that doesn't match the original protocol.
    """
    _require_str(value, "sendTo address")
    scheme, sep, rest = value.partition(":")
    if not sep:
        # No scheme at all (a bare address): treat the whole value as opaque.
        if mode == "replace":
            return "redacted@example.local"
        return hash_text(value, salt)
    if mode == "replace":
        return f"{scheme}:redacted@example.local"
    if scheme.lower() == "mailto":
        return hash_mailto_address(value, salt)
    return f"{scheme}:{hash_text(rest, salt)}"


def _anonymize_keywords(keywords_map: dict, field_name: str, mode: str, salt: bytes) -> dict:
    shortcut = _container_shortcut(keywords_map, field_name, mode)
    if shortcut is not None:
        return shortcut
    if mode == "replace":
        return {"REDACTED": True}
    for keyword in keywords_map:
        _require_str(keyword, f"{field_name} key")
    return {hash_text(keyword, salt): True for keyword in keywords_map}


_JSCAL_LINK_PRESERVED_FIELDS = frozenset({"CONTENTTYPE", "SIZE", "REL", "DISPLAY"})
_JSCAL_LINK_URI_FIELDS = frozenset({"href", "uri"})
_JSCAL_LINK_TEXT_FIELDS = frozenset({"title", "description", "name"})


def _anonymize_links(map_obj: dict, field_name: str, mode: str, salt: bytes) -> dict:
    """Anonymize a Link or VirtualLocation map (RFC 8984's links/virtualLocations).

    Both are maps of objects that identify or describe something (a URL,
    a dial-in number, a name) alongside purely structural metadata
    (contentType, size, rel, display), so the same handling covers both.
    """
    shortcut = _container_shortcut(map_obj, field_name, mode)
    if shortcut is not None:
        return shortcut
    new_map = {}
    for key, entry in map_obj.items():
        _require_dict(entry, f"{field_name}.{key}")
        new_entry = {}
        for subfield, value in entry.items():
            upper_subfield = subfield.upper()
            if subfield == "@type":
                new_entry[subfield] = value
            elif subfield in _JSCAL_LINK_URI_FIELDS:
                _require_str(value, f"{field_name}.{subfield}")
                new_entry[subfield] = (
                    "[Link removed]" if mode == "replace" else hash_text(value, salt)
                )
            elif subfield in _JSCAL_LINK_TEXT_FIELDS:
                new_entry[subfield] = _apply_text_mode(
                    value, f"{field_name}.{subfield}", "LINK", mode, salt
                )
            elif upper_subfield in _JSCAL_LINK_PRESERVED_FIELDS:
                new_entry[subfield] = copy.deepcopy(value)
            else:
                new_entry[subfield] = _anonymize_unknown_value(value, salt)
        new_map[key] = new_entry
    return new_map
