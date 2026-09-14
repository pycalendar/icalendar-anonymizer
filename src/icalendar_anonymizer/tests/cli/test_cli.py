# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Tests for CLI functionality."""

import json
from datetime import datetime

import pytest
from click.testing import CliRunner
from icalendar import Calendar, Event

from icalendar_anonymizer.cli import main


@pytest.fixture
def sample_ics():
    """Create sample ICS data for testing."""
    cal = Calendar()
    cal.add("prodid", "-//Test//Test//EN")
    cal.add("version", "2.0")

    event = Event()
    event.add("summary", "Secret Meeting")
    event.add("description", "Confidential discussion")
    event.add("location", "Private Office")
    event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))
    event.add("dtend", datetime(2024, 1, 15, 15, 0, 0))
    event.add("uid", "test-event-uid@example.com")

    cal.add_component(event)
    return cal.to_ical()


@pytest.fixture
def cli_runner():
    """Create Click test runner."""
    return CliRunner()


# Basic Functionality Tests


def test_anonymize_file_to_stdout(cli_runner, sample_ics, tmp_path):
    """Test reading from file and writing to stdout."""

    # Create input file
    input_file = tmp_path / "input.ics"
    input_file.write_bytes(sample_ics)

    # Run CLI
    result = cli_runner.invoke(main, [str(input_file)])

    # Check success
    assert result.exit_code == 0

    # Check output is valid ICS
    output_cal = Calendar.from_ical(result.output_bytes)
    assert output_cal is not None

    # Check anonymization occurred
    event = next(iter(output_cal.walk("VEVENT")))
    assert event["summary"] != "Secret Meeting"

    # Check date preserved
    assert event["dtstart"].dt == datetime(2024, 1, 15, 14, 0, 0)


def test_anonymize_stdin_to_file(cli_runner, sample_ics, tmp_path):
    """Test reading from stdin and writing to file."""

    output_file = tmp_path / "output.ics"

    # Run CLI with stdin
    result = cli_runner.invoke(main, ["-o", str(output_file)], input=sample_ics)

    # Check success
    assert result.exit_code == 0
    assert output_file.exists()

    # Verify output file is valid ICS
    output_cal = Calendar.from_ical(output_file.read_bytes())
    assert output_cal is not None


def test_anonymize_stdin_to_stdout(cli_runner, sample_ics):
    """Test reading from stdin and writing to stdout."""

    # Run CLI with stdin
    result = cli_runner.invoke(main, input=sample_ics)

    # Check success
    assert result.exit_code == 0

    # Check output is valid ICS
    output_cal = Calendar.from_ical(result.output_bytes)
    assert output_cal is not None


def test_anonymize_file_to_file(cli_runner, sample_ics, tmp_path):
    """Test reading from file and writing to file."""

    input_file = tmp_path / "input.ics"
    input_file.write_bytes(sample_ics)
    output_file = tmp_path / "output.ics"

    # Run CLI
    result = cli_runner.invoke(main, [str(input_file), "-o", str(output_file)])

    # Check success
    assert result.exit_code == 0
    assert output_file.exists()

    # Verify output
    output_cal = Calendar.from_ical(output_file.read_bytes())
    assert output_cal is not None


# Version and Help Tests


def test_version_flag(cli_runner):
    """Test --version flag."""

    result = cli_runner.invoke(main, ["--version"])

    assert result.exit_code == 0
    assert "icalendar-anonymizer" in result.output
    assert "version" in result.output.lower()


def test_help_flag(cli_runner):
    """Test --help flag."""

    result = cli_runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "--output" in result.output
    assert "--verbose" in result.output


# Verbose Mode Tests


def test_verbose_output(cli_runner, sample_ics, tmp_path):
    """Test verbose mode shows processing information."""

    input_file = tmp_path / "input.ics"
    input_file.write_bytes(sample_ics)

    result = cli_runner.invoke(main, ["-v", str(input_file)])

    assert result.exit_code == 0

    # Check verbose messages appear in output
    assert "Reading from:" in result.output
    assert "Anonymizing" in result.output
    assert "Done" in result.output


