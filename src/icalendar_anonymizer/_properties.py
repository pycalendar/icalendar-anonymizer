# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Property classification for iCalendar anonymization.

Defines which properties should be preserved vs anonymized based on RFC 5545
and privacy requirements. Default-deny approach: unknown properties are
anonymized by default.
"""

# Properties that must be preserved exactly (technical/structural data)
PRESERVED_PROPERTIES = {
    # Date/time properties
    "DTSTART",
    "DTEND",
    "DUE",
    "DURATION",
    "DTSTAMP",
    "CREATED",
    "LAST-MODIFIED",
    # Recurrence properties
    "RRULE",
    "RDATE",
    "EXDATE",
    "RECURRENCE-ID",
    # Timezone properties
    "TZID",
    "TZOFFSETFROM",
    "TZOFFSETTO",
    "TZNAME",
    "TZURL",
    "X-WR-TIMEZONE",
    # Metadata properties
    "SEQUENCE",
    "STATUS",
    "TRANSP",
    "CLASS",
    "PRIORITY",
    # Structural properties
    "VERSION",
    "PRODID",
    "CALSCALE",
    "METHOD",
    # Component identification
    # Note: ATTACH, URL, and GEO intentionally NOT preserved due to privacy concerns
    # - ATTACH/URL may contain personal data in paths/queries
    # - GEO coordinates reveal home/work location
    # Alarm properties
    "ACTION",
    "TRIGGER",
    "REPEAT",
    # Freebusy properties
    "FREEBUSY",
    "FBTYPE",
    # Relationship properties
    "RELATED-TO",
    "REQUEST-STATUS",
}

# Properties that contain personal data and must be anonymized
ANONYMIZED_PROPERTIES = {
    # Text fields with personal content
    "SUMMARY",
    "DESCRIPTION",
    "LOCATION",
    "COMMENT",
    "CONTACT",
    "RESOURCES",
    "CATEGORIES",
    # Calendar addresses (emails + CN parameters)
    "ATTENDEE",
    "ORGANIZER",
    # Unique identifiers (hashed to preserve uniqueness)
    "UID",
}

# Component types that should be completely preserved (timezone data)
PRESERVED_COMPONENTS = {
    "VTIMEZONE",
    "STANDARD",
    "DAYLIGHT",
}


def should_preserve_property(property_name: str) -> bool:
    """Check if a property should be preserved.

    Args:
        property_name: The property name (uppercase)

    Returns:
        True if property should be preserved, False if it should be anonymized
    """
    upper_name = property_name.upper()

    # Explicitly preserved properties
    if upper_name in PRESERVED_PROPERTIES:
        return True

    # Explicitly anonymized properties
    if upper_name in ANONYMIZED_PROPERTIES:
        return False

    # Default-deny: unknown properties are anonymized for safety
    # This includes X- properties and future RFC additions
    return False


def should_preserve_component(component_name: str) -> bool:
    """Check if a component should be completely preserved.

    Args:
        component_name: The component name (e.g., VTIMEZONE)

    Returns:
        True if component and all its properties should be preserved
    """
    return component_name.upper() in PRESERVED_COMPONENTS
