.. SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
.. SPDX-License-Identifier: AGPL-3.0-or-later

=====================================================
Publish an anonymized calendar with Open Web Calendar
=====================================================

This tutorial shows you how to publish a public calendar that displays only event titles, while keeping the rest of your schedule private.

You'll chain three tools:

1. **Google Calendar** provides a private ICS feed.
2. **icalendar-anonymizer** strips personal data from the feed.
3. **Open Web Calendar (OWC)** renders the anonymized feed as a public web page.

The result is a live-updating public calendar that hides attendees, locations, descriptions, and categories but keeps dates, times, and event titles visible.

Before you start
================

You need:

- A Google Calendar account (or any calendar source that exposes an ICS URL)
- A web browser

You don't need:

- A server
- A developer account
- To install anything

Step 1: Get your Google Calendar ICS URL
========================================

1. Open `Google Calendar <https://calendar.google.com/>`_.
2. Select the **gear icon** in the top right, then select **Settings**.
3. In the left sidebar, under **Settings for my calendars**, select the calendar you want to publish.
4. Scroll to the **Integrate calendar** section.
5. Copy the **Secret address in iCal format**.

.. image:: /_static/tutorials/google-calendar-ics.png
   :alt: Google Calendar's "Integrate calendar" section showing the Secret address in iCal format field
   :width: 100%

The URL looks like this::

    https://calendar.google.com/calendar/ical/{email}/private-{secret-token}/basic.ics

.. warning::
    Keep this URL private. Anyone who has it can read your full calendar. The next step anonymizes the feed before it's exposed publicly.

Step 2: Wrap the URL with icalendar-anonymizer
==============================================

icalendar-anonymizer fetches the Google feed, strips personal data, and returns an anonymized ICS file. Use the ``/fetch`` endpoint on `icalendar-anonymizer.com <https://icalendar-anonymizer.com/>`_.

The basic pattern is::

    https://icalendar-anonymizer.com/fetch?url=YOUR_GOOGLE_URL

URL-encode your Google URL before you add it. Most browsers and online encoders handle this.

Configure which fields to keep with query parameters. To keep event titles and remove everything else, add ``summary=keep``::

    https://icalendar-anonymizer.com/fetch?url=YOUR_GOOGLE_URL&summary=keep

Supported query parameters: ``summary``, ``description``, ``location``, ``comment``, ``contact``, ``resources``, ``categories``, ``attendee``, ``organizer``, ``uid``. Each accepts ``keep``, ``remove``, ``randomize``, or ``replace``.

The defaults match the web interface: ``summary=keep``, all personal fields set to ``remove``, ``uid=randomize``.

.. image:: /_static/tutorials/anonymizer-fetch-options.png
   :alt: The Fetch URL tab on icalendar-anonymizer.com with Advanced Options expanded, showing per-field dropdowns
   :width: 100%

You can also configure these options visually on the `Fetch URL tab <https://icalendar-anonymizer.com/>`_, then copy the resulting URL.

Test the wrapped URL by opening it in your browser. You should see an anonymized ICS file.

Step 3: Pass the wrapped URL to Open Web Calendar
=================================================

Open Web Calendar accepts an ICS URL through its ``url`` query parameter::

    https://open-web-calendar.hosted.quelltext.eu/calendar.html?url=WRAPPED_URL

Replace ``WRAPPED_URL`` with the URL from Step 2, URL-encoded a second time. The wrapped URL already contains an encoded Google URL inside it; encoding it again escapes the ``&`` and ``?`` characters that OWC would otherwise treat as its own parameters. The final URL contains double-encoded characters like ``%253A`` (which is ``%3A`` encoded again).

A complete example::

    https://open-web-calendar.hosted.quelltext.eu/calendar.html?url=https%3A%2F%2Ficalendar-anonymizer.com%2Ffetch%3Furl%3Dhttps%253A%252F%252Fcalendar.google.com%252Fcalendar%252Fical%252F...

Open the URL. OWC renders a public calendar that shows only the event titles from your Google Calendar.

.. image:: /_static/tutorials/owc-rendered.png
   :alt: Open Web Calendar rendering a monthly view with only event titles visible
   :width: 100%

Step 4: Embed the calendar on your website
==========================================

To embed the calendar on any web page, use an iframe::

    <iframe src="https://open-web-calendar.hosted.quelltext.eu/calendar.html?url=WRAPPED_URL"
            width="100%"
            height="600"
            frameborder="0">
    </iframe>

Replace ``WRAPPED_URL`` with your wrapped URL. The calendar re-fetches the anonymized feed on every page load, so updates in Google Calendar appear in the embedded view without any manual refresh.

What gets published
===================

With the default configuration, visitors to your public calendar see:

- Event dates and times
- Event titles
- Recurrence (weekly standups, monthly reviews, and so on)
- Your timezone

Visitors don't see:

- Descriptions or notes
- Locations
- Attendees, organizers, or any email addresses
- Comments, categories, or custom fields

To hide titles too, change ``summary=keep`` to ``summary=remove`` in the wrapped URL. OWC will render empty blocks at your busy times, revealing only availability.

Troubleshooting
===============

**OWC shows an empty calendar.** Open your wrapped URL directly in the browser. If it doesn't return valid ICS, the issue is with icalendar-anonymizer or the source URL. Check that your Google ICS URL is correct and reachable by the icalendar-anonymizer service. Keep the secret URL private; don't share it publicly.

**The calendar doesn't update.** OWC fetches fresh data on every page load, but your browser may cache the page itself. Force-refresh with :kbd:`Ctrl+F5` or :kbd:`Cmd+Shift+R`.

**Query parameters aren't applied.** Make sure you URL-encoded the inner URL. Unencoded ``&`` characters break the chain.

Related topics
==============

- :doc:`../usage/web-service` — Full reference for the ``/fetch`` endpoint
