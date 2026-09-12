# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Tests for _encoding module."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from icalendar_anonymizer._encoding import (
    charset_from_content_type,
    decode_ics_bytes,
    decode_ics_bytes_with_content_type,
    decode_ics_bytes_with_declared_charset,
)

# Realistic multi-property ICS body with accented French text.
_FRENCH_ICS = (
    "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Test//Test//EN\r\n"
    "BEGIN:VEVENT\r\nUID:test-event@example.com\r\n"
    "DTSTART:20240115T140000Z\r\nDTEND:20240115T150000Z\r\n"
    "SUMMARY:Réunion budgétaire\r\n"
    "DESCRIPTION:Discussion confidentielle à propos du bureau privé\r\n"
    "LOCATION:Salle de conférence, 5ème étage\r\n"
    "END:VEVENT\r\nEND:VCALENDAR\r\n"
)


class TestDecodeIcsBytes:
    """Tests for decode_ics_bytes()."""

    def test_valid_utf8_uses_fast_path(self):
        text, encoding_used = decode_ics_bytes(_FRENCH_ICS.encode("utf-8"))
        assert text == _FRENCH_ICS
        assert encoding_used == "utf-8"

    def test_latin1_french_text_decodes_correctly(self):
        text, encoding_used = decode_ics_bytes(_FRENCH_ICS.encode("latin-1"))
        assert text == _FRENCH_ICS
        assert encoding_used == "cp1252"

    def test_cp1252_smart_quotes_decode_correctly(self):
        ics = (
            "BEGIN:VCALENDAR\r\nVERSION:2.0\r\n"
            "SUMMARY:Team’s Q1 offsite – Munich office\r\n"
            "END:VCALENDAR\r\n"
        )
        text, encoding_used = decode_ics_bytes(ics.encode("cp1252"))
        assert text == ics
        assert encoding_used == "cp1252"

    @pytest.mark.parametrize(
        ("summary", "expected_summary"),
        [
            ("Büro Besprechung über Verkäufe", "Büro Besprechung über Verkäufe"),
            ("Reunión con el equipo de diseño", "Reunión con el equipo de diseño"),
            ("Reunião de planejamento orçamentário", "Reunião de planejamento orçamentário"),
            ("Møde med salgsteamet i København", "Møde med salgsteamet i København"),
        ],
    )
    def test_western_european_languages_decode_correctly(self, summary, expected_summary):
        ics = f"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nSUMMARY:{summary}\r\nEND:VCALENDAR\r\n"
        text, _encoding_used = decode_ics_bytes(ics.encode("cp1252"))
        assert expected_summary in text

    def test_encoding_outside_cp1252_range_decodes_without_raising(self):
        # Polish "ł" has no cp1252 representation. Detection is scoped to
        # cp1252/Latin-1 (see _encoding.py's module docstring) and cp1252
        # has a defined mapping for nearly every byte value, so this does
        # NOT reliably produce a visible replacement character - it can
        # silently decode to a different, plausible-looking character
        # instead (verified: the "ł" byte here decodes to "³", not a
        # replacement character). The guarantee this module provides is
        # narrower than "visible failure": only that decoding never
        # raises, not that a wrong guess is always detectable.
        ics = "BEGIN:VCALENDAR\r\nSUMMARY:Spotkanie zespołu\r\nEND:VCALENDAR\r\n"
        text, _encoding_used = decode_ics_bytes(ics.encode("cp1250"))
        assert "Spotkanie zespo" in text
        assert "łu" not in text  # the Polish character itself never survives

    def test_explicit_encoding_override_bypasses_detection(self):
        data = _FRENCH_ICS.encode("cp1252")
        text, encoding_used = decode_ics_bytes(data, encoding="cp1252")
        assert text == _FRENCH_ICS
        assert encoding_used == "cp1252"

    def test_explicit_wrong_encoding_raises_unicode_decode_error(self):
        data = _FRENCH_ICS.encode("cp1252")
        with pytest.raises(UnicodeDecodeError):
            decode_ics_bytes(data, encoding="ascii")

    def test_explicit_unknown_codec_raises_lookup_error(self):
        with pytest.raises(LookupError):
            decode_ics_bytes(b"anything", encoding="not-a-real-codec")

    def test_bytearray_input_is_accepted(self):
        data = bytearray(_FRENCH_ICS.encode("latin-1"))
        text, _encoding_used = decode_ics_bytes(data)
        assert text == _FRENCH_ICS

    @given(st.binary(max_size=2000))
    def test_never_raises_without_explicit_encoding(self, data):
        text, encoding_used = decode_ics_bytes(data)
        assert isinstance(text, str)
        assert isinstance(encoding_used, str)


class TestCharsetFromContentType:
    """Tests for charset_from_content_type()."""

    def test_extracts_declared_charset(self):
        assert charset_from_content_type("text/calendar; charset=utf-16") == "utf-16"

    def test_case_insensitive_parameter_name(self):
        assert charset_from_content_type("text/calendar; CHARSET=utf-16") == "utf-16"

    def test_no_charset_parameter_returns_none(self):
        assert charset_from_content_type("text/calendar") is None

    def test_none_input_returns_none(self):
        assert charset_from_content_type(None) is None


class TestDecodeIcsBytesWithDeclaredCharset:
    """Tests for decode_ics_bytes_with_declared_charset()."""

    def test_honors_correct_declared_charset(self):
        data = _FRENCH_ICS.encode("utf-16")
        text, encoding_used = decode_ics_bytes_with_declared_charset(data, "utf-16")
        assert text == _FRENCH_ICS
        assert encoding_used == "utf-16"

    def test_falls_back_to_detection_when_no_charset_declared(self):
        data = _FRENCH_ICS.encode("latin-1")
        text, _encoding_used = decode_ics_bytes_with_declared_charset(data, None)
        assert text == _FRENCH_ICS

    def test_falls_back_to_detection_when_declared_charset_is_wrong(self):
        # Declares utf-8 but the bytes are actually cp1252 - a real-world
        # server/client misconfiguration, not just a hypothetical.
        data = _FRENCH_ICS.encode("cp1252")
        text, _encoding_used = decode_ics_bytes_with_declared_charset(data, "utf-8")
        assert text == _FRENCH_ICS

    def test_falls_back_when_declared_charset_is_unknown(self):
        data = _FRENCH_ICS.encode("latin-1")
        text, _encoding_used = decode_ics_bytes_with_declared_charset(data, "not-a-real-codec")
        assert text == _FRENCH_ICS


class TestDecodeIcsBytesWithContentType:
    """Tests for decode_ics_bytes_with_content_type()."""

    def test_honors_charset_in_content_type_header(self):
        data = _FRENCH_ICS.encode("utf-16")
        text = decode_ics_bytes_with_content_type(data, "text/calendar; charset=utf-16")
        assert text == _FRENCH_ICS

    def test_no_content_type_falls_back_to_detection(self):
        data = _FRENCH_ICS.encode("latin-1")
        text = decode_ics_bytes_with_content_type(data, None)
        assert text == _FRENCH_ICS

    def test_content_type_without_charset_falls_back_to_detection(self):
        data = _FRENCH_ICS.encode("latin-1")
        text = decode_ics_bytes_with_content_type(data, "text/calendar")
        assert text == _FRENCH_ICS