def test_verbose_doesnt_corrupt_stdout(cli_runner, sample_ics, tmp_path):
    """Test that verbose output doesn't corrupt stdout."""

    # Use output file to avoid CliRunner mixing streams
    output_file = tmp_path / "output.ics"
    result = cli_runner.invoke(main, ["-v", "-o", str(output_file)], input=sample_ics)

    assert result.exit_code == 0

    # Verbose messages should appear in output (CliRunner captures both stdout and stderr)
    assert "Reading from:" in result.output
    assert "Done" in result.output

    # Output file should still be valid ICS (verbose went to stderr)
    output_cal = Calendar.from_ical(output_file.read_bytes())
    assert output_cal is not None


# Error Handling Tests


def test_invalid_ics_data(cli_runner):
    """Test error handling for invalid ICS data."""

    invalid_ics = b"This is not a valid ICS file"

    result = cli_runner.invoke(main, input=invalid_ics)

    # Should fail with exit code 1
    assert result.exit_code == 1

    # Should show specific error message
    assert "Error: Invalid ICS" in result.output


def test_empty_input(cli_runner):
    """Test error handling for empty input."""

    result = cli_runner.invoke(main, input=b"")

    assert result.exit_code == 1
    assert "Error" in result.output
    assert "empty" in result.output.lower()


def test_file_not_found(cli_runner):
    """Test error handling for missing input file."""

    result = cli_runner.invoke(main, ["/nonexistent/file.ics"])

    # Click handles file not found and exits with code 2
    assert result.exit_code == 2
    assert "No such file or directory" in result.output


# Output Validation Tests


def test_output_is_valid_ics(cli_runner, sample_ics):
    """Test that output is valid ICS format."""

    result = cli_runner.invoke(main, input=sample_ics)

    assert result.exit_code == 0

    # Should parse without errors
    output_cal = Calendar.from_ical(result.output_bytes)
    assert output_cal is not None
    assert output_cal.get("version") == "2.0"


def test_output_is_anonymized(cli_runner, sample_ics):
    """Test that personal data is removed."""

    result = cli_runner.invoke(main, input=sample_ics)

    assert result.exit_code == 0

    output_cal = Calendar.from_ical(result.output_bytes)
    event = next(iter(output_cal.walk("VEVENT")))

    # Personal data should be anonymized (check that values changed)
    assert event["summary"] != "Secret Meeting"
    # Hashed summary should be hex-like string
    summary_str = str(event.get("summary"))
    assert len(summary_str) > 0
    assert summary_str != "Secret Meeting"


def test_preserves_dates(cli_runner, sample_ics):
    """Test that dates are preserved during anonymization."""

    result = cli_runner.invoke(main, input=sample_ics)

    assert result.exit_code == 0

    output_cal = Calendar.from_ical(result.output_bytes)
    event = next(iter(output_cal.walk("VEVENT")))

    # Check dates are exactly preserved
    assert event["dtstart"].dt == datetime(2024, 1, 15, 14, 0, 0)
    assert event["dtend"].dt == datetime(2024, 1, 15, 15, 0, 0)


# Exit Code Tests


def test_success_exit_code(cli_runner, sample_ics):
    """Test that successful execution returns exit code 0."""

    result = cli_runner.invoke(main, input=sample_ics)
    assert result.exit_code == 0


def test_error_exit_code(cli_runner):
    """Test that errors return exit code 1."""

    result = cli_runner.invoke(main, input=b"invalid")
    assert result.exit_code == 1


# Output File Tests


def test_output_to_file(cli_runner, sample_ics, tmp_path):
    """Test writing output to a file."""

    output_file = tmp_path / "output.ics"

    result = cli_runner.invoke(main, ["-o", str(output_file)], input=sample_ics)

    assert result.exit_code == 0
    assert output_file.exists()

    # Verify output file is valid ICS
    output_cal = Calendar.from_ical(output_file.read_bytes())
    assert output_cal is not None


# Field Mode Integration Tests


