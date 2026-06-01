.. SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
.. SPDX-License-Identifier: AGPL-3.0-or-later

**********************
Command-line interface
**********************

The command-line interface (CLI) provides Unix-style tools for anonymizing iCalendar files from the terminal.

Installation
============

First, install uv as described in :ref:`development-prerequisites`.

Then, clone icalendar-anonymizer and change your working directory to the root of the repository.

..  code-block:: shell

    git clone https://github.com/pycalendar/icalendar-anonymizer.git
    cd icalendar-anonymizer

Then, install the CLI from a local checkout of icalendar-anonymizer with the following command.

..  code-block:: shell

    uv pip install --group cli

This installs the Click dependency and both command-line tools.

Verify installation with the following command.

..  code-block:: shell

    ican --version

This should output the package name and its version number.


Commands
========

Two commands are provided.

:program:`icalendar-anonymize`
    Full command name
:program:`ican`
    Short alias for convenience

Both commands work identically.

Basic usage
===========

This section describes how to use the command-line :program:`icalendar-anonymize` application.
For brevity, examples use the alias form.

The basic usage syntax calls the program, followed optionally by options, then input, and finally output.

..  code-block:: shell

    ican [OPTIONS] [INPUT] [-o OUTPUT]

Anonymize a file
----------------

Read from a file and write to another file:

..  code-block:: shell

    ican calendar.ics -o anonymized.ics

Write to ``stdout``
-------------------

Omit the ``-o`` flag to write to ``stdout``:

..  code-block:: shell

    ican calendar.ics

Read from ``stdin``
-------------------

Omit the input argument to read from ``stdin``:

..  code-block:: shell

    cat calendar.ics | ican > anonymized.ics

Alternatively, use ``-``. 

..  code-block:: shell

    ican - -o anonymized.ics

Options reference
=================

..  program:: icalendar-anonymize
 
..  option:: [INPUT]
 
    Input iCalendar file to anonymize.
    Optional positional argument.
 
    -   **Default**: ``stdin`` (``-``)
    -   **Format**: File path or ``-`` for ``stdin``
    -   **Example**: :code:`ican calendar.ics`
 
..  option:: -o <file>, --output <file>
 
    Output file for anonymized calendar.
 
    -   **Default**: ``stdout`` (``-``)
    -   **Format**: File path or ``-`` for ``stdout``
    -   **Example**: :code:`ican input.ics -o output.ics`
 
..  option:: -v, --verbose
 
    Show processing information on stderr. Displays input/output sources and processing steps.
 
    -   **Flag**: No value required
    -   **Output**: Messages written to stderr (not ``stdout``)
    -   **Example**: :code:`ican -v calendar.ics -o anonymized.ics`
 
    The following example shows verbose output:
 
    ..  code-block:: text
 
        Reading from: calendar.ics
        Parsing calendar...
        Anonymizing calendar...
        Writing to: anonymized.ics
        Done.

..  option:: --version
 
    Display version information and exit.
 
    ..  code-block:: shell
 
        $ ican --version
        icalendar-anonymizer, version 0.1.0
 
..  option:: --help
 
    Show usage information and exit.
 
    ..  code-block:: shell
 
        ican --help

    ..  note::

        The output for "Usage" is somewhat misleading, as Click merges ``-o, --output FILENAME`` with the options instead of as a positional final optional argument.

Field configuration options
----------------------------

Configure how individual fields are anonymized.
The four modes are ``keep``, ``remove``, ``randomize``, and ``replace``.

..  option:: --summary <mode>
 
    Mode for SUMMARY field.
 
    -   **Choices**: ``keep``, ``remove``, ``randomize``, ``replace``
    -   **Default**: ``randomize``
    -   **Example**: :code:`ican --summary keep calendar.ics`
 
..  option:: --description <mode>
 
    Mode for DESCRIPTION field.
 
..  option:: --location <mode>
 
    Mode for LOCATION field.
 
..  option:: --comment <mode>
 
    Mode for COMMENT field.
 
..  option:: --contact <mode>
 
    Mode for CONTACT field.
 
