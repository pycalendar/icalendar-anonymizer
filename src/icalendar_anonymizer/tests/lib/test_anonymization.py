# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Tests for core anonymization functionality.

Test suite for Issues #1 and #2:
- Property preservation (dates, recurrence, timezone, metadata)
- Property anonymization (text fields, attendees, organizer)
- UID handling with global salt
- Unknown property handling (default-deny)
- Edge cases and structure preservation
"""

from datetime import datetime, timedelta

import pytest
from icalendar import Calendar, Event, Todo


@pytest.fixture
def simple_event():
    """Create a simple test event."""
    cal = Calendar()
    event = Event()
    event.add("summary", "Team Meeting")
    event.add("description", "Discuss project roadmap and timeline")
    event.add("location", "Conference Room A")
    event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
    event.add("dtend", datetime(2024, 1, 15, 15, 0, 0))
    event.add("uid", "original-uid-12345@example.com")
    cal.add_component(event)
    return cal


@pytest.fixture
def event_with_attendees():
    """Create event with attendees and organizer."""
    cal = Calendar()
    event = Event()
    event.add("summary", "Project Review")
    event.add("dtstart", datetime(2024, 1, 20, 10, 0, 0))

    # Add organizer with CN parameter
    from icalendar import vCalAddress

    organizer = vCalAddress("mailto:john.doe@example.com")
    organizer.params["cn"] = "John Doe"
    event.add("organizer", organizer)

    # Add attendees with CN parameters
    attendee1 = vCalAddress("mailto:jane.smith@example.com")
    attendee1.params["cn"] = "Jane Smith"
    attendee1.params["role"] = "REQ-PARTICIPANT"
    event.add("attendee", attendee1)

    attendee2 = vCalAddress("mailto:bob.jones@company.org")
    attendee2.params["cn"] = "Bob Jones"
    attendee2.params["partstat"] = "ACCEPTED"
    event.add("attendee", attendee2)

    cal.add_component(event)
    return cal


@pytest.fixture
def event_with_recurrence():
    """Create recurring event with RRULE."""
    cal = Calendar()
    event = Event()
    event.add("summary", "Weekly Standup")
    event.add("dtstart", datetime(2024, 1, 1, 9, 0, 0))
    event.add("dtend", datetime(2024, 1, 1, 9, 30, 0))
    event.add("rrule", {"freq": "WEEKLY", "byday": "MO", "count": 10})
    event.add("exdate", datetime(2024, 1, 8, 9, 0, 0))
    event.add("rdate", datetime(2024, 1, 9, 9, 0, 0))
    cal.add_component(event)
    return cal


# Property Preservation Tests


@pytest.mark.parametrize(
    ("property_name", "expected_ical"),
    [
        ("dtstart", b"20240115T140000"),
        ("dtend", b"20240115T150000"),
    ],
)
def test_preserves_datetime_properties(simple_event, property_name, expected_ical):
    """Date/time properties should be preserved exactly."""
    from icalendar_anonymizer import anonymize

    anon_cal = anonymize(simple_event)
    event = next(iter(anon_cal.walk("VEVENT")))

    assert event[property_name].to_ical() == expected_ical


def test_preserves_rrule(event_with_recurrence):
    """RRULE should be preserved exactly."""
    from icalendar_anonymizer import anonymize

    anon_cal = anonymize(event_with_recurrence)
    event = next(iter(anon_cal.walk("VEVENT")))

    rrule = event["rrule"]
    assert rrule["FREQ"] == "WEEKLY"
    assert rrule["BYDAY"] == "MO"
    assert rrule["COUNT"] == 10


@pytest.mark.parametrize(
    ("property_name", "expected_ical"),
    [
        ("exdate", b"20240108T090000"),
        ("rdate", b"20240109T090000"),
    ],
)
def test_preserves_recurrence_dates(event_with_recurrence, property_name, expected_ical):
    """Recurrence date properties should be preserved exactly."""
    from icalendar_anonymizer import anonymize

    anon_cal = anonymize(event_with_recurrence)
    event = next(iter(anon_cal.walk("VEVENT")))

    assert event[property_name].to_ical() == expected_ical


@pytest.mark.parametrize(
    ("property_name", "property_value", "expected_value"),
    [
        ("sequence", 3, 3),
        ("status", "CONFIRMED", "CONFIRMED"),
        ("transp", "OPAQUE", "OPAQUE"),
        ("class", "PRIVATE", "PRIVATE"),
        ("priority", 1, 1),
    ],
)
def test_preserves_metadata_properties(property_name, property_value, expected_value):
    """Metadata properties should be preserved exactly."""
    from icalendar_anonymizer import anonymize

    cal = Calendar()
    event = Event()
    event.add("summary", "Test Event")
    event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
    event.add(property_name, property_value)
    cal.add_component(event)

    anon_cal = anonymize(cal)
    anon_event = next(iter(anon_cal.walk("VEVENT")))

    assert anon_event[property_name] == expected_value


def test_anonymizes_categories():
    """CATEGORIES should be anonymized (default-deny for personal data)."""
    from icalendar_anonymizer import anonymize

    cal = Calendar()
    event = Event()
    event.add("summary", "Work Meeting")
    event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
    event.add("categories", ["WORK", "MEETING"])
    cal.add_component(event)

    anon_cal = anonymize(cal)
    anon_event = next(iter(anon_cal.walk("VEVENT")))

    # CATEGORIES should be anonymized
    categories = anon_event.get("categories")
    assert categories is not None, "CATEGORIES should be preserved (but anonymized)"
    assert categories.to_ical() != b"WORK,MEETING"


def test_preserves_duration():
    """DURATION should be preserved."""
    from datetime import timedelta

    from icalendar_anonymizer import anonymize

    cal = Calendar()
    event = Event()
    event.add("summary", "Timed Event")
    event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
    event.add("duration", timedelta(hours=2))
    cal.add_component(event)

    anon_cal = anonymize(cal)
    anon_event = next(iter(anon_cal.walk("VEVENT")))

    assert anon_event["duration"].to_ical() == b"PT2H"


def test_preserves_dtstamp():
    """DTSTAMP should be preserved."""
    from icalendar_anonymizer import anonymize

    cal = Calendar()
    event = Event()
    event.add("summary", "Stamped Event")
    event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
    event.add("dtstamp", datetime(2024, 1, 10, 12, 0, 0))
    cal.add_component(event)

    anon_cal = anonymize(cal)
    anon_event = next(iter(anon_cal.walk("VEVENT")))

    assert anon_event["dtstamp"].to_ical() == b"20240110T120000Z"


def test_preserves_due_in_todo():
    """DUE should be preserved in VTODO."""
    from icalendar_anonymizer import anonymize

    cal = Calendar()
    todo = Todo()
    todo.add("summary", "Complete report")
    todo.add("due", datetime(2024, 1, 20, 17, 0, 0))
    cal.add_component(todo)

    anon_cal = anonymize(cal)
    anon_todo = next(iter(anon_cal.walk("VTODO")))

    assert anon_todo["due"].to_ical() == b"20240120T170000"


# Property Anonymization Tests


@pytest.mark.parametrize(
    ("property_name", "original_value"),
    [
        ("summary", "Team Meeting"),
        ("description", "Discuss project roadmap and timeline"),
        ("location", "Conference Room A"),
    ],
)
def test_anonymizes_text_properties(simple_event, property_name, original_value):
    """Text properties should be anonymized."""
    from icalendar_anonymizer import anonymize

    anon_cal = anonymize(simple_event)
    event = next(iter(anon_cal.walk("VEVENT")))

    assert event[property_name] != original_value
    assert len(str(event[property_name])) > 0


def test_anonymizes_comment():
    """COMMENT should be anonymized."""
    from icalendar_anonymizer import anonymize

    cal = Calendar()
    event = Event()
    event.add("summary", "Event")
    event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
    event.add("comment", "This is a private note")
    cal.add_component(event)

    anon_cal = anonymize(cal)
    anon_event = next(iter(anon_cal.walk("VEVENT")))

    assert anon_event["comment"] != "This is a private note"


def test_anonymizes_contact():
    """CONTACT should be anonymized."""
    from icalendar_anonymizer import anonymize

    cal = Calendar()
    event = Event()
    event.add("summary", "Event")
    event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
    event.add("contact", "John Doe, 555-1234")
    cal.add_component(event)

    anon_cal = anonymize(cal)
    anon_event = next(iter(anon_cal.walk("VEVENT")))

    assert anon_event["contact"] != "John Doe, 555-1234"


@pytest.mark.parametrize("property_name", ["summary", "description"])
def test_preserves_word_count(simple_event, property_name):
    """Anonymized text properties should preserve word count."""
    from icalendar_anonymizer import anonymize

    original_property = next(iter(simple_event.walk("VEVENT")))[property_name]
    original_words = len(str(original_property).split())

    anon_cal = anonymize(simple_event)
    event = next(iter(anon_cal.walk("VEVENT")))
    anon_words = len(str(event[property_name]).split())

    assert anon_words == original_words


def test_anonymizes_organizer_email(event_with_attendees):
    """ORGANIZER email should be anonymized."""
    from icalendar_anonymizer import anonymize

    anon_cal = anonymize(event_with_attendees)
    event = next(iter(anon_cal.walk("VEVENT")))

    organizer = str(event["organizer"])
    assert "john.doe@example.com" not in organizer
    assert organizer.startswith("mailto:")


def test_anonymizes_organizer_cn(event_with_attendees):
    """ORGANIZER CN parameter should be anonymized."""
    from icalendar_anonymizer import anonymize

    anon_cal = anonymize(event_with_attendees)
    event = next(iter(anon_cal.walk("VEVENT")))

    cn = event["organizer"].params.get("cn", "")
    assert cn != "John Doe"


def test_preserves_mailto_prefix_in_organizer(event_with_attendees):
    """ORGANIZER should preserve mailto: prefix."""
    from icalendar_anonymizer import anonymize

    anon_cal = anonymize(event_with_attendees)
    event = next(iter(anon_cal.walk("VEVENT")))

    organizer = str(event["organizer"])
    assert organizer.startswith("mailto:")


def test_anonymizes_attendee_emails(event_with_attendees):
    """ATTENDEE emails should be anonymized."""
    from icalendar_anonymizer import anonymize

    anon_cal = anonymize(event_with_attendees)
    event = next(iter(anon_cal.walk("VEVENT")))

    attendees = event.get("attendee", [])
    if not isinstance(attendees, list):
        attendees = [attendees]

    for attendee in attendees:
        attendee_str = str(attendee)
        assert "jane.smith@example.com" not in attendee_str
        assert "bob.jones@company.org" not in attendee_str
        assert attendee_str.startswith("mailto:")


def test_preserves_attendee_parameters(event_with_attendees):
    """ATTENDEE non-CN parameters should be preserved."""
    from icalendar_anonymizer import anonymize

    anon_cal = anonymize(event_with_attendees)
    event = next(iter(anon_cal.walk("VEVENT")))

    attendees = event.get("attendee", [])
    if not isinstance(attendees, list):
        attendees = [attendees]

    # Check that ROLE and PARTSTAT are preserved
    roles = [a.params.get("role") for a in attendees if "role" in a.params]
    partstats = [a.params.get("partstat") for a in attendees if "partstat" in a.params]

    assert "REQ-PARTICIPANT" in roles
    assert "ACCEPTED" in partstats


# UID Handling Tests


def test_uid_is_hashed(simple_event):
    """UID should be hashed, not preserved."""
    from icalendar_anonymizer import anonymize

    anon_cal = anonymize(simple_event)
    event = next(iter(anon_cal.walk("VEVENT")))

    assert event["uid"] != "original-uid-12345@example.com"


def test_uid_uniqueness_preserved():
    """Different UIDs should remain different after anonymization."""
    from icalendar_anonymizer import anonymize

    cal = Calendar()

    event1 = Event()
    event1.add("summary", "Event 1")
    event1.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
    event1.add("uid", "uid-1@example.com")
    cal.add_component(event1)

    event2 = Event()
    event2.add("summary", "Event 2")
    event2.add("dtstart", datetime(2024, 1, 15, 15, 0, 0))
    event2.add("uid", "uid-2@example.com")
    cal.add_component(event2)

    anon_cal = anonymize(cal)
    events = list(anon_cal.walk("VEVENT"))

    assert events[0]["uid"] != events[1]["uid"]


def test_same_uid_produces_same_hash():
    """Same UID within calendar should produce same hash."""
    from icalendar_anonymizer import anonymize

    cal = Calendar()

    # Events with same UID (e.g., instances of recurring event)
    event1 = Event()
    event1.add("summary", "Instance 1")
    event1.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
    event1.add("uid", "recurring-event@example.com")
    event1.add("recurrence-id", datetime(2024, 1, 15, 14, 0, 0))
    cal.add_component(event1)

    event2 = Event()
    event2.add("summary", "Instance 2")
    event2.add("dtstart", datetime(2024, 1, 22, 14, 0, 0))
    event2.add("uid", "recurring-event@example.com")
    event2.add("recurrence-id", datetime(2024, 1, 22, 14, 0, 0))
    cal.add_component(event2)

    anon_cal = anonymize(cal)
    events = list(anon_cal.walk("VEVENT"))

    assert events[0]["uid"] == events[1]["uid"]


def test_different_salt_produces_different_hash(simple_event):
    """Different anonymization runs should produce different hashes."""
    from icalendar_anonymizer import anonymize

    anon_cal1 = anonymize(simple_event)
    anon_cal2 = anonymize(simple_event)

    event1 = next(iter(anon_cal1.walk("VEVENT")))
    event2 = next(iter(anon_cal2.walk("VEVENT")))

    # Different runs use different salts, so hashes differ
    assert event1["uid"] != event2["uid"]


# Unknown Property Tests


def test_anonymizes_unknown_x_property():
    """Unknown X- properties should be anonymized (default-deny)."""
    from icalendar_anonymizer import anonymize

    cal = Calendar()
    event = Event()
    event.add("summary", "Event")
    event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
    event.add("x-custom-field", "sensitive data")
    cal.add_component(event)

    anon_cal = anonymize(cal)
    anon_event = next(iter(anon_cal.walk("VEVENT")))

    # X-CUSTOM-FIELD should be anonymized
    custom_field = anon_event.get("x-custom-field")
    assert custom_field is not None, "X-CUSTOM-FIELD should be preserved (but anonymized)"
    assert str(custom_field) != "sensitive data"


def test_preserves_x_wr_timezone():
    """X-WR-TIMEZONE is timezone metadata and must be preserved."""
    from icalendar_anonymizer import anonymize

    cal = Calendar()
    cal.add("x-wr-timezone", "Europe/Berlin")

    assert str(anonymize(cal)["x-wr-timezone"]) == "Europe/Berlin"


def test_anonymizes_unknown_standard_property():
    """Unknown standard properties should be anonymized (safe default)."""
    from icalendar_anonymizer import anonymize

    cal = Calendar()
    event = Event()
    event.add("summary", "Event")
    event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
    # Add a hypothetical future standard property
    event.add("future-property", "unknown value")
    cal.add_component(event)

    anon_cal = anonymize(cal)
    anon_event = next(iter(anon_cal.walk("VEVENT")))

    future_prop = anon_event.get("future-property")
    assert future_prop is not None, "FUTURE-PROPERTY should be preserved (but anonymized)"
    assert str(future_prop) != "unknown value"


# Edge Cases


def test_empty_calendar():
    """Empty calendar should not crash."""
    from icalendar_anonymizer import anonymize

    cal = Calendar()
    anon_cal = anonymize(cal)

    assert anon_cal is not None
    assert len(list(anon_cal.walk())) > 0  # At least VCALENDAR component


def test_calendar_with_only_vtimezone():
    """Calendar with only VTIMEZONE should work."""
    from icalendar.cal import Timezone, TimezoneStandard

    from icalendar_anonymizer import anonymize

    cal = Calendar()
    tz = Timezone()
    tz.add("tzid", "America/New_York")

    standard = TimezoneStandard()
    standard.add("dtstart", datetime(1970, 11, 1, 2, 0, 0))
    standard.add("tzoffsetfrom", timedelta(hours=-4))
    standard.add("tzoffsetto", timedelta(hours=-5))
    tz.add_component(standard)

    cal.add_component(tz)

    anon_cal = anonymize(cal)
    anon_tz = next(iter(anon_cal.walk("VTIMEZONE")))

    # VTIMEZONE should be completely preserved
    assert anon_tz["tzid"] == "America/New_York"


def test_handles_multibyte_utf8():
    """Should handle multi-byte UTF-8 characters correctly."""
    from icalendar_anonymizer import anonymize

    cal = Calendar()
    event = Event()
    event.add("summary", "会議 ミーティング 🎉")
    event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
    cal.add_component(event)

    anon_cal = anonymize(cal)
    anon_event = next(iter(anon_cal.walk("VEVENT")))

    # Should not crash and should produce valid output
    assert anon_event["summary"] is not None
    assert len(str(anon_event["summary"])) > 0


# Preserve Parameter Tests


def test_preserve_additional_property():
    """preserve parameter should preserve specified properties."""
    from icalendar_anonymizer import anonymize

    cal = Calendar()
    event = Event()
    event.add("summary", "Team Meeting")
    event.add("location", "Conference Room A")
    event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
    cal.add_component(event)

    anon_cal = anonymize(cal, preserve={"LOCATION"})
    anon_event = next(iter(anon_cal.walk("VEVENT")))

    assert anon_event["summary"] != "Team Meeting"
    assert anon_event["location"] == "Conference Room A"


def test_preserve_case_insensitive():
    """preserve parameter should be case-insensitive."""
    from icalendar_anonymizer import anonymize

    cal = Calendar()
    event = Event()
    event.add("summary", "Meeting")
    event.add("location", "Room A")
    event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
    cal.add_component(event)

    anon_cal = anonymize(cal, preserve={"location", "Location", "LOCATION"})
    anon_event = next(iter(anon_cal.walk("VEVENT")))

    assert anon_event["location"] == "Room A"


def test_preserve_multiple_properties():
    """preserve parameter can preserve multiple properties."""
    from icalendar_anonymizer import anonymize

    cal = Calendar()
    event = Event()
    event.add("summary", "Meeting")
    event.add("location", "Room A")
    event.add("comment", "Important note")
    event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
    cal.add_component(event)

    anon_cal = anonymize(cal, preserve={"LOCATION", "COMMENT"})
    anon_event = next(iter(anon_cal.walk("VEVENT")))

    assert anon_event["summary"] != "Meeting"
    assert anon_event["location"] == "Room A"
    assert anon_event["comment"] == "Important note"


def test_preserve_categories():
    """preserve can be used to preserve CATEGORIES."""
    from icalendar_anonymizer import anonymize

    cal = Calendar()
    event = Event()
    event.add("summary", "Work Meeting")
    event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
    event.add("categories", ["WORK", "MEETING"])
    cal.add_component(event)

    anon_cal = anonymize(cal, preserve={"CATEGORIES"})
    anon_event = next(iter(anon_cal.walk("VEVENT")))

    categories = anon_event.get("categories")
    assert categories.to_ical() == b"WORK,MEETING"


def test_preserve_empty_set():
    """preserve with empty set should work like no preserve."""
    from icalendar_anonymizer import anonymize

    cal = Calendar()
    event = Event()
    event.add("summary", "Meeting")
    event.add("location", "Room A")
    event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
    cal.add_component(event)

    anon_cal = anonymize(cal, preserve=set())
    anon_event = next(iter(anon_cal.walk("VEVENT")))

    assert anon_event["summary"] != "Meeting"
    assert anon_event["location"] != "Room A"


def test_preserve_none():
    """preserve=None should work like default behavior."""
    from icalendar_anonymizer import anonymize

    cal = Calendar()
    event = Event()
    event.add("summary", "Meeting")
    event.add("location", "Room A")
    event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
    cal.add_component(event)

    anon_cal = anonymize(cal, preserve=None)
    anon_event = next(iter(anon_cal.walk("VEVENT")))

    assert anon_event["summary"] != "Meeting"
    assert anon_event["location"] != "Room A"


def test_preserve_in_subcomponents():
    """preserve should apply to subcomponents like VALARM."""
    from icalendar import Alarm

    from icalendar_anonymizer import anonymize

    cal = Calendar()
    event = Event()
    event.add("summary", "Event with Alarm")
    event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))

    alarm = Alarm()
    alarm.add("action", "DISPLAY")
    alarm.add("description", "Alarm description")
    alarm.add("trigger", timedelta(minutes=-15))
    event.add_component(alarm)

    cal.add_component(event)

    anon_cal = anonymize(cal, preserve={"DESCRIPTION"})
    anon_event = next(iter(anon_cal.walk("VEVENT")))
    anon_alarm = next(iter(anon_event.walk("VALARM")))

    assert anon_alarm["description"] == "Alarm description"


def test_preserve_type_validation_rejects_string():
    """preserve parameter must be a set, not a string."""
    import pytest

    from icalendar_anonymizer import anonymize

    cal = Calendar()
    event = Event()
    event.add("summary", "Test")
    event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
    cal.add_component(event)

    with pytest.raises(TypeError, match="preserve must be a set or None, got str"):
        anonymize(cal, preserve="LOCATION")


def test_preserve_type_validation_rejects_list():
    """preserve parameter must be a set, not a list."""
    import pytest

    from icalendar_anonymizer import anonymize

    cal = Calendar()
    event = Event()
    event.add("summary", "Test")
    event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
    cal.add_component(event)

    with pytest.raises(TypeError, match="preserve must be a set or None, got list"):
        anonymize(cal, preserve=["LOCATION"])


def test_preserve_type_validation_rejects_tuple():
    """preserve parameter must be a set, not a tuple."""
    import pytest

    from icalendar_anonymizer import anonymize

    cal = Calendar()
    event = Event()
    event.add("summary", "Test")
    event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
    cal.add_component(event)

    with pytest.raises(TypeError, match="preserve must be a set or None, got tuple"):
        anonymize(cal, preserve=("LOCATION",))


class TestFieldModes:
    """Tests for field_modes parameter."""

    def test_keep_mode_preserves_value(self):
        """KEEP mode preserves original value."""
        from icalendar_anonymizer import anonymize

        cal = Calendar()
        event = Event()
        event.add("summary", "Original Summary")
        event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
        cal.add_component(event)

        result = anonymize(cal, field_modes={"SUMMARY": "keep"})
        anon_event = next(iter(result.walk("VEVENT")))
        assert anon_event["summary"] == "Original Summary"

    def test_remove_mode_strips_property(self):
        """REMOVE mode strips property entirely."""
        from icalendar_anonymizer import anonymize

        cal = Calendar()
        event = Event()
        event.add("summary", "To Remove")
        event.add("location", "Also Remove")
        event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
        cal.add_component(event)

        result = anonymize(cal, field_modes={"SUMMARY": "remove", "LOCATION": "remove"})
        anon_event = next(iter(result.walk("VEVENT")))
        assert "summary" not in anon_event
        assert "location" not in anon_event

    def test_replace_mode_uses_placeholder(self):
        """REPLACE mode uses placeholder text."""
        from icalendar_anonymizer import anonymize

        cal = Calendar()
        event = Event()
        event.add("summary", "Original")
        event.add("description", "Original Desc")
        event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
        cal.add_component(event)

        result = anonymize(cal, field_modes={"SUMMARY": "replace", "DESCRIPTION": "replace"})
        anon_event = next(iter(result.walk("VEVENT")))
        assert anon_event["summary"] == "[Redacted]"
        assert anon_event["description"] == "[Content removed]"

    def test_randomize_is_default(self):
        """RANDOMIZE is the default mode when not specified."""
        from icalendar_anonymizer import anonymize

        cal = Calendar()
        event = Event()
        event.add("summary", "Test")
        event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
        cal.add_component(event)

        result1 = anonymize(cal)
        result2 = anonymize(cal, field_modes={})
        event1 = next(iter(result1.walk("VEVENT")))
        event2 = next(iter(result2.walk("VEVENT")))
        assert event1["summary"] != "Test"
        assert event2["summary"] != "Test"

    def test_mixed_modes(self):
        """Different fields can use different modes simultaneously."""
        from icalendar_anonymizer import anonymize

        cal = Calendar()
        event = Event()
        event.add("summary", "Keep Me")
        event.add("location", "Remove Me")
        event.add("description", "Replace Me")
        event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
        cal.add_component(event)

        result = anonymize(
            cal,
            field_modes={
                "SUMMARY": "keep",
                "LOCATION": "remove",
                "DESCRIPTION": "replace",
            },
        )
        anon_event = next(iter(result.walk("VEVENT")))
        assert anon_event["summary"] == "Keep Me"
        assert "location" not in anon_event
        assert anon_event["description"] == "[Content removed]"

    def test_uid_replace_unique_per_event(self):
        """UID REPLACE mode generates unique IDs for each event."""
        from icalendar_anonymizer import anonymize

        cal = Calendar()
        for i in range(3):
            event = Event()
            event.add("summary", f"Event {i}")
            event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
            event.add("uid", f"uid-{i}@example.com")
            cal.add_component(event)

        result = anonymize(cal, field_modes={"UID": "replace"})
        uids = [str(e["uid"]) for e in result.walk("VEVENT")]
        assert len(set(uids)) == 3  # All unique
        assert all("redacted-" in uid for uid in uids)
        assert "redacted-1@anonymous.local" in uids
        assert "redacted-2@anonymous.local" in uids
        assert "redacted-3@anonymous.local" in uids

    def test_attendee_replace_preserves_params(self):
        """ATTENDEE REPLACE mode preserves non-personal params."""
        from icalendar.prop import vCalAddress

        from icalendar_anonymizer import anonymize

        cal = Calendar()
        event = Event()
        event.add("summary", "Meeting")
        event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))

        attendee = vCalAddress("mailto:john@example.com")
        attendee.params["cn"] = "John Doe"
        attendee.params["role"] = "REQ-PARTICIPANT"
        attendee.params["partstat"] = "ACCEPTED"
        event.add("attendee", attendee)
        cal.add_component(event)

        result = anonymize(cal, field_modes={"ATTENDEE": "replace"})
        anon_event = next(iter(result.walk("VEVENT")))
        anon_attendee = anon_event["attendee"]

        assert str(anon_attendee) == "mailto:redacted@example.local"
        assert anon_attendee.params["cn"] == "Redacted"
        assert anon_attendee.params["role"] == "REQ-PARTICIPANT"
        assert anon_attendee.params["partstat"] == "ACCEPTED"

    def test_preserve_and_field_modes_mutual_exclusion(self):
        """Cannot specify both preserve and field_modes."""
        import pytest

        from icalendar_anonymizer import anonymize

        cal = Calendar()
        event = Event()
        event.add("summary", "Test")
        event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
        cal.add_component(event)

        with pytest.raises(ValueError, match="Cannot specify both"):
            anonymize(cal, preserve={"LOCATION"}, field_modes={"SUMMARY": "keep"})

    def test_preserve_backward_compat(self):
        """preserve parameter still works for backward compatibility."""
        from icalendar_anonymizer import anonymize

        cal = Calendar()
        event = Event()
        event.add("summary", "Anonymize")
        event.add("location", "Keep Me")
        event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
        cal.add_component(event)

        result = anonymize(cal, preserve={"LOCATION"})
        anon_event = next(iter(result.walk("VEVENT")))
        assert anon_event["location"] == "Keep Me"
        assert anon_event["summary"] != "Anonymize"

    def test_field_modes_in_subcomponents(self):
        """field_modes applies to subcomponents like VALARM."""
        from icalendar import Alarm

        from icalendar_anonymizer import anonymize

        cal = Calendar()
        event = Event()
        event.add("summary", "Event")
        event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))

        alarm = Alarm()
        alarm.add("action", "DISPLAY")
        alarm.add("description", "Alarm description to keep")
        alarm.add("trigger", timedelta(minutes=-15))
        event.add_component(alarm)
        cal.add_component(event)

        result = anonymize(cal, field_modes={"DESCRIPTION": "keep"})
        anon_event = next(iter(result.walk("VEVENT")))
        anon_alarm = next(iter(anon_event.walk("VALARM")))
        assert anon_alarm["description"] == "Alarm description to keep"

    def test_uid_remove_not_allowed(self):
        """UID cannot be removed (would break recurring events)."""
        import pytest

        from icalendar_anonymizer import anonymize

        cal = Calendar()
        event = Event()
        event.add("summary", "Test")
        event.add("uid", "test@example.com")
        event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
        cal.add_component(event)

        with pytest.raises(ValueError, match="UID cannot be removed"):
            anonymize(cal, field_modes={"UID": "remove"})

    def test_all_configurable_fields(self):
        """All 10 configurable fields can be set."""
        from icalendar.prop import vCalAddress

        from icalendar_anonymizer import anonymize

        cal = Calendar()
        event = Event()
        event.add("summary", "Test Summary")
        event.add("description", "Test Description")
        event.add("location", "Test Location")
        event.add("comment", "Test Comment")
        event.add("contact", "Test Contact")
        event.add("resources", "Test Resources")
        event.add("categories", ["Test Category"])
        attendee = vCalAddress("mailto:test@example.com")
        event.add("attendee", attendee)
        organizer = vCalAddress("mailto:org@example.com")
        event.add("organizer", organizer)
        event.add("uid", "test@example.com")
        event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
        cal.add_component(event)

        result = anonymize(
            cal,
            field_modes={
                "SUMMARY": "keep",
                "DESCRIPTION": "keep",
                "LOCATION": "keep",
                "COMMENT": "keep",
                "CONTACT": "keep",
                "RESOURCES": "keep",
                "CATEGORIES": "keep",
                "ATTENDEE": "keep",
                "ORGANIZER": "keep",
                "UID": "keep",
            },
        )
        anon_event = next(iter(result.walk("VEVENT")))
        assert anon_event["summary"] == "Test Summary"
        assert anon_event["description"] == "Test Description"
        assert anon_event["location"] == "Test Location"
        assert anon_event["comment"] == "Test Comment"
        assert anon_event["contact"] == "Test Contact"
        assert anon_event["resources"] == "Test Resources"
        assert anon_event["categories"].to_ical() == b"Test Category"
        assert str(anon_event["attendee"]) == "mailto:test@example.com"
        assert str(anon_event["organizer"]) == "mailto:org@example.com"
        assert anon_event["uid"] == "test@example.com"
