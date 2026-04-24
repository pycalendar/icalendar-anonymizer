.. SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
.. SPDX-License-Identifier: AGPL-3.0-or-later

=====================================================
Publish an anonymized calendar with Open Web Calendar
=====================================================

Share your calendar publicly, but hide the details you don't want people to see.

You'll use three tools:

- **Google Calendar** — where your events live
- **icalendar-anonymizer** — removes the fields you choose
- **Open Web Calendar (OWC)** — renders the result as a web page

Step 1: Create a Google Calendar
================================

Sign in at `Google Calendar <https://calendar.google.com/>`_.

In the left sidebar, next to **Other calendars**, click **+** → **Create new calendar**. Name it ``Demo Calendar``, pick your timezone, click **Create calendar**.

Add a few events. Mix weekly, daily, and one-off. Give them titles, descriptions, locations — the tutorial uses them to show the difference between what stays and what gets stripped.

.. image:: /_static/tutorials/google-calendar-demo.png
   :alt: Google Calendar showing a month of events including Team Standup, Gym, Lunch with Steve, and 1:1 with Sashank
   :width: 100%

Step 2: Get the ICS URL
=======================

Google Calendar exposes each calendar as an ICS feed.

1. Gear icon (top right) → **Settings**.
2. Left sidebar → **Settings for my calendars** → your **Demo Calendar**.
3. Scroll to **Integrate calendar**.
4. Copy the **Secret address in iCal format**.

.. image:: /_static/tutorials/google-calendar-ics.png
   :alt: The Integrate calendar section with the Secret address in iCal format field
   :width: 100%

The URL looks like this::

    https://calendar.google.com/calendar/ical/{email}/private-{secret-token}/basic.ics

.. warning::
    Treat this URL like a password. Anyone who has it can read your full calendar. Step 3 wraps it in an encrypted link so you can share publicly without leaking the original.

Step 3: Choose what to share online
===================================

Open `icalendar-anonymizer.com <https://icalendar-anonymizer.com/>`_ and click the **Fetch URL** tab. Paste the secret URL.

Expand **Advanced Options**.

.. image:: /_static/tutorials/anonymizer-fetch-options.png
   :alt: The Fetch URL tab with Advanced Options expanded, showing dropdowns for each field
   :width: 100%

Each field has four modes:

- **Keep original** — pass through unchanged
- **Remove** — strip the field entirely
- **Randomize** — replace with a deterministic hash
- **Replace with placeholder** — replace with fixed text like ``[Redacted]``

The defaults keep titles (``SUMMARY: Keep original``) and remove everything else personal — descriptions, locations, attendees, organizers, categories, comments. ``UID`` is randomized so recurring events stay grouped but the original identifier doesn't leak.

Check **Generate shareable link** and pick **Live proxy (Fernet)**. This encrypts the original URL and your field choices into an opaque token. Anyone with the resulting link gets your anonymized calendar, but can't decrypt it back to the Google URL or see the fields you stripped.

Click **Fetch & Anonymize**. Copy the link::

    https://icalendar-anonymizer.com/fernet/{encrypted-token}

It's live — every time someone opens it, icalendar-anonymizer refetches your calendar and applies the same field choices. Edits in Google Calendar show up within minutes.

Step 4: Embed with Open Web Calendar
====================================

OWC turns an ICS URL into a month/week/day view. Pass your Fernet URL through its ``url`` parameter::

    https://open-web-calendar.hosted.quelltext.eu/calendar.html?url={fernet-url}

URL-encode the Fernet URL first. It contains ``&`` and ``?``, which OWC would otherwise read as its own parameters. Most online URL encoders handle this in one click.

.. image:: /_static/tutorials/owc-rendered-demo.png
   :alt: Open Web Calendar rendering the anonymized Demo Calendar with only event titles visible
   :width: 100%

Compare this with the Step 1 screenshot. Event titles and times match. Descriptions, locations, and everything else are gone.

To embed on a web page, wrap the URL in an iframe::

    <iframe src="https://open-web-calendar.hosted.quelltext.eu/calendar.html?url={fernet-url}"
            width="100%"
            height="600"
            frameborder="0">
    </iframe>

Troubleshooting
===============

**OWC shows an empty calendar.** Open your Fernet URL in the browser. If the response doesn't start with ``BEGIN:VCALENDAR``, the Google URL is wrong or Google's ICS feed is slow to pick up new events (can take 10–30 minutes).

**Fields you expected to hide are still visible.** The Fernet token captures your field choices at the moment you generated it. Changing the dropdowns later doesn't update an existing token — generate a new link.

**Query parameters aren't being applied.** Make sure you URL-encoded the Fernet URL before passing it to OWC.

Related topics
==============

- :doc:`../usage/web-service` — Full reference for the ``/fetch`` and ``/fernet-generate`` endpoints