..  option:: --resources <mode>
 
    Mode for RESOURCES field.
 
..  option:: --categories <mode>
 
    Mode for CATEGORIES field.
 
..  option:: --attendee <mode>
 
    Mode for ATTENDEE field.
 
..  option:: --organizer <mode>
 
    Mode for ORGANIZER field.
 
..  option:: --uid <mode>
 
    Mode for UID field.
    
    .. note::

        The ``remove`` mode is not allowed.
 
    -   **Choices**: ``keep``, ``randomize``, ``replace``
    -   **Default**: ``randomize``

Field configuration examples
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Keep summaries, remove locations.

..  code-block:: shell

    ican --summary keep --location remove calendar.ics

Replace descriptions with placeholders.

..  code-block:: shell

    ican --description replace calendar.ics

Combine multiple field modes.

..  code-block:: shell

    ican --summary keep --location remove --description replace calendar.ics

Usage examples
==============

This section provides examples of various ways to use icalendar-anonymizer on the command line.

Basic file conversion
---------------------

Anonymize a single file.

..  code-block:: shell

    ican calendar.ics -o anonymized.ics

Verbose output shows progress.

..  code-block:: shell

    ican -v calendar.ics -o anonymized.ics

Pipeline processing
-------------------

Read from ``stdin`` and write to ``stdout``.

..  code-block:: shell

    cat calendar.ics | ican > anonymized.ics

Explicitly read from ``stdin`` with ``-`` and write to ``stdout``.

..  code-block:: shell

    ican - < calendar.ics > anonymized.ics

Verbose output to ``stderr`` doesn't corrupt ``stdout``.

..  code-block:: shell

    cat calendar.ics | ican -v > anonymized.ics

Batch processing
----------------

Anonymize all ICS files in directory.

..  code-block:: shell

    for file in *.ics; do
        ican "$file" -o "anonymized-$file"
    done

Process files from a list.

..  code-block:: shell

    while read -r file; do
        ican "$file" -o "anon-$(basename "$file")"
    done < file-list.txt

Remote files
------------

Download a remote file and anonymize it.

..  code-block:: shell

    curl https://example.com/calendar.ics | ican > local-anon.ics

Do the previous example with error checking.

..  code-block:: shell

    curl -f https://example.com/calendar.ics | ican -v > local-anon.ics

Combining with other tools
--------------------------

Anonymize and count events.

..  code-block:: shell

    ican calendar.ics | grep -c "BEGIN:VEVENT"

Anonymize and validate the input.

..  code-block:: shell

    ican calendar.ics | ics-validator

Compress the anonymized output.

..  code-block:: shell

    ican calendar.ics | gzip > anonymized.ics.gz

Keep summaries for debugging, pipe to a file, and compress it.

..  code-block:: shell

    ican --summary keep calendar.ics | gzip > debug-anon.ics.gz

Anonymization summary
=====================

The CLI uses the same anonymization as the :doc:`python-api`:

..  seealso::

    See :ref:`python-api-property-handling-reference` for the complete property reference table.

Anonymized properties
---------------------

These properties get anonymized and hashed with SHA-256.

-   Event summaries, descriptions, locations
-   Attendee and organizer names (CN parameter)
-   Comments, categories, resources
-   UIDs (uniqueness preserved)

Preserved properties
--------------------

These properties get preserved for bug reproduction.

-   All dates and times (DTSTART, DTEND, DUE)
-   Recurrence rules (RRULE, RDATE, EXDATE)
-   Status, priority, sequence numbers
-   Timezones (complete VTIMEZONE)

Error handling
==============

The CLI provides error messages for common issues, as described in each of the following subsections.

File not found
--------------

..  code-block:: text

    $ ican nonexistent.ics
    Error: Could not open 'nonexistent.ics': No such file or directory

Exit code: ``2``.

Invalid ICS file
----------------

..  code-block:: text

    $ echo "invalid content" | ican
    Error: Invalid ICS file - Expected instance of <class 'icalendar.cal.Component'>

Exit code: ``1``.

Empty input
-----------

