# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Tests for CLI functionality."""

from datetime import datetime

import pytest
from click.testing import CliRunner
from icalendar import Calendar, Event


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
    from icalendar_anonymizer.cli import main

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
    from icalendar_anonymizer.cli import main

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
    from icalendar_anonymizer.cli import main

    # Run CLI with stdin
    result = cli_runner.invoke(main, input=sample_ics)

    # Check success
    assert result.exit_code == 0

    # Check output is valid ICS
    output_cal = Calendar.from_ical(result.output_bytes)
    assert output_cal is not None


def test_anonymize_file_to_file(cli_runner, sample_ics, tmp_path):
    """Test reading from file and writing to file."""
    from icalendar_anonymizer.cli import main

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
    from icalendar_anonymizer.cli import main

    result = cli_runner.invoke(main, ["--version"])

    assert result.exit_code == 0
    assert "icalendar-anonymizer" in result.output
    assert "version" in result.output.lower()


def test_help_flag(cli_runner):
    """Test --help flag."""
    from icalendar_anonymizer.cli import main

    result = cli_runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "--output" in result.output
    assert "--verbose" in result.output


# Verbose Mode Tests


def test_verbose_output(cli_runner, sample_ics, tmp_path):
    """Test verbose mode shows processing information."""
    from icalendar_anonymizer.cli import main

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
    from icalendar_anonymizer.cli import main

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
    from icalendar_anonymizer.cli import main

    invalid_ics = b"This is not a valid ICS file"

    result = cli_runner.invoke(main, input=invalid_ics)

    # Should fail with exit code 1
    assert result.exit_code == 1

    # Should show specific error message
    assert "Error: Invalid ICS" in result.output


def test_empty_input(cli_runner):
    """Test error handling for empty input."""
    from icalendar_anonymizer.cli import main

    result = cli_runner.invoke(main, input=b"")

    assert result.exit_code == 1
    assert "Error" in result.output
    assert "empty" in result.output.lower()


def test_file_not_found(cli_runner):
    """Test error handling for missing input file."""
    from icalendar_anonymizer.cli import main

    result = cli_runner.invoke(main, ["/nonexistent/file.ics"])

    # Click handles file not found and exits with code 2
    assert result.exit_code == 2
    assert "No such file or directory" in result.output


# Output Validation Tests


def test_output_is_valid_ics(cli_runner, sample_ics):
    """Test that output is valid ICS format."""
    from icalendar_anonymizer.cli import main

    result = cli_runner.invoke(main, input=sample_ics)

    assert result.exit_code == 0

    # Should parse without errors
    output_cal = Calendar.from_ical(result.output_bytes)
    assert output_cal is not None
    assert output_cal.get("version") == "2.0"


def test_output_is_anonymized(cli_runner, sample_ics):
    """Test that personal data is removed."""
    from icalendar_anonymizer.cli import main

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
    from icalendar_anonymizer.cli import main

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
    from icalendar_anonymizer.cli import main

    result = cli_runner.invoke(main, input=sample_ics)
    assert result.exit_code == 0


def test_error_exit_code(cli_runner):
    """Test that errors return exit code 1."""
    from icalendar_anonymizer.cli import main

    result = cli_runner.invoke(main, input=b"invalid")
    assert result.exit_code == 1


# Output File Tests


