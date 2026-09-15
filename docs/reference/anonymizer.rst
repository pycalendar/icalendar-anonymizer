.. SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
.. SPDX-License-Identifier: AGPL-3.0-or-later

========================
anonymizer - Core Module
========================

.. automodule:: icalendar_anonymizer.anonymizer
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource

Usage Example
=============

.. code-block:: python

    from icalendar import Calendar
    from icalendar_anonymizer import anonymize

    with open('calendar.ics', 'rb') as f:
        cal = Calendar.from_ical(f.read())

    anonymized_cal = anonymize(cal)

    with open('anonymized.ics', 'wb') as f:
        f.write(anonymized_cal.to_ical())
