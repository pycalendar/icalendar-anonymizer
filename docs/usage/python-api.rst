.. SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
.. SPDX-License-Identifier: AGPL-3.0-or-later

==========
Python API
==========

Basic Usage
===========

Use :py:func:`icalendar_anonymizer.anonymize` to anonymize a :py:class:`icalendar.Calendar` object:

.. code-block:: python

    from icalendar import Calendar
    from icalendar_anonymizer import anonymize

    # Load your calendar
    with open('calendar.ics', 'rb') as f:
        cal = Calendar.from_ical(f.read())

    # Anonymize it
    anonymized_cal = anonymize(cal)

    # Save the result
    with open('anonymized.ics', 'wb') as f:
        f.write(anonymized_cal.to_ical())

Function Signature
==================

.. autofunction:: icalendar_anonymizer.anonymize

Using Custom Salt
=================

Provide your own salt for reproducible output:

.. code-block:: python

    # Anonymize with custom salt
    anonymized_cal = anonymize(cal, salt=b"my-secret-salt-12345678901234567890")

    # Same input + same salt = same output
    anonymized_again = anonymize(cal, salt=b"my-secret-salt-12345678901234567890")
    assert anonymized_cal.to_ical() == anonymized_again.to_ical()

**Use cases:**

- Reproducible output across runs
- Testing and debugging
- Consistent hashing when sharing calendars

.. warning::
    Keep your custom salt secret if you need to prevent others from testing potential matches against the hashed values.

Configurable Field Anonymization
=================================

Control how each field is anonymized using the ``field_modes`` parameter. Four modes available:

**keep**
    Preserve the original value unchanged

**remove**
    Strip the property entirely from the output

**randomize** (default)
    Hash to a deterministic random value

**replace**
    Replace with a fixed placeholder text

.. code-block:: python

    # Keep SUMMARY, remove LOCATION, replace DESCRIPTION
    anonymized_cal = anonymize(cal, field_modes={
        "SUMMARY": "keep",
        "LOCATION": "remove",
        "DESCRIPTION": "replace"
    })

**Configurable fields (10 total):**

- Text: ``SUMMARY``, ``DESCRIPTION``, ``LOCATION``, ``COMMENT``, ``CONTACT``, ``RESOURCES``, ``CATEGORIES``
- Email: ``ATTENDEE``, ``ORGANIZER``
- ID: ``UID``

.. code-block:: python

    # Example: Preserve summaries, remove locations, randomize everything else
    anonymized_cal = anonymize(cal, field_modes={
        "SUMMARY": "keep",
        "LOCATION": "remove"
    })

**Important notes:**

- Field names are case-insensitive: ``{"summary": "keep"}`` and ``{"SUMMARY": "keep"}`` are equivalent
- Mode values are case-insensitive: ``"Keep"``, ``"KEEP"``, and ``"keep"`` all work
- Only configured fields are affected - others use the default randomize behavior
- Applies recursively to all components (VEVENT, VTODO, VJOURNAL, VALARM)
- **UID constraint**: Cannot use ``remove`` mode (would break recurring events)

Replace Mode Placeholders
-------------------------

When using ``replace`` mode, these placeholders are used:

.. code-block:: python

    SUMMARY: "[Redacted]"
    DESCRIPTION: "[Content removed]"
    LOCATION: "[Location removed]"
    COMMENT: "[Comment removed]"
    CONTACT: "[Contact removed]"
    RESOURCES: "[Resources removed]"
    CATEGORIES: "REDACTED"
    ATTENDEE: "mailto:redacted@example.local"
    ORGANIZER: "mailto:redacted@example.local"
    UID: "redacted-N@anonymous.local"  # N = counter for uniqueness

.. code-block:: python

    # Example: Replace sensitive fields with placeholders
    anonymized_cal = anonymize(cal, field_modes={
        "DESCRIPTION": "replace",
        "LOCATION": "replace",
        "ATTENDEE": "replace"
    })

Preserving Additional Properties (Legacy)
==========================================

The ``preserve`` parameter is still supported for backward compatibility:

.. code-block:: python

    # Legacy method - still works
    anonymized_cal = anonymize(cal, preserve={"CATEGORIES", "LOCATION"})

    # Equivalent using field_modes
    anonymized_cal = anonymize(cal, field_modes={
        "CATEGORIES": "keep",
        "LOCATION": "keep"
    })

