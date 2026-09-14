# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Tests for formats.jscal module."""

import copy

import pytest

from icalendar_anonymizer.formats.jscal import JSCAL_CONFIGURABLE_FIELDS, anonymize_jscal


def _minimal_event(**fields):
    """A minimal Event object with the given extra top-level fields merged in."""
    return {"@type": "Event", "uid": "x", **fields}


def _sample_jscal():
    return {
        "@type": "Event",
        "uid": "recur@example.com",
        "title": "Weekly Sync",
        "start": "2025-01-01T10:00:00",
        "duration": "PT1H",
        "timeZone": "Etc/UTC",
        "description": "Team standup",
        "color": "blue",
        "keywords": {"WORK": True, "PROJECT-X": True},
        "locations": {"loc-1": {"name": "Room 401"}},
        "participants": {
            "p1": {
                "roles": {"owner": True, "organizer": True},
                "sendTo": {"imip": "mailto:alice@example.com"},
                "name": "Alice Smith",
                "email": "alice@example.com",
            },
            "p2": {
                "roles": {"attendee": True},
                "sendTo": {"imip": "mailto:bob@example.com"},
                "email": "bob@example.com",
                "name": "Bob Jones",
                "participationStatus": "accepted",
            },
        },
        "recurrenceRules": [{"@type": "RecurrenceRule", "frequency": "weekly"}],
        "recurrenceOverrides": {
            "2025-01-08T10:00:00": {
                "title": "Rescheduled Sync",
                "participants": {
                    "p3": {
                        "roles": {"attendee": True},
                        "email": "carol@example.com",
                        "name": "Carol",
                    }
                },
                "start": "2025-01-08T11:00:00",
            }
        },
        "sequence": 0,
        "status": "confirmed",
        "privacy": "public",
        "freeBusyStatus": "busy",
    }


