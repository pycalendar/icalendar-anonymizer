.. SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
.. SPDX-License-Identifier: AGPL-3.0-or-later

======
Design
======

Why default-deny instead of a denylist
======================================

:func:`~icalendar_anonymizer._properties.should_preserve_property` only preserves a property if it's explicitly listed in ``PRESERVED_PROPERTIES``. Anything else, including unrecognized standard properties and every ``X-`` extension, is anonymized.

The alternative, a denylist of known-sensitive properties, fails open: a calendar client's own custom ``X-`` property (Outlook's, or a vendor's) could carry a name, an address, or a note, and a denylist has no way to know that in advance. Default-deny means an unknown property gets treated as personal data until someone adds it to the preserved set on purpose, which is the direction a privacy tool should fail in.

This is also why ``ATTACH``, ``URL``, and ``GEO`` are anonymized despite looking technical: an attachment or URL can carry personal data in its path or query string, and ``GEO`` coordinates can reveal a home or work address. They read as structural, but the same default-deny reasoning applies to them.

Why hashing preserves structure instead of replacing wholesale
==============================================================

:func:`~icalendar_anonymizer._hash.hash_text` hashes each word in a value independently and rejoins them with spaces, rather than replacing the whole value with one opaque token. A three-word summary anonymizes to three hashed words. This exists because bug reports often depend on structural properties of the data that the anonymizer has no way to know are safe or unsafe in advance: whether a parser chokes on a particular word count, a particular string length, or a particular character class. Preserving structure while destroying content keeps a bug reproducible without knowing ahead of time which structural detail the bug depends on.

The same reasoning extends to :func:`~icalendar_anonymizer._hash.hash_email`, which keeps the ``local@domain`` shape (with the domain's TLD replaced by ``.local``, per :rfc:`6761`) instead of returning a single hash, and to :func:`~icalendar_anonymizer._hash.hash_uid`, which maps each distinct input UID to the same output UID within one anonymization run, so recurring events that share a UID across multiple ``VEVENT``\ s still share one after anonymization.

Why JSCalendar gets a native walker instead of round-tripping through iCalendar
===============================================================================

:func:`~icalendar_anonymizer.anonymize_jscal` walks a JSCalendar document's own JSON structure directly, rather than converting it to an iCalendar :class:`~icalendar.cal.Calendar` and reusing :func:`~icalendar_anonymizer.anonymize`. JSCalendar's property model differs from iCalendar's in ways a lossless round trip can't paper over: participants are one map covering both organizers and attendees instead of separate ``ATTENDEE``/``ORGANIZER`` properties, and locations are a map rather than a single value. Converting to iCalendar first and back would need to preserve every JSCalendar-specific shape through that round trip, which duplicates the problem the native walker already solves directly.

jCal doesn't have this problem: it's a lossless JSON encoding of the same property model as iCalendar, so :func:`~icalendar_anonymizer.anonymize_jcal` reuses :func:`~icalendar_anonymizer.anonymize` unchanged, feeding jCal's property list through the same code path a parsed iCalendar file would use.

Why DNS is resolved, validated, and pinned on every redirect hop
================================================================

:func:`icalendar_anonymizer.webapp._ssrf.fetch_with_pinned_redirects` resolves a hostname, validates every address it resolves to, and connects to that exact validated address, rather than validating a hostname and letting the underlying HTTP client resolve DNS again when it actually connects. Between those two steps, an attacker's own DNS record can change: a public address at validation time, and an internal one a moment later. Pinning the connection to the address that was actually checked closes that gap, and the whole sequence repeats independently on every redirect hop, since each hop is a new opportunity for the same rebinding to happen again.