class TestFieldModeFlags:
    """Integration tests for per-field CLI flags."""

    def test_summary_keep(self, cli_runner, sample_ics, tmp_path):
        """Test --summary keep preserves summary value."""

        input_file = tmp_path / "input.ics"
        input_file.write_bytes(sample_ics)

        result = cli_runner.invoke(main, [str(input_file), "--summary", "keep"])
        assert result.exit_code == 0

        output_cal = Calendar.from_ical(result.output_bytes)
        event = next(iter(output_cal.walk("VEVENT")))
        assert event["summary"] == "Secret Meeting"

    def test_location_remove(self, cli_runner, sample_ics, tmp_path):
        """Test --location remove strips location property."""

        input_file = tmp_path / "input.ics"
        input_file.write_bytes(sample_ics)

        result = cli_runner.invoke(main, [str(input_file), "--location", "remove"])
        assert result.exit_code == 0

        output_cal = Calendar.from_ical(result.output_bytes)
        event = next(iter(output_cal.walk("VEVENT")))
        assert "location" not in event

    def test_description_replace(self, cli_runner, sample_ics, tmp_path):
        """Test --description replace uses placeholder."""

        input_file = tmp_path / "input.ics"
        input_file.write_bytes(sample_ics)

        result = cli_runner.invoke(main, [str(input_file), "--description", "replace"])
        assert result.exit_code == 0

        output_cal = Calendar.from_ical(result.output_bytes)
        event = next(iter(output_cal.walk("VEVENT")))
        assert event["description"] == "[Content removed]"

    def test_summary_randomize_default(self, cli_runner, sample_ics, tmp_path):
        """Test --summary randomize produces hashed value."""

        input_file = tmp_path / "input.ics"
        input_file.write_bytes(sample_ics)

        result = cli_runner.invoke(main, [str(input_file), "--summary", "randomize"])
        assert result.exit_code == 0

        output_cal = Calendar.from_ical(result.output_bytes)
        event = next(iter(output_cal.walk("VEVENT")))
        # Randomize should hash the value (different from original)
        assert event["summary"] != "Secret Meeting"
        assert len(str(event["summary"])) > 0

    def test_combined_flags(self, cli_runner, sample_ics, tmp_path):
        """Test multiple field flags work together."""

        input_file = tmp_path / "input.ics"
        input_file.write_bytes(sample_ics)

        result = cli_runner.invoke(
            main,
            [
                str(input_file),
                "--summary",
                "keep",
                "--location",
                "remove",
                "--description",
                "replace",
            ],
        )
        assert result.exit_code == 0

        output_cal = Calendar.from_ical(result.output_bytes)
        event = next(iter(output_cal.walk("VEVENT")))

        # Verify each mode applied correctly
        assert event["summary"] == "Secret Meeting"  # kept
        assert "location" not in event  # removed
        assert event["description"] == "[Content removed]"  # replaced

    def test_uid_keep(self, cli_runner, sample_ics, tmp_path):
        """Test --uid keep preserves UID."""

        input_file = tmp_path / "input.ics"
        input_file.write_bytes(sample_ics)

        result = cli_runner.invoke(main, [str(input_file), "--uid", "keep"])
        assert result.exit_code == 0

        output_cal = Calendar.from_ical(result.output_bytes)
        event = next(iter(output_cal.walk("VEVENT")))
        assert str(event["uid"]) == "test-event-uid@example.com"

    def test_uid_replace(self, cli_runner, sample_ics, tmp_path):
        """Test --uid replace uses placeholder."""

        input_file = tmp_path / "input.ics"
        input_file.write_bytes(sample_ics)

        result = cli_runner.invoke(main, [str(input_file), "--uid", "replace"])
        assert result.exit_code == 0

        output_cal = Calendar.from_ical(result.output_bytes)
        event = next(iter(output_cal.walk("VEVENT")))
        uid = str(event["uid"])
        assert "redacted-" in uid
        assert "@anonymous.local" in uid

    def test_uid_randomize(self, cli_runner, sample_ics, tmp_path):
        """Test --uid randomize produces hashed UID."""

        input_file = tmp_path / "input.ics"
        input_file.write_bytes(sample_ics)

        result = cli_runner.invoke(main, [str(input_file), "--uid", "randomize"])
        assert result.exit_code == 0

        output_cal = Calendar.from_ical(result.output_bytes)
        event = next(iter(output_cal.walk("VEVENT")))
        uid = str(event["uid"])
        assert uid != "test-event-uid@example.com"
        assert len(uid) > 0

    def test_no_flags_uses_defaults(self, cli_runner, sample_ics, tmp_path):
        """Test that no flags results in default randomize behavior."""

        input_file = tmp_path / "input.ics"
        input_file.write_bytes(sample_ics)

        result = cli_runner.invoke(main, [str(input_file)])
        assert result.exit_code == 0

        output_cal = Calendar.from_ical(result.output_bytes)
        event = next(iter(output_cal.walk("VEVENT")))

        # All fields should be randomized by default
        assert event["summary"] != "Secret Meeting"
        assert event["description"] != "Confidential discussion"
        assert str(event["uid"]) != "test-event-uid@example.com"


