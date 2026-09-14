# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Tests for formats.jcal module."""

import pytest
from icalendar import Calendar

from icalendar_anonymizer.formats.jcal import anonymize_jcal

SAMPLE_ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:recurring-1@example.com
DTSTART:20250101T100000Z
DTEND:20250101T110000Z
RRULE:FREQ=WEEKLY;COUNT=5
SUMMARY:Weekly Sync
DESCRIPTION:Team status update
ORGANIZER;CN=Alice Smith:mailto:alice@example.com
ATTENDEE;CN=Bob Jones;ROLE=REQ-PARTICIPANT;PARTSTAT=ACCEPTED:mailto:bob@example.com
LOCATION:Conference Room B
END:VEVENT
END:VCALENDAR
"""


def _sample_jcal():
    return Calendar.from_ical(SAMPLE_ICS).to_jcal()


class TestAnonymizeJcal:
    """Tests for anonymize_jcal()."""

    def test_summary_and_description_hashed(self):
        result = anonymize_jcal(_sample_jcal())
        cal = Calendar.from_jcal(result)
        event = next(iter(cal.walk("VEVENT")))
        assert str(event.get("SUMMARY")) != "Weekly Sync"
        assert str(event.get("DESCRIPTION")) != "Team status update"

    def test_attendee_organizer_params_preserved(self):
        result = anonymize_jcal(_sample_jcal())
        cal = Calendar.from_jcal(result)
        event = next(iter(cal.walk("VEVENT")))
        organizer = event.get("ORGANIZER")
        attendee = event.get("ATTENDEE")
        assert str(organizer).startswith("mailto:")
        assert str(organizer) != "mailto:alice@example.com"
        assert organizer.params["CN"] != "Alice Smith"
        assert attendee.params["ROLE"] == "REQ-PARTICIPANT"
        assert attendee.params["PARTSTAT"] == "ACCEPTED"
        assert attendee.params["CN"] != "Bob Jones"

    def test_structural_fields_preserved(self):
        result = anonymize_jcal(_sample_jcal())
        cal = Calendar.from_jcal(result)
        event = next(iter(cal.walk("VEVENT")))
        assert event.get("RRULE")["FREQ"] == "WEEKLY"
        assert str(event.get("DTSTART").dt) == "2025-01-01 10:00:00+00:00"

    def test_full_roundtrip_to_valid_ics(self):
        result = anonymize_jcal(_sample_jcal())
        cal = Calendar.from_jcal(result)
        ics_bytes = cal.to_ical()
        reparsed = Calendar.from_ical(ics_bytes)
        assert reparsed is not None

    def test_field_modes_keep(self):
        result = anonymize_jcal(_sample_jcal(), field_modes={"SUMMARY": "keep"})
        cal = Calendar.from_jcal(result)
        event = next(iter(cal.walk("VEVENT")))
        assert str(event.get("SUMMARY")) == "Weekly Sync"

    def test_field_modes_remove(self):
        result = anonymize_jcal(_sample_jcal(), field_modes={"LOCATION": "remove"})
        cal = Calendar.from_jcal(result)
        event = next(iter(cal.walk("VEVENT")))
        assert "LOCATION" not in event

    def test_field_modes_replace(self):
        result = anonymize_jcal(_sample_jcal(), field_modes={"DESCRIPTION": "replace"})
        cal = Calendar.from_jcal(result)
        event = next(iter(cal.walk("VEVENT")))
        assert str(event.get("DESCRIPTION")) == "[Content removed]"

    def test_field_modes_randomize_is_default(self):
        result = anonymize_jcal(_sample_jcal())
        cal = Calendar.from_jcal(result)
        event = next(iter(cal.walk("VEVENT")))
        assert str(event.get("SUMMARY")) != "Weekly Sync"

    def test_deterministic_with_same_salt(self):
        salt = b"a" * 32
        result1 = anonymize_jcal(_sample_jcal(), salt=salt)
        result2 = anonymize_jcal(_sample_jcal(), salt=salt)
        assert result1 == result2

    def test_default_salt_is_random(self):
        result1 = anonymize_jcal(_sample_jcal())
        result2 = anonymize_jcal(_sample_jcal())
        assert result1 != result2

    @pytest.mark.parametrize("bad_data", ["not a list", {"a": 1}])
    def test_non_list_raises_type_error(self, bad_data):
        with pytest.raises(TypeError, match="must be a list"):
            anonymize_jcal(bad_data)

    def test_empty_list_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid jCal document"):
            anonymize_jcal([])

    def test_malformed_component_shape_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid jCal document"):
            anonymize_jcal(["vcalendar", "not-a-list-of-properties", []])

    def test_non_vcalendar_root_raises_value_error(self):
        # Calendar.from_jcal() can in principle parse a bare subcomponent
        # (its own type stub returns the base Component, not Calendar
        # specifically), but anonymize_jcal's documented input is always a
        # full vcalendar document, so a bare vevent must fail cleanly.
        with pytest.raises(ValueError, match="expected a vcalendar"):
            anonymize_jcal(["vevent", [["uid", {}, "text", "x"]], []])

    def test_invalid_field_modes_raises(self):
        with pytest.raises(ValueError, match="Unknown field"):
            anonymize_jcal(_sample_jcal(), field_modes={"BOGUS": "keep"})

    def test_uid_remove_raises(self):
        with pytest.raises(ValueError, match="UID cannot be removed"):
            anonymize_jcal(_sample_jcal(), field_modes={"UID": "remove"})