**Mutual exclusion:** Cannot specify both ``preserve`` and ``field_modes`` in the same call.

.. code-block:: python

    # ❌ Error: cannot use both
    anonymized_cal = anonymize(cal,
        preserve={"SUMMARY"},
        field_modes={"LOCATION": "keep"}
    )

**Important notes:**

- Property names are case-insensitive: ``{"summary"}`` and ``{"SUMMARY"}`` are equivalent
- The ``preserve`` set is **additive** - it adds to the default preserved properties, not replaces them
- Applies recursively to all components (VEVENT, VTODO, VJOURNAL, VALARM)
- Use this when you've confirmed the properties contain no sensitive data

.. code-block:: python

    # Example: Preserving categories for bug reproduction
    # After confirming categories contain no personal data
    anonymized_cal = anonymize(cal, preserve={"CATEGORIES"})

Property Handling Reference
===========================

This table shows which properties are anonymized vs. preserved by default.

Preserved Properties (Technical)
--------------------------------

These properties are preserved to enable bug reproduction:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Property
     - Notes
   * - **Datetime Properties**
     -
   * - DTSTART
     - Start date/time - critical for scheduling bugs
   * - DTEND
     - End date/time
   * - DUE
     - Due date for TODOs
   * - DURATION
     - Event duration
   * - DTSTAMP
     - Timestamp
   * - CREATED
     - Creation timestamp
   * - LAST-MODIFIED
     - Last modification timestamp
   * - COMPLETED
     - Completion timestamp for TODOs
   * - **Recurrence Properties**
     -
   * - RRULE
     - Recurrence rule - critical for recurrence bugs
   * - RDATE
     - Recurrence dates
   * - EXDATE
     - Exception dates
   * - **Metadata Properties**
     -
   * - SEQUENCE
     - Modification sequence number
   * - STATUS
     - Event status (CONFIRMED, TENTATIVE, CANCELLED)
   * - TRANSP
     - Transparency (OPAQUE, TRANSPARENT)
   * - CLASS
     - Classification (PUBLIC, PRIVATE, CONFIDENTIAL)
   * - PRIORITY
     - Priority level (0-9)
   * - PERCENT-COMPLETE
     - Completion percentage for TODOs
   * - **Calendar-Level Properties**
     -
   * - VERSION
     - iCalendar version
   * - PRODID
     - Product identifier
   * - CALSCALE
     - Calendar scale
   * - METHOD
     - Calendar method (REQUEST, REPLY, etc.)
   * - **Components**
     -
   * - VTIMEZONE
     - Complete timezone definitions preserved
   * - Component types
     - VEVENT, VTODO, VJOURNAL, VALARM types preserved

Anonymized Properties (Personal Data)
-------------------------------------

These properties contain personal data and are hashed:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Property
     - Anonymization Method
   * - **Text Fields**
     -
   * - SUMMARY
     - Hashed with word count preservation
   * - DESCRIPTION
     - Hashed with word count preservation
   * - LOCATION
     - Hashed with word count preservation
   * - COMMENT
     - Hashed with word count preservation
   * - CONTACT
     - Hashed with word count preservation
   * - CATEGORIES
     - Each category hashed individually (list property)
   * - RESOURCES
     - Each resource hashed individually (list property)
   * - **Person Identifiers**
     -
   * - ATTENDEE
     - CN parameter hashed, mailto: preserved for structure
   * - ORGANIZER
     - CN parameter hashed, mailto: preserved for structure
   * - **Unique Identifiers**
     -
   * - UID
     - Hashed but uniqueness preserved across calendar
   * - **Unknown Properties**
     -
   * - Any other property
     - Anonymized by default (secure default-deny model)

Special Handling Examples
=========================

ATTENDEE and ORGANIZER
----------------------

The CN (Common Name) parameter is hashed while preserving the mailto: structure:

.. code-block:: python

    # Original
    ATTENDEE;CN=John Doe:mailto:john@example.com

    # Anonymized
    ATTENDEE;CN=a1b2c3d4:mailto:john@example.com

UID Uniqueness
--------------

UIDs are hashed but uniqueness is maintained across the calendar:

