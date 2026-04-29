.. SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
.. SPDX-License-Identifier: AGPL-3.0-or-later

========
Examples
========

This chapter provides example workflows for common use cases.

Anonymize a Google Calendar export for a bug report
===================================================

From your Google Calendar, export it to an iCalendar file via :menuselection:`Settings --> Import & export --> Export`, then click the :guilabel:`Export` button.
Before attaching it to a bug report, run the exported file through the anonymizer with the following command.

.. code-block:: shell

    ican calendar.ics -o anonymized.ics

The output preserves dates, recurrence, and timezone data while stripping names, emails, and personal text.
Attach :file:`anonymized.ics` to the bug report.

To keep event titles visible, use the ``--summary keep`` flag:

.. code-block:: shell

    ican --summary keep calendar.ics -o anonymized.ics

.. _reproducible-test-data-with-custom-salts:

Reproducible test data with custom salts
========================================

By default, each run generates a fresh random salt, so the same input produces different output each time.
For tests that assert specific values, pass a fixed salt:

.. code-block:: python

    from icalendar import Calendar
    from icalendar_anonymizer import anonymize

    with open("calendar.ics", "rb") as f:
        cal = Calendar.from_ical(f.read())

    # Same salt = same hashed output every time
    anonymized = anonymize(cal, salt=b"test-fixture-salt-0123456789abcdef")

    with open("tests/fixtures/anonymized.ics", "wb") as f:
        f.write(anonymized.to_ical())

Pin the salt in version control alongside the fixture.
Changing the salt invalidates the fixture.

Batch process multiple calendar files
=====================================

Anonymize every ``.ics`` file in a directory, writing results to a sibling directory:

.. code-block:: python

    from pathlib import Path
    from icalendar import Calendar
    from icalendar_anonymizer import anonymize

    source = Path("calendars")
    target = Path("anonymized")
    target.mkdir(exist_ok=True)

    for ics_path in source.glob("*.ics"):
        cal = Calendar.from_ical(ics_path.read_bytes())
        anonymized = anonymize(cal)
        (target / ics_path.name).write_bytes(anonymized.to_ical())

For a shell-only pipeline:

.. code-block:: shell

    for f in calendars/*.ics; do
        ican "$f" -o "anonymized/$(basename "$f")"
    done

Debug recurrence and timezone issues
====================================

When reporting a bug in recurrence expansion or timezone handling, the technical properties (``RRULE``, ``RDATE``, ``EXDATE``, ``DTSTART``, ``TZID``, and ``VTIMEZONE``) are exactly what maintainers need.
The anonymizer preserves all of these by default.

If the bug requires a specific ``SUMMARY`` or ``CATEGORIES`` value to reproduce (for example, a parser triggered by a specific string), use ``--summary keep`` or ``--categories keep`` and confirm the preserved fields don't contain personal data before sharing.

To get reproducible hashed ``UID`` values so maintainers can match events across runs, use the Python API with a fixed salt as described in the above section, :ref:`reproducible-test-data-with-custom-salts`.