class TestAnonymizeJscal:
    """Tests for anonymize_jscal()."""

    def test_title_and_description_hashed(self):
        result = anonymize_jscal(_sample_jscal())
        assert result["title"] != "Weekly Sync"
        assert result["description"] != "Team standup"

    def test_structural_fields_preserved(self):
        data = _sample_jscal()
        result = anonymize_jscal(data)
        for field in (
            "start",
            "duration",
            "timeZone",
            "sequence",
            "status",
            "privacy",
            "freeBusyStatus",
            "@type",
            "recurrenceRules",
            "color",
        ):
            assert result[field] == data[field]

    def test_task_specific_structural_fields_preserved(self):
        # anonymize_jscal() isn't hardcoded to Event: a Task object (RFC
        # 8984 section 5.2) has its own structural scheduling fields that
        # must be preserved the same way start/status are for Event. Found
        # via manual testing: these were falling through to the unknown
        # field hash since the preserved set only covered Event's fields.
        task = {
            "@type": "Task",
            "uid": "task-1@example.com",
            "title": "Follow up with a client",
            "due": "2026-04-20T17:00:00",
            "estimatedDuration": "PT30M",
            "percentComplete": 50,
            "progress": "in-process",
            "progressUpdated": "2026-04-15T10:00:00",
        }
        result = anonymize_jscal(task)
        assert result["due"] == task["due"]
        assert result["estimatedDuration"] == task["estimatedDuration"]
        assert result["percentComplete"] == task["percentComplete"]
        assert result["progress"] == task["progress"]
        assert result["progressUpdated"] == task["progressUpdated"]
        assert result["title"] != task["title"]

    def test_group_entries_recursively_anonymized(self):
        # A Group's entries (RFC 8984 section 6.1) are full Event/Task
        # objects, not an arbitrary list. Found via manual testing: without
        # explicit handling, entries fell through to the generic unknown
        # value walker, which hashes dict keys and values indiscriminately,
        # destroying a nested event's own uid/start/@type structure instead
        # of anonymizing it through the real per-field dispatch.
        group = {
            "@type": "Group",
            "uid": "group-1@example.com",
            "title": "Q2 Reviews",
            "entries": [
                {
                    "@type": "Event",
                    "uid": "e1@example.com",
                    "title": "Meeting with Alice",
                    "start": "2026-04-10T15:00:00",
                }
            ],
        }
        result = anonymize_jscal(group)
        entry = result["entries"][0]
        assert entry["@type"] == "Event"
        assert entry["start"] == "2026-04-10T15:00:00"
        assert entry["uid"] != "e1@example.com"
        assert entry["title"] != "Meeting with Alice"

    def test_group_entries_not_a_list_raises_type_error(self):
        with pytest.raises(TypeError, match="entries must be an array"):
            anonymize_jscal({"@type": "Group", "uid": "x", "entries": "not-a-list"})

    def test_group_entry_not_a_dict_raises_type_error(self):
        with pytest.raises(TypeError, match=r"entries\[0\] must be an object"):
            anonymize_jscal({"@type": "Group", "uid": "x", "entries": ["not-a-dict"]})

    def test_locations_name_hashed_uuid_key_preserved(self):
        result = anonymize_jscal(_sample_jscal())
        assert "loc-1" in result["locations"]
        assert result["locations"]["loc-1"]["name"] != "Room 401"

    def test_participants_hashed_regardless_of_role(self):
        result = anonymize_jscal(_sample_jscal())
        organizer = result["participants"]["p1"]
        attendee = result["participants"]["p2"]
        assert organizer["name"] != "Alice Smith"
        assert organizer["email"] != "alice@example.com"
        assert attendee["name"] != "Bob Jones"
        assert attendee["email"] != "bob@example.com"

    def test_participants_roles_and_participation_status_preserved(self):
        result = anonymize_jscal(_sample_jscal())
        assert result["participants"]["p1"]["roles"] == {"owner": True, "organizer": True}
        assert result["participants"]["p2"]["roles"] == {"attendee": True}
        assert result["participants"]["p2"]["participationStatus"] == "accepted"

    def test_participants_sendto_mailto_hashed_preserving_prefix(self):
        result = anonymize_jscal(_sample_jscal())
        send_to = result["participants"]["p1"]["sendTo"]["imip"]
        assert send_to.startswith("mailto:")
        assert send_to != "mailto:alice@example.com"

    def test_participants_sendto_uppercase_mailto_preserves_structure(self):
        # sendTo comes from untrusted JSON, unlike ATTENDEE/ORGANIZER values
        # parsed by the icalendar library, which always normalize the
        # mailto: prefix to lowercase. An uppercase prefix must not collapse
        # the address into one opaque hash that loses the local@domain shape.
        data = _minimal_event(
            participants={
                "p1": {
                    "roles": {"attendee": True},
                    "sendTo": {"imip": "MAILTO:Alice@Example.com"},
                }
            },
        )
        result = anonymize_jscal(data)
        send_to = result["participants"]["p1"]["sendTo"]["imip"]
        assert send_to.startswith("MAILTO:")
        assert "@" in send_to[7:]

    @pytest.mark.parametrize(
        ("send_to_value", "mode", "check"),
        [
            ("alice@example.com", "randomize", lambda v: v != "alice@example.com"),
            (
                "tel:+15551234567",
                "randomize",
                lambda v: v.startswith("tel:") and v != "tel:+15551234567",
            ),
            ("tel:+15551234567", "replace", lambda v: v == "tel:redacted@example.local"),
            ("alice", "replace", lambda v: v == "redacted@example.local"),
        ],
    )
    def test_participants_sendto_scheme_handling(self, send_to_value, mode, check):
        # sendTo isn't always mailto: RFC 8984 allows tel:, xmpp:, and other
        # schemes, and a bare address with no scheme at all. Replace mode
        # must not force every address into a mailto: URI regardless of its
        # original protocol (it keeps the original scheme), and randomize
        # mode must not hash a non-email address as if it had local@domain
        # structure.
        data = _minimal_event(
            participants={"p1": {"roles": {"attendee": True}, "sendTo": {"other": send_to_value}}}
        )
        field_modes = {"PARTICIPANTS": mode} if mode == "replace" else None
        result = anonymize_jscal(data, field_modes=field_modes)
        send_to = result["participants"]["p1"]["sendTo"]["other"]
        assert check(send_to)

    def test_keywords_keys_hashed_values_preserved_as_true(self):
        data = _sample_jscal()
        result = anonymize_jscal(data)
        assert len(result["keywords"]) == len(data["keywords"])
        assert all(v is True for v in result["keywords"].values())
        assert set(result["keywords"].keys()) != set(data["keywords"].keys())

    def test_keywords_keep_mode_unchanged(self):
        data = _sample_jscal()
        result = anonymize_jscal(data, field_modes={"KEYWORDS": "keep"})
        assert result["keywords"] == data["keywords"]

    def test_keywords_remove_mode(self):
        result = anonymize_jscal(_sample_jscal(), field_modes={"KEYWORDS": "remove"})
        assert result["keywords"] == {}

    def test_keywords_replace_mode(self):
        result = anonymize_jscal(_sample_jscal(), field_modes={"KEYWORDS": "replace"})
        assert result["keywords"] == {"REDACTED": True}

    def test_recurrence_overrides_patch_fields_anonymized_recursively(self):
        result = anonymize_jscal(_sample_jscal())
        override = result["recurrenceOverrides"]["2025-01-08T10:00:00"]
        assert override["title"] != "Rescheduled Sync"
        assert override["participants"]["p3"]["name"] != "Carol"
        assert override["participants"]["p3"]["email"] != "carol@example.com"

    def test_recurrence_overrides_key_datetime_preserved(self):
        result = anonymize_jscal(_sample_jscal())
        assert "2025-01-08T10:00:00" in result["recurrenceOverrides"]

    def test_recurrence_overrides_start_preserved_inside_patch(self):
        result = anonymize_jscal(_sample_jscal())
        override = result["recurrenceOverrides"]["2025-01-08T10:00:00"]
        assert override["start"] == "2025-01-08T11:00:00"

    def test_no_participants_or_locations(self):
        data = _minimal_event(title="y", start="2025-01-01T10:00:00")
        result = anonymize_jscal(data)
        assert "participants" not in result
        assert "locations" not in result

    def test_minimal_dict(self):
        result = anonymize_jscal(_minimal_event(title="y"))
        assert result["title"] != "y"

    def test_unknown_string_field_hashed(self):
        result = anonymize_jscal(_minimal_event(unknownField="secret text"))
        assert result["unknownField"] != "secret text"

    def test_unknown_list_field_hashed_element_by_element(self):
        data = _minimal_event(unknownListField=["sensitive", "data"])
        result = anonymize_jscal(data)
        assert result["unknownListField"] != ["sensitive", "data"]
        assert result["unknownListField"][0] != "sensitive"
        assert result["unknownListField"][1] != "data"

    def test_unknown_nested_dict_field_hashed_recursively(self):
        data = _minimal_event(unknownDict={"nested": "secret"})
        result = anonymize_jscal(data)
        nested_value = next(iter(result["unknownDict"].values()))
        assert nested_value != "secret"

    def test_unknown_dict_field_string_keys_hashed(self):
        # An unrecognized dict-shaped field could carry personal data in a
        # key rather than a value (a vendor extension keyed by email
        # address, for example), so keys must be hashed too, not just left
        # as plaintext while only the value gets anonymized.
        data = _minimal_event(unknownDict={"alice@example.com": "some note"})
        result = anonymize_jscal(data)
        assert "alice@example.com" not in result["unknownDict"]

    def test_unknown_field_number_passes_through(self):
        result = anonymize_jscal(_minimal_event(unknownNumber=42))
        assert result["unknownNumber"] == 42

    def test_field_modes_validation_matches_config_pattern(self):
        with pytest.raises(ValueError, match="Unknown field"):
            anonymize_jscal(_sample_jscal(), field_modes={"BOGUS": "keep"})
        with pytest.raises(ValueError, match="UID cannot be removed"):
            anonymize_jscal(_sample_jscal(), field_modes={"UID": "remove"})

    def test_not_a_dict_raises_type_error(self):
        with pytest.raises(TypeError, match="must be a dict"):
            anonymize_jscal(["not", "a", "dict"])

    def test_salt_not_bytes_raises_type_error(self):
        with pytest.raises(TypeError, match="salt must be bytes"):
            anonymize_jscal(_sample_jscal(), salt="not bytes")

    def test_non_string_title_raises_type_error(self):
        # A non-string TITLE/DESCRIPTION/UID must fail cleanly with a
        # TypeError, not crash with an AttributeError from inside hash_text
        # (which would be miscategorized as an internal bug by callers that
        # only catch TypeError/ValueError, e.g. the CLI).
        with pytest.raises(TypeError, match="TITLE must be a string"):
            anonymize_jscal(_minimal_event(title=123))

    def test_non_string_uid_raises_type_error(self):
        with pytest.raises(TypeError, match="uid must be a string"):
            anonymize_jscal({"@type": "Event", "uid": 123, "title": "t"})

    def test_non_string_participant_email_raises_type_error(self):
        data = _minimal_event(participants={"p1": {"roles": {"attendee": True}, "email": 123}})
        with pytest.raises(TypeError, match="email must be a string"):
            anonymize_jscal(data)

    def test_links_and_virtuallocations_hashed_if_present(self):
        data = _minimal_event(
            links={"l1": {"href": "https://zoom.us/j/123?pwd=secret", "title": "Zoom"}},
            virtualLocations={"v1": {"uri": "tel:+15551234567", "description": "Dial in"}},
        )
        result = anonymize_jscal(data)
        assert result["links"]["l1"]["href"] != "https://zoom.us/j/123?pwd=secret"
        assert result["virtualLocations"]["v1"]["uri"] != "tel:+15551234567"

    def test_links_keep_mode(self):
        data = _minimal_event(links={"l1": {"href": "https://example.com/a"}})
        result = anonymize_jscal(data, field_modes={"LINKS": "keep"})
        assert result["links"] == data["links"]

    def test_links_remove_mode(self):
        data = _minimal_event(links={"l1": {"href": "https://example.com/a"}})
        result = anonymize_jscal(data, field_modes={"LINKS": "remove"})
        assert result["links"] == {}

    def test_color_preserved(self):
        data = _sample_jscal()
        result = anonymize_jscal(data)
        assert result["color"] == "blue"

    def test_uid_keep_mode(self):
        data = _sample_jscal()
        result = anonymize_jscal(data, field_modes={"UID": "keep"})
        assert result["uid"] == "recur@example.com"

    def test_uid_replace_mode(self):
        result = anonymize_jscal(_sample_jscal(), field_modes={"UID": "replace"})
        assert result["uid"] == "redacted-1@anonymous.local"

    def test_uid_replace_mode_unique_across_recurrence_overrides(self):
        # Each UID-bearing object under replace mode must get its own
        # placeholder rather than reusing "redacted-1" everywhere, since a
        # counter based on the (potentially unpopulated) hash map would
        # silently collapse every override's UID to the same value.
        data = _sample_jscal()
        data["recurrenceOverrides"]["2025-01-08T10:00:00"]["uid"] = "override@example.com"
        result = anonymize_jscal(data, field_modes={"UID": "replace"})
        override_uid = result["recurrenceOverrides"]["2025-01-08T10:00:00"]["uid"]
        assert result["uid"] == "redacted-1@anonymous.local"
        assert override_uid == "redacted-2@anonymous.local"

    def test_uid_replace_mode_consistent_when_override_repeats_master_uid(self):
        # RFC 8984 section 4.3.4 allows a recurrenceOverrides patch to
        # repeat the master event's UID. Replace mode must give the same
        # original UID the same placeholder both times, matching randomize
        # mode's uid_map-based consistency, not a fresh counter value.
        data = _sample_jscal()
        data["recurrenceOverrides"]["2025-01-08T10:00:00"]["uid"] = data["uid"]
        result = anonymize_jscal(data, field_modes={"UID": "replace"})
        override_uid = result["recurrenceOverrides"]["2025-01-08T10:00:00"]["uid"]
        assert result["uid"] == override_uid

    def test_title_keep_mode(self):
        data = _sample_jscal()
        result = anonymize_jscal(data, field_modes={"TITLE": "keep"})
        assert result["title"] == "Weekly Sync"

    def test_title_replace_mode(self):
        result = anonymize_jscal(_sample_jscal(), field_modes={"TITLE": "replace"})
        assert result["title"] == "[Redacted]"

    def test_participants_keep_mode(self):
        data = _sample_jscal()
        result = anonymize_jscal(data, field_modes={"PARTICIPANTS": "keep"})
        assert result["participants"] == data["participants"]

    def test_participants_replace_mode(self):
        result = anonymize_jscal(_sample_jscal(), field_modes={"PARTICIPANTS": "replace"})
        p1 = result["participants"]["p1"]
        assert p1["name"] == "[Redacted]"
        assert p1["email"] == "redacted@example.local"
        assert p1["sendTo"]["imip"] == "mailto:redacted@example.local"

    def test_participants_remove_mode(self):
        result = anonymize_jscal(_sample_jscal(), field_modes={"PARTICIPANTS": "remove"})
        assert result["participants"] == {}

    def test_participants_unknown_subfield_default_deny(self):
        # An unrecognized field on a participant object (a future RFC 8984
        # extension, or a vendor extension) must not pass through unhashed,
        # same default-deny reasoning as unknown top-level fields.
        data = _minimal_event(
            participants={"p1": {"roles": {"attendee": True}, "note": "secret note"}}
        )
        result = anonymize_jscal(data)
        assert result["participants"]["p1"]["note"] != "secret note"

    def test_participants_type_discriminator_preserved(self):
        # @type ("Participant") is structural, the same way it is for
        # locations and links entries. Found via manual testing with a
        # realistic multi-participant fixture: it was falling through to
        # the unknown-field hash, corrupting the object's own type tag.
        data = _minimal_event(
            participants={"p1": {"@type": "Participant", "roles": {"attendee": True}}}
        )
        result = anonymize_jscal(data)
        assert result["participants"]["p1"]["@type"] == "Participant"

    def test_participants_invited_by_reference_preserved(self):
        # invitedBy holds another participant's map key (RFC 8984 4.4.1),
        # not personal data itself. Hashing it independently of the actual
        # key would break the cross-reference between participants. Found
        # via manual testing with a realistic multi-participant fixture.
        data = _minimal_event(
            participants={
                "host": {"roles": {"owner": True}},
                "guest": {"roles": {"attendee": True}, "invitedBy": "host"},
            }
        )
        result = anonymize_jscal(data)
        assert result["participants"]["guest"]["invitedBy"] == "host"
        assert result["participants"]["guest"]["invitedBy"] in result["participants"]

    def test_locations_keep_mode(self):
        data = _sample_jscal()
        result = anonymize_jscal(data, field_modes={"LOCATIONS": "keep"})
        assert result["locations"] == data["locations"]

    def test_locations_replace_mode(self):
        result = anonymize_jscal(_sample_jscal(), field_modes={"LOCATIONS": "replace"})
        assert result["locations"]["loc-1"]["name"] == "[Location removed]"

    def test_locations_remove_mode(self):
        result = anonymize_jscal(_sample_jscal(), field_modes={"LOCATIONS": "remove"})
        assert result["locations"] == {}

    def test_locations_without_name_or_coordinates_unchanged(self):
        data = _minimal_event(locations={"loc-1": {}})
        result = anonymize_jscal(data)
        assert result["locations"]["loc-1"] == {}

    def test_locations_coordinates_anonymized(self):
        data = _minimal_event(
            locations={"loc-1": {"name": "Somewhere", "coordinates": "geo:1.0,2.0"}}
        )
        result = anonymize_jscal(data)
        assert result["locations"]["loc-1"]["coordinates"] != "geo:1.0,2.0"

    def test_links_replace_mode_href_and_title(self):
        data = _minimal_event(links={"l1": {"href": "https://example.com/a", "title": "My link"}})
        result = anonymize_jscal(data, field_modes={"LINKS": "replace"})
        assert result["links"]["l1"]["href"] == "[Link removed]"
        assert result["links"]["l1"]["title"] == "[Redacted]"

    def test_deterministic_with_same_salt(self):
        salt = b"a" * 32
        result1 = anonymize_jscal(_sample_jscal(), salt=salt)
        result2 = anonymize_jscal(_sample_jscal(), salt=salt)
        assert result1 == result2

    def test_default_salt_is_random(self):
        result1 = anonymize_jscal(_sample_jscal())
        result2 = anonymize_jscal(_sample_jscal())
        assert result1["title"] != result2["title"]

    def test_input_not_mutated(self):
        data = _sample_jscal()
        original = copy.deepcopy(data)
        anonymize_jscal(data)
        assert data == original

    def test_empty_keyword_key_documented_behavior(self):
        # hash_text() returns empty/whitespace-only strings unchanged, so an
        # empty-string keyword key produces an empty-string hashed key. This
        # documents that behavior rather than treating it as a bug: an empty
        # keyword string is itself a malformed-input edge case.
        result = anonymize_jscal(_minimal_event(keywords={"": True}))
        assert result["keywords"] == {"": True}

    @pytest.mark.parametrize(
        ("field", "bad_value"),
        [
            ("locations", ["not", "a", "dict"]),
            ("participants", "not-a-dict"),
            ("keywords", 5),
            ("links", "not-a-dict"),
            ("virtualLocations", []),
            ("recurrenceOverrides", "not-a-dict"),
        ],
    )
    def test_malformed_container_field_raises_type_error(self, field, bad_value):
        # Malformed JSON (a list where an object is expected, and so on)
        # must fail cleanly with a TypeError naming the field, not crash
        # with a raw AttributeError from .items() that the CLI's
        # (TypeError, ValueError) catch clause can't classify as bad input.
        data = _minimal_event(**{field: bad_value})
        with pytest.raises(TypeError, match=field):
            anonymize_jscal(data)

    @pytest.mark.parametrize(
        ("field", "malformed_entry_map", "match"),
        [
            ("locations", {"loc-1": "not-a-dict"}, "locations.loc-1"),
            ("participants", {"p1": "not-a-dict"}, "participants.p1"),
            ("links", {"l1": "not-a-dict"}, "links.l1"),
        ],
    )
    def test_malformed_entry_in_container_raises_type_error(
        self, field, malformed_entry_map, match
    ):
        data = _minimal_event(**{field: malformed_entry_map})
        with pytest.raises(TypeError, match=match):
            anonymize_jscal(data)

    def test_malformed_recurrence_override_raises_type_error(self):
        data = _minimal_event(recurrenceOverrides={"2025-01-08T10:00:00": "not-a-dict"})
        with pytest.raises(TypeError, match="recurrenceOverrides"):
            anonymize_jscal(data)

    def test_malformed_sendto_raises_type_error(self):
        data = _minimal_event(
            participants={"p1": {"roles": {"attendee": True}, "sendTo": "not-a-dict"}}
        )
        with pytest.raises(TypeError, match="sendTo"):
            anonymize_jscal(data)

    def test_keep_mode_does_not_alias_nested_containers(self):
        # A shallow copy under keep mode isn't enough: the outer dict must
        # differ from the caller's, but so must every nested dict, or
        # mutating the anonymized result silently mutates the original
        # input, breaking anonymize()'s documented never-mutates contract.
        data = _sample_jscal()
        result = anonymize_jscal(data, field_modes={"PARTICIPANTS": "keep"})
        result["participants"]["p1"]["name"] = "MUTATED"
        assert data["participants"]["p1"]["name"] == "Alice Smith"

    def test_preserved_field_passthrough_does_not_alias(self):
        # The default (no field_modes) path for a structural field like
        # recurrenceRules must not share the input's mutable containers
        # either, same reasoning as explicit keep mode above: mutating the
        # anonymized result must never mutate the caller's original data.
        data = _minimal_event(recurrenceRules=[{"frequency": "weekly"}])
        result = anonymize_jscal(data)
        result["recurrenceRules"][0]["frequency"] = "MUTATED"
        assert data["recurrenceRules"][0]["frequency"] == "weekly"

    def test_locations_description_hashed(self):
        # locations only anonymized name/coordinates originally; description
        # is an equally real RFC 8984 Location field that can carry personal
        # data and must not pass through by default-deny.
        data = _minimal_event(
            locations={"loc-1": {"name": "Room", "description": "Alice's private office"}}
        )
        result = anonymize_jscal(data)
        assert result["locations"]["loc-1"]["description"] != "Alice's private office"

    def test_locations_location_types_hashed(self):
        data = _minimal_event(locations={"loc-1": {"locationTypes": {"alice-desk": True}}})
        result = anonymize_jscal(data)
        assert "alice-desk" not in result["locations"]["loc-1"]["locationTypes"]

    def test_locations_nested_links_hashed(self):
        data = _minimal_event(
            locations={
                "loc-1": {"links": {"l1": {"href": "https://example.com/floorplan?user=alice"}}}
            }
        )
        result = anonymize_jscal(data)
        href = result["locations"]["loc-1"]["links"]["l1"]["href"]
        assert href != "https://example.com/floorplan?user=alice"

    def test_locations_type_and_timezone_preserved(self):
        data = _minimal_event(
            locations={"loc-1": {"@type": "Location", "name": "Room", "timeZone": "Etc/UTC"}}
        )
        result = anonymize_jscal(data)
        assert result["locations"]["loc-1"]["@type"] == "Location"
        assert result["locations"]["loc-1"]["timeZone"] == "Etc/UTC"

    def test_locations_unknown_field_default_deny(self):
        data = _minimal_event(locations={"loc-1": {"name": "Room", "note": "secret note"}})
        result = anonymize_jscal(data)
        assert result["locations"]["loc-1"]["note"] != "secret note"

    def test_virtual_locations_name_hashed(self):
        data = _minimal_event(
            virtualLocations={"v1": {"name": "Alice's Zoom room", "uri": "https://zoom.us/j/1"}}
        )
        result = anonymize_jscal(data)
        assert result["virtualLocations"]["v1"]["name"] != "Alice's Zoom room"

    def test_links_unknown_field_default_deny(self):
        data = _minimal_event(
            links={"l1": {"href": "https://example.com/a", "note": "secret note"}}
        )
        result = anonymize_jscal(data)
        assert result["links"]["l1"]["note"] != "secret note"

    def test_links_type_preserved(self):
        data = _minimal_event(links={"l1": {"@type": "Link", "href": "https://example.com/a"}})
        result = anonymize_jscal(data)
        assert result["links"]["l1"]["@type"] == "Link"

    def test_links_preserved_structural_fields_unchanged(self):
        data = _minimal_event(
            links={
                "l1": {
                    "href": "https://example.com/a.pdf",
                    "contentType": "application/pdf",
                    "rel": "enclosure",
                }
            }
        )
        result = anonymize_jscal(data)
        assert result["links"]["l1"]["contentType"] == "application/pdf"
        assert result["links"]["l1"]["rel"] == "enclosure"


class TestJscalConfigurableFields:
    """Tests for JSCAL_CONFIGURABLE_FIELDS."""

    def test_contains_expected_fields(self):
        assert JSCAL_CONFIGURABLE_FIELDS == {
            "TITLE",
            "DESCRIPTION",
            "LOCATIONS",
            "PARTICIPANTS",
            "KEYWORDS",
            "LINKS",
            "VIRTUALLOCATIONS",
            "UID",
        }