.. code-block:: python

    # Original calendar with recurring event
    Event 1: UID=abc123
    Event 2: UID=abc123  # Same event, recurrence exception
    Event 3: UID=xyz789

    # Anonymized calendar
    Event 1: UID=hash-of-abc123
    Event 2: UID=hash-of-abc123  # Same hash - uniqueness preserved!
    Event 3: UID=hash-of-xyz789

Word Count Preservation
-----------------------

Text properties preserve word count to maintain structure:

.. code-block:: python

    # Original
    SUMMARY:Team meeting about Q4 planning

    # Anonymized (6 words → 6 hashes)
    SUMMARY:a1b2c3 d4e5f6 g7h8i9 j0k1l2 m3n4o5 p6q7r8

List Properties
---------------

CATEGORIES and RESOURCES are list properties - each value is hashed individually:

.. code-block:: python

    # Original
    CATEGORIES:Work,Meeting,Important

    # Anonymized
    CATEGORIES:hash1,hash2,hash3

Working with Different Component Types
======================================

The anonymization works recursively on all component types:

Events (VEVENT)
---------------

.. code-block:: python

    from icalendar import Calendar, Event
    from icalendar_anonymizer import anonymize
    from datetime import datetime

    # Create an event
    event = Event()
    event.add('summary', 'Project meeting')
    event.add('dtstart', datetime(2025, 1, 15, 10, 0))
    event.add('dtend', datetime(2025, 1, 15, 11, 0))

    cal = Calendar()
    cal.add_component(event)

    # Anonymize
    anonymized_cal = anonymize(cal)

TODOs (VTODO)
-------------

.. code-block:: python

    from icalendar import Calendar, Todo
    from icalendar_anonymizer import anonymize
    from datetime import datetime

    # Create a TODO
    todo = Todo()
    todo.add('summary', 'Fix bug in authentication')
    todo.add('due', datetime(2025, 1, 20))
    todo.add('priority', 1)

    cal = Calendar()
    cal.add_component(todo)

    # Anonymize (PRIORITY preserved, SUMMARY anonymized)
    anonymized_cal = anonymize(cal)

Journals (VJOURNAL)
-------------------

.. code-block:: python

    from icalendar import Calendar, Journal
    from icalendar_anonymizer import anonymize
    from datetime import datetime

    # Create a journal entry
    journal = Journal()
    journal.add('summary', 'Daily standup notes')
    journal.add('description', 'Discussed blockers and next steps')
    journal.add('dtstart', datetime(2025, 1, 15))

    cal = Calendar()
    cal.add_component(journal)

    # Anonymize
    anonymized_cal = anonymize(cal)

Alarms (VALARM)
---------------

Alarms within events are also processed:

.. code-block:: python

    from icalendar import Calendar, Event, Alarm
    from icalendar_anonymizer import anonymize
    from datetime import timedelta

    # Event with alarm
    event = Event()
    event.add('summary', 'Important meeting')

    alarm = Alarm()
    alarm.add('description', 'Meeting reminder')  # Will be anonymized
    alarm.add('trigger', timedelta(minutes=-15))  # Preserved

    event.add_component(alarm)
    cal = Calendar()
    cal.add_component(event)

    # Anonymize
    anonymized_cal = anonymize(cal)

Supported Components
====================

.. note::
   This library supports standard iCalendar components: VEVENT, VTODO, VJOURNAL, and VALARM.
   Components from other standards or extensions may not be fully supported.

Error Handling
==============

The function performs strict type checking:

TypeError for Invalid Calendar
------------------------------

.. code-block:: python

    from icalendar_anonymizer import anonymize

    # Wrong: passing a string instead of Calendar
    try:
        anonymized = anonymize("BEGIN:VCALENDAR...")
    except TypeError as e:
        print(e)  # "cal must be a Calendar instance"

TypeError for Invalid Salt
--------------------------

.. code-block:: python

    # Wrong: passing a string instead of bytes
    try:
        anonymized = anonymize(cal, salt="my-salt")
    except TypeError as e:
        print(e)  # "salt must be bytes or None"

TypeError for Invalid Preserve
------------------------------

