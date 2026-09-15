.. SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
.. SPDX-License-Identifier: AGPL-3.0-or-later

=============
Configuration
=============

.. automodule:: icalendar_anonymizer._config
   :members:
   :undoc-members:
   :show-inheritance:

Usage
=====

.. code-block:: python

    from icalendar_anonymizer import AnonymizeMode, CONFIGURABLE_FIELDS

    print(sorted(CONFIGURABLE_FIELDS))
    # ['ATTENDEE', 'CATEGORIES', 'COMMENT', 'CONTACT', 'DESCRIPTION',
    #  'LOCATION', 'ORGANIZER', 'RESOURCES', 'SUMMARY', 'UID']

    print(list(AnonymizeMode))
    # [<AnonymizeMode.KEEP: 'keep'>, <AnonymizeMode.REMOVE: 'remove'>,
    #  <AnonymizeMode.RANDOMIZE: 'randomize'>, <AnonymizeMode.REPLACE: 'replace'>]

``AnonymizeMode`` is a ``StrEnum``, so its members compare equal to the plain strings ``field_modes`` already accepts: ``AnonymizeMode.KEEP == "keep"``. See :doc:`python-api` for ``field_modes`` in context.
