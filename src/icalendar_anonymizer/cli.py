# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Command-line interface for icalendar-anonymizer.

Provides the `icalendar-anonymize` and `ican` commands for anonymizing
iCalendar files from the command line.
"""

import sys
from typing import BinaryIO

import click
from icalendar import Calendar

from .anonymizer import anonymize
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

        # Read ICS data
        ics_data = input.read()

        if not ics_data:
            click.echo("Error: Input is empty", err=True)
            sys.exit(1)

        if verbose:
            click.echo("Parsing calendar...", err=True)

        # Parse calendar
        try:
            cal = Calendar.from_ical(ics_data)
        except ValueError as e:
            click.echo(f"Error: Invalid ICS file - {e}", err=True)
            sys.exit(1)

        if verbose:
            click.echo("Anonymizing calendar...", err=True)

        # Build field_modes from CLI flags
        field_modes = {}
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

        # Anonymize (uses random salt by default)
        try:
            anonymized_cal = anonymize(cal, field_modes=field_modes or None)
        except (TypeError, ValueError) as e:
            click.echo(f"Error: Anonymization failed - {e}", err=True)
            sys.exit(1)

        if verbose:
            click.echo(f"Writing to: {output_name}", err=True)

        # Write output
        output.write(anonymized_cal.to_ical())

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
