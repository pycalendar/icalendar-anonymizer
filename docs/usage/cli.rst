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

.. code-block:: shell

    ican calendar.ics

Read from ``stdin``
-------------------

Omit the input argument, or use ``-``, to read from ``stdin``:

.. code-block:: shell

    cat calendar.ics | ican > anonymized.ics
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

Examples
========

Unix-style piping
-----------------

Combine with other Unix tools:

.. code-block:: shell

    # Download and anonymize
    curl https://example.com/calendar.ics | ican > anonymized.ics

    # Anonymize multiple files
    for f in *.ics; do ican "$f" -o "anon-$f"; done

    # Anonymize and compress
    cat calendar.ics | ican | gzip > anonymized.ics.gz


Basic file conversion
---------------------

.. code-block:: shell

    # Anonymize a single file
    ican calendar.ics -o anonymized.ics

    # Verbose output shows progress
    ican -v calendar.ics -o anonymized.ics

Pipeline processing
-------------------

.. code-block:: shell

    # Read from ``stdin``, write to ``stdout``
    cat calendar.ics | ican > anonymized.ics

    # Explicit ``stdin``/``stdout`` with -
    ican - < calendar.ics > anonymized.ics

    # Verbose output to stderr doesn't corrupt ``stdout``
    cat calendar.ics | ican -v > anonymized.ics

Batch processing
----------------

.. code-block:: shell

    # Anonymize all ICS files in directory
    for file in *.ics; do
        ican "$file" -o "anonymized-$file"
    done

    # Process files from a list
    while read -r file; do
        ican "$file" -o "anon-$(basename "$file")"
    done < file-list.txt

Remote files
------------

.. code-block:: shell

    # Download and anonymize
    curl https://example.com/calendar.ics | ican > local-anon.ics

    # With error checking
    curl -f https://example.com/calendar.ics | ican -v > local-anon.ics

Combining with other tools
---------------------------

.. code-block:: shell

    # Anonymize and count events
    ican calendar.ics | grep -c "BEGIN:VEVENT"

    # Anonymize and validate
    ican calendar.ics | ics-validator

    # Compress anonymized output
    ican calendar.ics | gzip > anonymized.ics.gz

    # Keep summaries for debugging, pipe to file
    ican --summary keep calendar.ics | gzip > debug-anon.ics.gz

What gets anonymized?
=====================

.. note::
   This is a quick reference. See :doc:`python-api` for the complete property reference table.

The CLI uses the same anonymization as the Python API:

**Anonymized (hashed with SHA-256):**

- Event summaries, descriptions, locations
- Attendee and organizer names (CN parameter)
- Comments, categories, resources
- UIDs (uniqueness preserved)

**Preserved for bug reproduction:**

- All dates and times (DTSTART, DTEND, DUE)
- Recurrence rules (RRULE, RDATE, EXDATE)
- Status, priority, sequence numbers
- Timezones (complete VTIMEZONE)

See :doc:`python-api` for complete property reference.

Error handling
==============

The CLI provides clear error messages for common issues.

File not found
--------------

.. code-block:: text

    $ ican nonexistent.ics
    Error: Could not open 'nonexistent.ics': No such file or directory

**Exit code**: 2

Invalid ICS file
----------------

.. code-block:: text

    $ echo "invalid content" | ican
    Error: Invalid ICS file - Expected instance of <class 'icalendar.cal.Component'>

**Exit code**: 1

Empty input
-----------

.. code-block:: text

    $ echo "" | ican
    Error: Input is empty

**Exit code**: 1

Permission denied
-----------------

.. code-block:: text

    $ ican protected.ics -o /root/output.ics
    Error: [Errno 13] Permission denied: '/root/output.ics'

**Exit code**: 1

Keyboard interrupt
------------------

.. code-block:: text

    $ ican large-file.ics
    ^C
    Interrupted

**Exit code**: 130

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
     - User pressed Ctrl+C (SIGINT)

Troubleshooting
===============

Command not found
-----------------

If you get ``command not found`` after installation:

1. Verify the CLI extra is installed:

   .. code-block:: shell

       pip show icalendar-anonymizer | grep cli

2. Check your PATH includes pip's script directory:

   .. code-block:: shell

       python -m site --user-base

3. Reinstall with CLI extra:

   .. code-block:: shell

       pip install --force-reinstall icalendar-anonymizer[cli]

4. Use the full Python module path:

   .. code-block:: shell

       python -m icalendar_anonymizer.cli calendar.ics

Binary mode on windows
----------------------

The CLI automatically handles binary mode on Windows. You don't need to worry about CRLF line endings.

If you encounter encoding issues on Windows:

.. code-block:: shell

    # Use binary mode with PowerShell
    Get-Content calendar.ics -Raw | ican > anonymized.ics

Large files
-----------

The CLI loads the entire file into memory. For very large files (>100MB):

1. **Monitor memory usage**: Use verbose mode to track progress

   .. code-block:: shell

       ican -v large-file.ics -o output.ics

2. **Process in chunks**: Split large calendars before anonymizing

   .. code-block:: shell

       # Example: Split by year, then anonymize
       grep -A 100 "DTSTART:2024" calendar.ics | ican > 2024-anon.ics

3. **Use the Python API**: For programmatic control over memory usage

Hyphen as filename
------------------

To use a file literally named ``-``:

.. code-block:: shell

    # Use ./ prefix to treat - as a filename
    ican ./- -o output.ics

Debugging
---------

Enable verbose mode to see processing steps:

.. code-block:: shell

    ican -v calendar.ics -o anonymized.ics

Check the exit code after running:

.. code-block:: shell

    ican calendar.ics
    echo $?  # Unix/macOS/Linux
    echo %ERRORLEVEL%  # Windows cmd
    echo $LASTEXITCODE  # Windows PowerShell

Getting help
============

If you encounter issues with the CLI:

- Use ``ican --help`` for usage information
- Check the `Issue Tracker <https://github.com/pycalendar/icalendar-anonymizer/issues>`_
- Open a new issue with:
  - Your command
  - Error message
  - Operating system
  - Python version (``python --version``)
  - Package version (``ican --version``)

Integration examples
====================

Git pre-commit hook
--------------------

Automatically anonymize calendars before committing:

.. code-block:: shell

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

.. code-block:: shell

    # Crontab entry: Anonymize daily at 2 AM
    0 2 * * * /usr/bin/ican /path/to/calendar.ics -o /path/to/anon.ics

See also
========

- :doc:`python-api` - Python API for programmatic usage
- :doc:`../installation` - Installation instructions
- :doc:`../api/index` - Complete API reference
- :doc:`../contributing` - Development guide
