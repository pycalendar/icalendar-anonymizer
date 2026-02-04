# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Core anonymization engine for iCalendar files.

Anonymizes personal data while preserving technical properties needed for
bug reproduction. Uses deterministic hashing with configurable salt.
"""

from icalendar import Alarm, Calendar, Event, Journal, Todo
from icalendar.cal import Component
from icalendar.prop import vCalAddress

from ._config import (
    DEFAULT_PLACEHOLDERS,
    AnonymizeMode,
    validate_field_modes,
)
from ._hash import (
    generate_salt,
    hash_caladdress_cn,
    hash_email,
    hash_text,
    hash_uid,
)
from ._properties import (
    should_preserve_component,
    should_preserve_property,
)


def anonymize(
    cal: Calendar,
    salt: bytes | None = None,
    preserve: set[str] | None = None,
    field_modes: dict[str, str] | None = None,
) -> Calendar:
    """Anonymize an iCalendar object.

    Removes personal data (names, emails, locations, descriptions) while
    preserving technical properties (dates, recurrence, timezones). Uses
    deterministic hashing so the same input produces the same output with
    the same salt.

    Args:
        cal: The Calendar object to anonymize
        salt: Optional salt for hashing. If None, generates random salt.
              Pass the same salt to get consistent output across runs.
        preserve: Optional set of additional property names to preserve.
                 Case-insensitive. User must ensure these don't contain
                 sensitive data. Example: {"CATEGORIES", "COMMENT"}
                 Cannot be used with field_modes.
        field_modes: Optional dict mapping field names to anonymization modes.
                    Modes: "keep", "remove", "randomize", "replace".
                    Fields: SUMMARY, DESCRIPTION, LOCATION, COMMENT, CONTACT,
                           RESOURCES, CATEGORIES, ATTENDEE, ORGANIZER, UID.
                    Cannot be used with preserve.

    Returns:
        New anonymized Calendar object

    Raises:
        TypeError: If cal is not a Calendar object or salt is not bytes
        ValueError: If both preserve and field_modes are specified, or if
                   field_modes contains invalid fields/modes
    """
    if not isinstance(cal, Calendar):
        raise TypeError(f"Expected Calendar, got {type(cal).__name__}")

    if salt is None:
        salt = generate_salt()
    elif not isinstance(salt, bytes):
        raise TypeError(f"salt must be bytes, got {type(salt).__name__}")

    if preserve is not None and not isinstance(preserve, set):
        raise TypeError(f"preserve must be a set or None, got {type(preserve).__name__}")

    if field_modes is not None and not isinstance(field_modes, dict):
        raise TypeError(f"field_modes must be dict or None, got {type(field_modes).__name__}")

    # Mutual exclusion check
    if preserve is not None and field_modes is not None:
        raise ValueError("Cannot specify both 'preserve' and 'field_modes'")

    # Convert preserve to field_modes internally
    if preserve:
        field_modes_normalized = {p.upper(): AnonymizeMode.KEEP for p in preserve}
    else:
        field_modes_normalized = validate_field_modes(field_modes) or {}

    # UID mapping to maintain uniqueness across calendar
    uid_map: dict[str, str] = {}

    # UID counter for REPLACE mode
    uid_counter = [0]

    # Create new calendar to avoid modifying original
    new_cal = Calendar()

    # Copy calendar-level properties (applying same filtering rules)
    # Use .items() which returns only actual properties (key-value pairs)
    # NOT .property_items() which incorrectly includes subcomponent properties,
    # causing events/todos to be copied as regular properties and creating malformed ICS output
    for key, value in cal.items():
        prop_name = key.upper()
        # Calendar-level properties use simple preserve logic (not configurable via field_modes)
        if should_preserve_property(prop_name):
            new_cal.add(key, value)
        else:
            # Anonymize calendar-level properties too
            anonymized = _anonymize_property_value(value, salt)
            new_cal.add(key, anonymized)

    # Process only top-level components (not subcomponents)
    for component in cal.subcomponents:
        # Check if this component should be completely preserved
        if should_preserve_component(component.name):
            # VTIMEZONE: preserve entirely
            new_cal.add_component(component)
            continue

        # Anonymize component
        new_component = _anonymize_component(
            component, salt, uid_map, field_modes_normalized, uid_counter
        )
        new_cal.add_component(new_component)

    return new_cal


def _anonymize_component(
    component: Component,
    salt: bytes,
    uid_map: dict[str, str],
    field_modes: dict[str, AnonymizeMode],
    uid_counter: list[int],
) -> Component:
    """Anonymize a single component (VEVENT, VTODO, etc.).

    Args:
        component: The component to anonymize
        salt: Salt for hashing
        uid_map: UID mapping for maintaining uniqueness
        field_modes: Dict mapping field names to anonymization modes
        uid_counter: Counter for generating unique placeholder UIDs

    Returns:
        New anonymized component
    """
    component_types = {
        "VEVENT": Event,
        "VTODO": Todo,
        "VJOURNAL": Journal,
        "VALARM": Alarm,
    }

    component_class = component_types.get(component.name, Component)
    new_component = component_class()

    # Process each property
    for key, value in component.property_items():
        prop_name = key.upper()

        # Skip BEGIN and END markers (structural, not properties)
        if prop_name in ("BEGIN", "END"):
            continue

        # Check if property should be preserved (technical properties)
        if should_preserve_property(prop_name):
            new_component.add(key, value)
            continue

        # Get mode for this field (default: RANDOMIZE)
        mode = field_modes.get(prop_name, AnonymizeMode.RANDOMIZE)

        if mode == AnonymizeMode.KEEP:
            new_component.add(key, value)
        elif mode == AnonymizeMode.REMOVE:
            # Don't add property - skip
            continue
        elif mode == AnonymizeMode.REPLACE:
            # Use placeholder
            if prop_name == "UID":
                uid_counter[0] += 1
                placeholder = f"redacted-{uid_counter[0]}@anonymous.local"
            elif prop_name in ("ATTENDEE", "ORGANIZER"):
                placeholder = _create_placeholder_caladdress(value, prop_name)
            else:
                placeholder = DEFAULT_PLACEHOLDERS.get(prop_name, "[Redacted]")
            new_component.add(key, placeholder)
        # Existing anonymization logic
        elif prop_name == "UID":
            new_component.add(key, hash_uid(str(value), salt, uid_map))
        elif prop_name in ("ATTENDEE", "ORGANIZER"):
            if isinstance(value, vCalAddress):
                new_component.add(key, _anonymize_caladdress(value, salt))
            else:
                new_component.add(key, hash_email(str(value), salt))
        else:
            new_component.add(key, _anonymize_property_value(value, salt))

    # Process subcomponents (e.g., VALARM inside VEVENT)
    for subcomponent in component.subcomponents:
        new_subcomponent = _anonymize_component(
            subcomponent, salt, uid_map, field_modes, uid_counter
        )
        new_component.add_component(new_subcomponent)

    return new_component


def _anonymize_property_value(value, salt: bytes):
    """Anonymize a property value.

    Args:
        value: The property value to anonymize
        salt: Salt for hashing

    Returns:
        Anonymized value
    """
    # Handle different value types
    if isinstance(value, str):
        return hash_text(value, salt)
    if isinstance(value, bytes):
        return hash_text(value.decode("utf-8", errors="replace"), salt).encode("utf-8")
    if isinstance(value, list):
        # Handle lists (like CATEGORIES)
        return [hash_text(str(item), salt) for item in value]
    # For other types, convert to string and hash
    return hash_text(str(value), salt)


def _create_placeholder_caladdress(original: vCalAddress, prop_name: str) -> vCalAddress:
    """Create placeholder vCalAddress preserving non-personal params.

    Args:
        original: The original vCalAddress
        prop_name: The property name (ATTENDEE or ORGANIZER)

    Returns:
        New vCalAddress with placeholder email and "Redacted" CN
    """
    placeholder_email = DEFAULT_PLACEHOLDERS.get(prop_name, "mailto:redacted@example.local")
    new_addr = vCalAddress(placeholder_email)

    # Copy parameters, replacing CN with "Redacted"
    for param_key, param_value in original.params.items():
        if param_key.upper() == "CN":
            new_addr.params[param_key] = "Redacted"
        else:
            # Preserve ROLE, PARTSTAT, RSVP, CUTYPE, etc.
            new_addr.params[param_key] = param_value

    return new_addr


def _anonymize_caladdress(caladdress: vCalAddress, salt: bytes) -> vCalAddress:
    """Anonymize ATTENDEE or ORGANIZER (vCalAddress).

    Anonymizes the email and CN parameter while preserving mailto: prefix
    and other parameters (ROLE, PARTSTAT, RSVP, etc.).

    Args:
        caladdress: The vCalAddress to anonymize
        salt: Salt for hashing

    Returns:
        New anonymized vCalAddress
    """
    # Get the email address
    email = str(caladdress)

    # Hash the email while preserving mailto: prefix
    if email.startswith("mailto:"):
        email_part = email[7:]  # Remove mailto: prefix
        hashed_email = hash_email(email_part, salt)
        new_email = f"mailto:{hashed_email}"
    else:
        new_email = hash_email(email, salt)

    # Create new vCalAddress
    new_caladdress = vCalAddress(new_email)

    # Copy all parameters, anonymizing CN
    for param_key, param_value in caladdress.params.items():
        if param_key.upper() == "CN":
            # Anonymize common name
            new_caladdress.params[param_key] = hash_caladdress_cn(param_value, salt)
        else:
            # Preserve other parameters (ROLE, PARTSTAT, RSVP, etc.)
            new_caladdress.params[param_key] = param_value

    return new_caladdress
