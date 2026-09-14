# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Command-line interface for icalendar-anonymizer.

Provides the `icalendar-anonymize` and `ican` commands for anonymizing
iCalendar files from the command line.
"""

import json
import sys
from typing import BinaryIO, Literal, NoReturn, cast

import click
from icalendar import Calendar

from ._encoding import decode_ics_bytes
from .anonymizer import anonymize
from .formats.jcal import anonymize_jcal
from .formats.jscal import anonymize_jscal
from .version import __version__


@click.command(
    help=(
        "Anonymize iCalendar files by removing personal data while preserving technical properties."
    ),
    epilog="Examples:\n\n"
    "  icalendar-anonymize input.ics -o output.ics\n"
    "  cat input.ics | icalendar-anonymize > output.ics\n"
    "  ican -v calendar.ics -o anonymized.ics\n",
)
@click.argument(
    "input",
    type=click.File("rb"),
    default="-",
    required=False,
)
@click.option(
    "-o",
    "--output",
    type=click.File("wb"),
    default="-",
    help="Output file (default: stdout)",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Show processing information",
)
@click.option(
    "--encoding",
    default=None,
    help="Force a specific input encoding (e.g. latin-1, cp1252) instead of auto-detecting.",
)
@click.option(
    "--format",
    "format_",
    type=click.Choice(["auto", "ics", "jscal", "jcal"]),
    default="auto",
    help=(
        "Input format. auto detects from the file extension (.ics, .json as a "
        "JSCalendar object or jCal array). Required to override for stdin."
    ),
)
@click.option(
    "--summary",
    type=click.Choice(["keep", "remove", "randomize", "replace"]),
    help="Mode for SUMMARY field",
)
@click.option(
    "--description",
    type=click.Choice(["keep", "remove", "randomize", "replace"]),
    help="Mode for DESCRIPTION field",
)
@click.option(
    "--location",
    type=click.Choice(["keep", "remove", "randomize", "replace"]),
    help="Mode for LOCATION field",
)
@click.option(
    "--comment",
    type=click.Choice(["keep", "remove", "randomize", "replace"]),
    help="Mode for COMMENT field",
)
@click.option(
    "--contact",
    type=click.Choice(["keep", "remove", "randomize", "replace"]),
    help="Mode for CONTACT field",
)
@click.option(
    "--resources",
    type=click.Choice(["keep", "remove", "randomize", "replace"]),
    help="Mode for RESOURCES field",
)
@click.option(
    "--categories",
    type=click.Choice(["keep", "remove", "randomize", "replace"]),
    help="Mode for CATEGORIES field",
)
@click.option(
    "--attendee",
    type=click.Choice(["keep", "remove", "randomize", "replace"]),
    help="Mode for ATTENDEE field",
)
@click.option(
    "--organizer",
    type=click.Choice(["keep", "remove", "randomize", "replace"]),
    help="Mode for ORGANIZER field",
)
@click.option(
    "--uid",
    type=click.Choice(["keep", "randomize", "replace"]),
    help="Mode for UID field (remove not allowed)",
)
@click.version_option(version=__version__, prog_name="icalendar-anonymizer")
def main(
    input: BinaryIO,  # noqa: A002
    output: BinaryIO,
    verbose: bool,  # noqa: FBT001
    encoding: str | None,
    format_: str,
    summary: str | None,
    description: str | None,
    location: str | None,
    comment: str | None,
    contact: str | None,
    resources: str | None,
    categories: str | None,
    attendee: str | None,
    organizer: str | None,
    uid: str | None,
) -> None:
    """Anonymize an iCalendar file.

    Reads an ICS file, anonymizes personal data, and writes the result.
    Supports stdin/stdout for Unix-style piping.

    Args:
        input: Input file handle (stdin or file)
        output: Output file handle (stdout or file)
        verbose: Whether to show processing information
    """
    try:
        # Get file names for verbose output
        input_name = _get_stream_name(input)
        output_name = _get_stream_name(output)

        if verbose:
            click.echo(f"Reading from: {input_name}", err=True)

        raw_data = input.read()

        if not raw_data:
            _fail("Input is empty")

        try:
            detected_format, parsed_json = _detect_format(format_, input, raw_data)
        except ValueError as e:
            _fail(str(e))

        if verbose:
            click.echo(f"Format: {detected_format}", err=True)

        field_mapping = {
            "SUMMARY": summary,
            "DESCRIPTION": description,
            "LOCATION": location,
            "COMMENT": comment,
            "CONTACT": contact,
            "RESOURCES": resources,
            "CATEGORIES": categories,
            "ATTENDEE": attendee,
            "ORGANIZER": organizer,
            "UID": uid,
        }
        field_modes = {field: value for field, value in field_mapping.items() if value}

        if detected_format == "jscal" and field_modes:
            click.echo(
                f"Warning: {', '.join(f'--{f.lower()}' for f in field_modes)} "
                "ignored for JSCalendar input",
                err=True,
            )
            field_modes = {}

        if detected_format == "ics":
            if verbose:
                click.echo("Decoding input...", err=True)

            try:
                ics_text, used_encoding = decode_ics_bytes(raw_data, encoding=encoding)
            except (UnicodeDecodeError, LookupError) as e:
                _fail(f"Could not decode input with encoding {encoding!r} - {e}")

            if verbose:
                if encoding is not None:
                    click.echo(f"Using encoding override: {used_encoding}", err=True)
                else:
                    click.echo(f"Detected encoding: {used_encoding}", err=True)
                click.echo("Parsing calendar...", err=True)

            try:
                cal = Calendar.from_ical(ics_text)
            except ValueError as e:
                _fail(f"Invalid ICS file - {e}")

            if verbose:
                click.echo("Anonymizing calendar...", err=True)

            try:
                anonymized_cal = anonymize(cal, field_modes=field_modes or None)
            except (TypeError, ValueError) as e:
                _fail(f"Anonymization failed - {e}")

            result_bytes = anonymized_cal.to_ical()
        else:
            if encoding is not None:
                click.echo("Warning: --encoding is ignored for JSON input", err=True)

            if parsed_json is not None:
                parsed = parsed_json
            else:
                try:
                    parsed = json.loads(raw_data.decode("utf-8"))
                except UnicodeDecodeError as e:
                    _fail(f"Could not decode JSON input as UTF-8 - {e}")
                except json.JSONDecodeError as e:
                    _fail(f"Could not parse input as JSON - {e}")

            if verbose:
                click.echo("Anonymizing calendar...", err=True)

            try:
                if detected_format == "jscal":
                    result = anonymize_jscal(parsed)
                else:
                    result = anonymize_jcal(parsed, field_modes=field_modes or None)
            except (TypeError, ValueError) as e:
                _fail(f"Anonymization failed - {e}")

            result_bytes = json.dumps(result).encode("utf-8")

        if verbose:
            click.echo(f"Writing to: {output_name}", err=True)

        # Write output
        output.write(result_bytes)

        if verbose:
            click.echo("Done.", err=True)

    except OSError as e:
        # Handle file I/O errors (permission denied, disk full, etc.)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        click.echo("\nInterrupted", err=True)
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:  # noqa: BLE001
        # Catch-all for unexpected errors
        click.echo(f"Error: Unexpected error - {e}", err=True)
        click.echo(
            "Please report this issue at https://github.com/pycalendar/icalendar-anonymizer/issues",
            err=True,
        )
        sys.exit(1)


def _fail(message: str) -> NoReturn:
    """Print a CLI error and exit(1)."""
    click.echo(f"Error: {message}", err=True)
    sys.exit(1)


def _detect_format(
    format_: str, input_stream: BinaryIO, raw_data: bytes
) -> tuple[Literal["ics", "jscal", "jcal"], dict | list | None]:
    """Detect the input format from an explicit override or the file extension.

    For "auto" detection on a .json file, this parses the JSON to tell
    JSCalendar (an object) apart from jCal (an array), and returns that
    parsed value so the caller doesn't need to parse it again.

    Args:
        format_: The --format option value ("auto", "ics", "jscal", or "jcal")
        input_stream: The input stream, used to read its name/extension for "auto"
        raw_data: The raw input bytes, parsed as JSON when detecting between
            JSCalendar and jCal

    Returns:
        A (format, parsed_json) tuple. parsed_json is None unless format
        was auto-detected from .json content, in which case it's already
        parsed and the caller should reuse it instead of parsing again.

    Raises:
        ValueError: If the input can't be parsed as JSON for a .json file,
            or parses to neither a JSON object nor a JSON array
    """
    if format_ != "auto":
        # format_ is a plain str at the type level (Click has no Literal
        # return type for click.Choice), but the "auto", "ics", "jscal",
        # "jcal" choice is enforced at runtime by the --format option's
        # click.Choice, so this narrowing is safe.
        return cast("Literal['ics', 'jscal', 'jcal']", format_), None

    # getattr, not direct attribute access: under click.testing.CliRunner,
    # piped stdin is a raw BytesIO with no .name attribute at all.
    name = getattr(input_stream, "name", None) or ""
    if not name.lower().endswith(".json"):
        return "ics", None

    try:
        parsed = json.loads(raw_data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ValueError(f"Could not parse .json input as JSON - {e}") from e

    if isinstance(parsed, dict):
        return "jscal", parsed
    if isinstance(parsed, list):
        return "jcal", parsed
    raise ValueError(
        ".json input must be a JSON object (JSCalendar) or array (jCal), "
        f"got {type(parsed).__name__}"
    )


def _get_stream_name(stream: BinaryIO) -> str:
    """Get a human-readable name for a stream.

    Args:
        stream: File handle or stdin/stdout

    Returns:
        Stream name (e.g., "<stdin>", "/path/to/file.ics")
    """
    # Check if stream is stdin/stdout
    if stream == sys.stdin.buffer:
        return "<stdin>"
    if stream == sys.stdout.buffer:
        return "<stdout>"

    # Get file path from stream
    name = getattr(stream, "name", None)
    if name and name not in ("<stdin>", "<stdout>"):
        return name

    # Fallback
    return "<stream>"


if __name__ == "__main__":
    main()