def test_output_to_file(cli_runner, sample_ics, tmp_path):
    """Test writing output to a file."""
    from icalendar_anonymizer.cli import main

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
        from icalendar_anonymizer.cli import main

        input_file = tmp_path / "input.ics"
        input_file.write_bytes(sample_ics)

        result = cli_runner.invoke(main, [str(input_file), "--summary", "keep"])
        assert result.exit_code == 0

        output_cal = Calendar.from_ical(result.output_bytes)
        event = next(iter(output_cal.walk("VEVENT")))
        assert event["summary"] == "Secret Meeting"

    def test_location_remove(self, cli_runner, sample_ics, tmp_path):
        """Test --location remove strips location property."""
        from icalendar_anonymizer.cli import main

        input_file = tmp_path / "input.ics"
        input_file.write_bytes(sample_ics)

        result = cli_runner.invoke(main, [str(input_file), "--location", "remove"])
        assert result.exit_code == 0

        output_cal = Calendar.from_ical(result.output_bytes)
        event = next(iter(output_cal.walk("VEVENT")))
        assert "location" not in event

    def test_description_replace(self, cli_runner, sample_ics, tmp_path):
        """Test --description replace uses placeholder."""
        from icalendar_anonymizer.cli import main

        input_file = tmp_path / "input.ics"
        input_file.write_bytes(sample_ics)

        result = cli_runner.invoke(main, [str(input_file), "--description", "replace"])
        assert result.exit_code == 0

        output_cal = Calendar.from_ical(result.output_bytes)
        event = next(iter(output_cal.walk("VEVENT")))
        assert event["description"] == "[Content removed]"

    def test_summary_randomize_default(self, cli_runner, sample_ics, tmp_path):
        """Test --summary randomize produces hashed value."""
        from icalendar_anonymizer.cli import main

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
        from icalendar_anonymizer.cli import main

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
        from icalendar_anonymizer.cli import main

        input_file = tmp_path / "input.ics"
        input_file.write_bytes(sample_ics)

        result = cli_runner.invoke(main, [str(input_file), "--uid", "keep"])
        assert result.exit_code == 0

        output_cal = Calendar.from_ical(result.output_bytes)
        event = next(iter(output_cal.walk("VEVENT")))
        assert str(event["uid"]) == "test-event-uid@example.com"

    def test_uid_replace(self, cli_runner, sample_ics, tmp_path):
        """Test --uid replace uses placeholder."""
        from icalendar_anonymizer.cli import main

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
        from icalendar_anonymizer.cli import main

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
        from icalendar_anonymizer.cli import main

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
        from icalendar_anonymizer.cli import main

        input_file = tmp_path / "input.ics"
        input_file.write_bytes(sample_ics_latin1)

        result = cli_runner.invoke(main, [str(input_file), "--summary", "keep"])
        assert result.exit_code == 0

        output_cal = Calendar.from_ical(result.output_bytes)
        event = next(iter(output_cal.walk("VEVENT")))
        assert str(event["summary"]) == "Réunion à café Montréal"

    def test_encoding_flag_forces_explicit_encoding(self, cli_runner, sample_ics_latin1, tmp_path):
        """Test --encoding overrides detection and still succeeds for the correct codec."""
        from icalendar_anonymizer.cli import main

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
        from icalendar_anonymizer.cli import main

        input_file = tmp_path / "input.ics"
        input_file.write_bytes(sample_ics_latin1)

        result = cli_runner.invoke(main, [str(input_file), "--encoding", "ascii"])

        assert result.exit_code == 1
        assert "Could not decode input" in result.output

    def test_encoding_flag_unknown_codec_name(self, cli_runner, sample_ics_latin1, tmp_path):
        """Test --encoding with an unrecognized codec name fails cleanly."""
        from icalendar_anonymizer.cli import main

        input_file = tmp_path / "input.ics"
        input_file.write_bytes(sample_ics_latin1)

        result = cli_runner.invoke(main, [str(input_file), "--encoding", "not-a-real-codec"])

        assert result.exit_code == 1
        assert "Could not decode input" in result.output

    def test_verbose_shows_detected_encoding(self, cli_runner, sample_ics_latin1, tmp_path):
        """Test -v reports which encoding was actually used."""
        from icalendar_anonymizer.cli import main

        input_file = tmp_path / "input.ics"
        input_file.write_bytes(sample_ics_latin1)

        result = cli_runner.invoke(main, ["-v", str(input_file)])

        assert result.exit_code == 0
        assert "Detected encoding:" in result.output

    def test_verbose_with_encoding_override_says_override_not_detected(
        self, cli_runner, sample_ics_latin1, tmp_path
    ):
        """Test -v with --encoding reports an override, not a false "detected" claim."""
        from icalendar_anonymizer.cli import main

        input_file = tmp_path / "input.ics"
        input_file.write_bytes(sample_ics_latin1)

        result = cli_runner.invoke(main, ["-v", "--encoding", "latin-1", str(input_file)])

        assert result.exit_code == 0
        assert "Using encoding override: latin-1" in result.output
        assert "Detected encoding:" not in result.output