# Encoding Tests


@pytest.fixture
def sample_ics_latin1():
    """Realistic ICS body with accented French text, encoded as Latin-1."""
    ics_text = (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Test//Test//EN\r\n"
        "BEGIN:VEVENT\r\nUID:test-event-uid@example.com\r\n"
        "DTSTART:20240115T140000Z\r\nDTEND:20240115T150000Z\r\n"
        "SUMMARY:Réunion à café Montréal\r\n"
        "END:VEVENT\r\nEND:VCALENDAR\r\n"
    )
    return ics_text.encode("latin-1")


class TestEncodingFlag:
    """Tests for legacy encoding detection and the --encoding override."""

    def test_latin1_file_anonymizes_correctly(self, cli_runner, sample_ics_latin1, tmp_path):
        """Test a Latin-1 file with no declared charset is decoded and anonymized."""

        input_file = tmp_path / "input.ics"
        input_file.write_bytes(sample_ics_latin1)

        result = cli_runner.invoke(main, [str(input_file), "--summary", "keep"])
        assert result.exit_code == 0

        output_cal = Calendar.from_ical(result.output_bytes)
        event = next(iter(output_cal.walk("VEVENT")))
        assert str(event["summary"]) == "Réunion à café Montréal"

    def test_encoding_flag_forces_explicit_encoding(self, cli_runner, sample_ics_latin1, tmp_path):
        """Test --encoding overrides detection and still succeeds for the correct codec."""

        input_file = tmp_path / "input.ics"
        input_file.write_bytes(sample_ics_latin1)

        result = cli_runner.invoke(
            main, [str(input_file), "--encoding", "latin-1", "--summary", "keep"]
        )
        assert result.exit_code == 0

        output_cal = Calendar.from_ical(result.output_bytes)
        event = next(iter(output_cal.walk("VEVENT")))
        assert str(event["summary"]) == "Réunion à café Montréal"

    def test_encoding_flag_wrong_codec_fails_cleanly(self, cli_runner, sample_ics_latin1, tmp_path):
        """Test --encoding with the wrong codec is a hard error, not a silent guess."""

        input_file = tmp_path / "input.ics"
        input_file.write_bytes(sample_ics_latin1)

        result = cli_runner.invoke(main, [str(input_file), "--encoding", "ascii"])

        assert result.exit_code == 1
        assert "Could not decode input" in result.output

    def test_encoding_flag_unknown_codec_name(self, cli_runner, sample_ics_latin1, tmp_path):
        """Test --encoding with an unrecognized codec name fails cleanly."""

        input_file = tmp_path / "input.ics"
        input_file.write_bytes(sample_ics_latin1)

        result = cli_runner.invoke(main, [str(input_file), "--encoding", "not-a-real-codec"])

        assert result.exit_code == 1
        assert "Could not decode input" in result.output

    def test_verbose_shows_detected_encoding(self, cli_runner, sample_ics_latin1, tmp_path):
        """Test -v reports which encoding was actually used."""

        input_file = tmp_path / "input.ics"
        input_file.write_bytes(sample_ics_latin1)

        result = cli_runner.invoke(main, ["-v", str(input_file)])

        assert result.exit_code == 0
        assert "Detected encoding:" in result.output

    def test_verbose_with_encoding_override_says_override_not_detected(
        self, cli_runner, sample_ics_latin1, tmp_path
    ):
        """Test -v with --encoding reports an override, not a false "detected" claim."""

        input_file = tmp_path / "input.ics"
        input_file.write_bytes(sample_ics_latin1)

        result = cli_runner.invoke(main, ["-v", "--encoding", "latin-1", str(input_file)])

        assert result.exit_code == 0
        assert "Using encoding override: latin-1" in result.output
        assert "Detected encoding:" not in result.output