..  code-block:: text

    $ echo "" | ican
    Error: Input is empty

Exit code: ``1``.

Permission denied
-----------------

..  code-block:: text

    $ ican protected.ics -o /root/output.ics
    Error: [Errno 13] Permission denied: '/root/output.ics'

Exit code: ``1``.

Keyboard interrupt
------------------

..  code-block:: text

    $ ican large-file.ics
    ^C
    Interrupted

Exit code: ``130``.

Exit codes
==========

The CLI follows Unix conventions for exit codes:

.. list-table::
   :header-rows: 1
   :widths: 10 20 70

   * - Code
     - Meaning
     - When Used
   * - 0
     - Success
     - Anonymization completed successfully
   * - 1
     - General error
     - Invalid ICS, empty input, I/O errors, unexpected errors
   * - 2
     - File error
     - Input file not found or cannot be opened
   * - 130
     - Interrupted
     - User pressed :kbd:`Ctrl+C` (SIGINT)

Troubleshooting
===============

The following sections provide troubleshooting tips.

Command not found
-----------------

If you get ``command not found`` after installation:

#.  Reinstall with the CLI dependency group:
 
    ..  code-block:: shell
 
        uv sync --group cli
 
#.  Use the full Python module path:
 
    ..  code-block:: shell
 
        python -m icalendar_anonymizer.cli calendar.ics

Binary mode on Windows
----------------------

The CLI automatically handles binary mode on Windows.
You don't need to worry about CRLF line endings.

If you encounter encoding issues on Windows, then use binary mode with PowerShell. 

..  code-block:: shell

    Get-Content calendar.ics -Raw | ican > anonymized.ics

Large files
-----------

The CLI loads the entire file into memory.
For large files over 100MB in size, the following tips will improve performance.

-   Monitor memory usage.
    Use verbose mode to track progress.

    ..  code-block:: shell

        ican -v large-file.ics -o output.ics

-   Process in chunks.
    Split large calendars before anonymizing.

    The following example splits the calendar by year, then anonymizes it.

    ..  code-block:: shell

        grep -A 100 "DTSTART:2024" calendar.ics | ican > 2024-anon.ics

-   Use the :doc:`python-api` for programmatic control over memory usage.

Debugging
---------

Enable verbose mode with the ``-v`` option to see processing steps.

..  code-block:: shell

    ican -v calendar.ics -o anonymized.ics

Check the exit code after running ``ican``, according to your operating system and shell.

.. tab-set::

    ..  tab-item:: Unix/macOS/Linux

        ..  code-block:: shell
        
            ican calendar.ics
            echo $?

    ..  tab-item:: Windows cmd

        ..  code-block:: batch
        
            ican calendar.ics
            echo %ERRORLEVEL%

    ..  tab-item:: Windows PowerShell

        ..  code-block:: ps1con
        
            ican calendar.ics
            echo $LASTEXITCODE


Getting help
============

If you encounter issues with the CLI:

-   Use ``ican --help`` for usage information.
-   Check the `Issue Tracker <https://github.com/pycalendar/icalendar-anonymizer/issues>`_.
-   Open a new issue with:
    -   Your command
    -   Error message
    -   Operating system
    -   Python version (``python --version``)
    -   Package version (``ican --version``)

Integration examples
====================

The following examples describe how to integrate icalendar-anonymizer with various third-party tools.

Git pre-commit hook
--------------------

Automatically anonymize calendars before committing:

..  code-block:: shell

    #!/bin/bash
    # .git/hooks/pre-commit

    for file in *.ics; do
        if [ -f "$file" ]; then
            ican "$file" -o "anon-$file"
            git add "anon-$file"
        fi
    done

cron job
--------

Periodically anonymize shared calendars:

..  code-block:: shell

    # Crontab entry: Anonymize daily at 2 AM
    0 2 * * * /usr/bin/ican /path/to/calendar.ics -o /path/to/anon.ics

See also
========

- :doc:`python-api` - Python API for programmatic usage
- :doc:`../installation` - Installation instructions
- :doc:`../api/index` - Complete API reference
- :doc:`../contributing` - Development guide