.. code-block:: python

    # Wrong: passing a list instead of set
    try:
        anonymized = anonymize(cal, preserve=["SUMMARY", "DESCRIPTION"])
    except TypeError as e:
        print(e)  # "preserve must be a set or None"

    # Correct: use a set
    anonymized = anonymize(cal, preserve={"SUMMARY", "DESCRIPTION"})

TypeError/ValueError for Invalid field_modes
--------------------------------------------

.. code-block:: python

    # Wrong: passing a list instead of dict
    try:
        anonymized = anonymize(cal, field_modes=["SUMMARY"])
    except TypeError as e:
        print(e)  # "field_modes must be dict or None"

    # Wrong: invalid field name
    try:
        anonymized = anonymize(cal, field_modes={"INVALID": "keep"})
    except ValueError as e:
        print(e)  # "Unknown field 'INVALID'. Valid: ..."

    # Wrong: invalid mode
    try:
        anonymized = anonymize(cal, field_modes={"SUMMARY": "invalid"})
    except ValueError as e:
        print(e)  # "Invalid mode 'invalid'. Valid: ..."

    # Wrong: trying to remove UID
    try:
        anonymized = anonymize(cal, field_modes={"UID": "remove"})
    except ValueError as e:
        print(e)  # "UID cannot be removed (would break recurring events)"

    # Correct: valid field_modes
    anonymized = anonymize(cal, field_modes={"SUMMARY": "keep"})

Best Practices
==============

1. **Load from Files**

   Always load calendars using the icalendar library:

   .. code-block:: python

       from icalendar import Calendar

       with open('calendar.ics', 'rb') as f:
           cal = Calendar.from_ical(f.read())

2. **Verify Before Preserving**

   Only use ``preserve`` after confirming properties contain no sensitive data:

   .. code-block:: python

       # ❌ Don't blindly preserve
       anonymized = anonymize(cal, preserve={"SUMMARY"})

       # ✅ Verify first, then preserve if safe
       # (After manual inspection confirms SUMMARY has no personal data)
       anonymized = anonymize(cal, preserve={"CATEGORIES"})

3. **Use Custom Salt for Reproducibility**

   If you need consistent output across runs:

   .. code-block:: python

       SALT = b"my-project-salt-" + b"0" * 16  # 32 bytes total
       anonymized = anonymize(cal, salt=SALT)

4. **Don't Modify Original**

   The function returns a new Calendar object - the original is not modified:

   .. code-block:: python

       anonymized = anonymize(cal)
       # cal is unchanged
       # anonymized is the new anonymized calendar

5. **Save with Binary Mode**

   Always save iCalendar files in binary mode:

   .. code-block:: python

       with open('anonymized.ics', 'wb') as f:  # Note: 'wb' not 'w'
           f.write(anonymized_cal.to_ical())

Complete Example
================

Here's a complete example putting it all together:

.. code-block:: python

    from icalendar import Calendar, Event
    from icalendar_anonymizer import anonymize
    from datetime import datetime

    # Create a calendar
    cal = Calendar()
    cal.add('prodid', '-//My App//My Calendar//EN')
    cal.add('version', '2.0')

    # Add an event with personal data
    event = Event()
    event.add('summary', 'Dentist appointment with Dr. Smith')
    event.add('description', 'Regular checkup at 123 Main St')
    event.add('location', 'Downtown Dental Clinic')
    event.add('dtstart', datetime(2025, 1, 15, 14, 0))
    event.add('dtend', datetime(2025, 1, 15, 15, 0))
    event.add('status', 'CONFIRMED')

    attendee = 'mailto:patient@example.com'
    event.add('attendee', attendee, parameters={'CN': 'Jane Doe'})

    cal.add_component(event)

    # Anonymize with custom salt
    SALT = b"my-secret-salt-for-testing-12345"
    anonymized_cal = anonymize(cal, salt=SALT)

    # Save the anonymized calendar
    with open('anonymized.ics', 'wb') as f:
        f.write(anonymized_cal.to_ical())

    print("Anonymization complete!")
    print(f"Original UID: {event['uid']}")
    print(f"Anonymized UID: {list(anonymized_cal.walk('VEVENT'))[0]['uid']}")

See Also
========

- :doc:`../api/index` - Complete API reference
- :doc:`../installation` - Installation instructions
- :doc:`../contributing` - Development guide