# Format Detection Tests


@pytest.fixture
def sample_jcal():
    """Create sample jCal data (a real .ics fixture converted via to_jcal())."""
    cal = Calendar()
    cal.add("prodid", "-//Test//Test//EN")
    cal.add("version", "2.0")

    event = Event()
    event.add("summary", "Secret Meeting")
    event.add("uid", "test-event-uid@example.com")
    event.add("dtstart", datetime(2024, 1, 15, 14, 0, 0))

    cal.add_component(event)

    return json.dumps(cal.to_jcal()).encode("utf-8")


@pytest.fixture
def sample_jscal():
    """Create sample JSCalendar data."""

    data = {
        "@type": "Event",
        "uid": "test-event-uid@example.com",
        "title": "Secret Meeting",
        "start": "2024-01-15T14:00:00",
    }
    return json.dumps(data).encode("utf-8")


class TestFormatDetection:
    """Tests for CLI format auto-detection and the --format override."""

    def test_detects_ics_extension(self, cli_runner, sample_ics, tmp_path):
        input_file = tmp_path / "input.ics"
        input_file.write_bytes(sample_ics)

        result = cli_runner.invoke(main, [str(input_file)])
        assert result.exit_code == 0
        output_cal = Calendar.from_ical(result.output_bytes)
        assert output_cal is not None

    def test_detects_json_dict_as_jscal(self, cli_runner, sample_jscal, tmp_path):
        input_file = tmp_path / "input.json"
        input_file.write_bytes(sample_jscal)

        verbose_result = cli_runner.invoke(main, ["-v", str(input_file)])
        assert verbose_result.exit_code == 0
        assert "Format: jscal" in verbose_result.output

        result = cli_runner.invoke(main, [str(input_file)])
        assert result.exit_code == 0

        output = json.loads(result.output_bytes)
        assert output["title"] != "Secret Meeting"
        assert output["start"] == "2024-01-15T14:00:00"

    def test_detects_json_array_as_jcal(self, cli_runner, sample_jcal, tmp_path):
        input_file = tmp_path / "input.json"
        input_file.write_bytes(sample_jcal)

        verbose_result = cli_runner.invoke(main, ["-v", str(input_file)])
        assert verbose_result.exit_code == 0
        assert "Format: jcal" in verbose_result.output

        result = cli_runner.invoke(main, [str(input_file)])
        assert result.exit_code == 0

        output = json.loads(result.output_bytes)
        cal = Calendar.from_jcal(output)
        event = next(iter(cal.walk("VEVENT")))
        assert str(event.get("SUMMARY")) != "Secret Meeting"

    def test_malformed_json_raises_clean_error(self, cli_runner, tmp_path):
        input_file = tmp_path / "input.json"
        input_file.write_bytes(b'{"not": "valid json')

        result = cli_runner.invoke(main, [str(input_file)])
        assert result.exit_code == 1
        assert "Error" in result.output

    def test_json_neither_dict_nor_list_raises_clean_error(self, cli_runner, tmp_path):
        input_file = tmp_path / "input.json"
        input_file.write_bytes(b'"just a string"')

        result = cli_runner.invoke(main, [str(input_file)])
        assert result.exit_code == 1
        assert "must be a JSON object" in result.output

    def test_format_override_flag(self, cli_runner, sample_jscal):
        # No .json extension for detection to key off, so --format is required.
        result = cli_runner.invoke(main, ["--format", "jscal"], input=sample_jscal)
        assert result.exit_code == 0

        output = json.loads(result.output_bytes)
        assert output["title"] != "Secret Meeting"

    def test_stdin_defaults_to_ics(self, cli_runner, sample_ics):
        result = cli_runner.invoke(main, input=sample_ics)
        assert result.exit_code == 0
        output_cal = Calendar.from_ical(result.output_bytes)
        assert output_cal is not None

    def test_jscal_input_ignores_ics_field_flags_with_warning(
        self, cli_runner, sample_jscal, tmp_path
    ):
        input_file = tmp_path / "input.json"
        input_file.write_bytes(sample_jscal)

        result = cli_runner.invoke(main, ["--summary", "keep", str(input_file)])
        assert result.exit_code == 0
        assert "ignored for JSCalendar input" in result.output

    def test_jcal_input_honors_ics_field_flags(self, cli_runner, sample_jcal, tmp_path):
        # Unlike JSCalendar, jCal is a direct JSON encoding of iCalendar's
        # own property model, so anonymize_jcal() supports the exact same
        # field_modes vocabulary as .ics input, and the CLI's --summary/etc.
        # flags must reach it rather than being dropped as "JSON input".

        input_file = tmp_path / "input.json"
        input_file.write_bytes(sample_jcal)

        result = cli_runner.invoke(main, ["--summary", "keep", str(input_file)])
        assert result.exit_code == 0
        assert "ignored" not in result.output
        assert "Secret Meeting" in result.output

    def test_jscal_output_is_valid_json(self, cli_runner, sample_jscal, tmp_path):
        input_file = tmp_path / "input.json"
        input_file.write_bytes(sample_jscal)

        result = cli_runner.invoke(main, [str(input_file)])
        assert result.exit_code == 0

        output = json.loads(result.output_bytes)
        assert isinstance(output, dict)

    def test_jcal_output_is_valid_json_and_valid_jcal_shape(
        self, cli_runner, sample_jcal, tmp_path
    ):
        input_file = tmp_path / "input.json"
        input_file.write_bytes(sample_jcal)

        result = cli_runner.invoke(main, [str(input_file)])
        assert result.exit_code == 0

        output = json.loads(result.output_bytes)
        assert isinstance(output, list)
        assert output[0] == "vcalendar"
        # Confirms it round-trips through icalendar's own jCal parser.
        Calendar.from_jcal(output)

    def test_json_input_bypasses_encoding_fallback(self, cli_runner, tmp_path):
        input_file = tmp_path / "input.json"
        # Invalid UTF-8 bytes inside what looks like JSON content.
        input_file.write_bytes('{"title": "Café"}'.encode("cp1252"))

        result = cli_runner.invoke(main, [str(input_file)])
        assert result.exit_code == 1
        assert "Error" in result.output

    def test_explicit_format_with_encoding_flag_warns(self, cli_runner):
        result = cli_runner.invoke(
            main,
            ["--format", "jscal", "--encoding", "latin-1"],
            input=b'{"@type": "Event", "uid": "x", "title": "y"}',
        )
        assert result.exit_code == 0
        assert "--encoding is ignored for JSON input" in result.output

    def test_explicit_format_with_invalid_utf8_fails_cleanly(self, cli_runner):
        # --format bypasses extension-based auto-detection entirely, so this
        # exercises a different code path than the .json-extension case above.
        result = cli_runner.invoke(
            main, ["--format", "jscal"], input='{"title": "Café"}'.encode("cp1252")
        )
        assert result.exit_code == 1
        assert "Error" in result.output

    def test_explicit_format_with_malformed_json_fails_cleanly(self, cli_runner):
        result = cli_runner.invoke(main, ["--format", "jscal"], input=b'{"not": "valid json')
        assert result.exit_code == 1
        assert "Error" in result.output

    def test_explicit_format_jscal_anonymization_error(self, cli_runner):
        # Not a dict, so anonymize_jscal() raises TypeError.
        result = cli_runner.invoke(main, ["--format", "jscal"], input=b"[1, 2, 3]")
        assert result.exit_code == 1
        assert "Anonymization failed" in result.output

    def test_explicit_format_jcal_anonymization_error(self, cli_runner):
        # Not a list, so anonymize_jcal() raises TypeError.
        result = cli_runner.invoke(main, ["--format", "jcal"], input=b'{"a": 1}')
        assert result.exit_code == 1
        assert "Anonymization failed" in result.output
