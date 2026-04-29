.. SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
.. SPDX-License-Identifier: AGPL-3.0-or-later

=====================================================
Publish an anonymized calendar with Open Web Calendar
=====================================================

This tutorial will guide you to share your calendar publicly, but hide the details you don't want people to see.

You'll use three tools:

-   :program:`Google Calendar` stores your calendar data.
-   :program:`icalendar-anonymizer` removes fields you don't want to share.
-   :program:`Open Web Calendar (OWC)` renders the result as a web page.

Step 1: Create a Google Calendar
================================

Sign in at `Google Calendar <https://calendar.google.com/>`_.

In the left sidebar, next to :guilabel:`Other calendars`, select :menuselection:`+ --> Create new calendar`.
Name it ``Demo Calendar``, pick your time zone, and click the :guilabel:`Create calendar` button.

Add a few events.
Mix weekly and daily recurring events, and one-time events.
Give them titles, descriptions, locations, and other useful data to make the before-and-after comparison easier to spot.

Step 2: Get the calendar's URL
==============================

Google Calendar assigns every calendar a feed as a URL.
To get this URL, take the following steps.

1.  Click on the gear icon in the top right, :menuselection:`Settings menu`.
2.  In the left sidebar, below :guilabel:`Settings for my calendars`, click the name of your calendar :menuselection:`Demo Calendar`.
3.  In the left sidebar, click :menuselection:`Integrate calendar` to scroll that section into view.
4.  Click the :guilabel:`Copy to clipboard` icon to the right of :guilabel:`Secret address in iCal format` to copy the URL to your computer's clipboard.

The URL looks like :samp:`https://calendar.google.com/calendar/ical/{email}/private-{secret-token}/basic.ics`, but with personal values for ``email`` and ``secret-token``.

.. warning::
    Treat this URL like a password.
    Anyone who has it can read your full calendar.
    The next step wraps it in an encrypted link, so you can share that publicly without leaking the original data.

Step 3: Choose what to share online
===================================

Open `icalendar-anonymizer.com <https://icalendar-anonymizer.com/>`_ and click the :guilabel:`Fetch URL` tab.
Click in the input field with the placeholder text :guilabel:`https://example.com/calendar.ics`, and paste the secret URL.

Click :guilabel:`Advanced Options` to reveal fields that you can manage.

Each field has four options, with its default option selected.

-   :guilabel:`Keep original` passes through the field value unchanged.
-   :guilabel:`Remove` removes the field.
-   :guilabel:`Randomize` replaces the field value with a deterministic hash.
-   :guilabel:`Replace with placeholder` replaces the field value with fixed text, such as ``[Redacted]``.

The default selections keep titles, such as ``SUMMARY: Keep original``, and remove all other personal data, including descriptions, locations, attendees, organizers, categories, and comments.
:guilabel:`UID` is randomized by default so recurring events stay grouped, but the original identifier doesn't leak.

Check the box labeled :guilabel:`Generate shareable link`, and select :guilabel:`Live proxy`.
The original URL and your field choices get encrypted into the link using Fernet encryption.
For convenience, this tutorial calls this encrypted link a "Fernet URL".
Anyone using it gets your anonymized calendar, and nobody can read the Google URL out of it.

Click the button :guilabel:`Fetch & Anonymize`.
The Fernet URL appears.
Click the button :guilabel:`Copy` to copy the link to your computer's clipboard.

The Fernet URL will look like :samp:`https://icalendar-anonymizer.com/fernet/{encrypted-token}`, but with your actual encrypted token.

This Fernet URL is a live feed.
Every visit refetches your calendar anew.
Edits in Google Calendar show up within minutes.

Step 4: Embed with Open Web Calendar
====================================

OWC turns an iCalendar URL into a month, week, or day view.

First, URL-encode your Fernet URL.
It may contain ``&`` and ``?``, which OWC would otherwise read as its own parameters.
Most online URL encoders handle this in one click.

Then construct your OWC URL with :samp:`https://open-web-calendar.hosted.quelltext.eu/calendar.html?url={fernet-url}`, replacing ``fernet-url`` with your URL-encoded Fernet URL.

Paste the OWC URL into a web browser's address bar to visit the site.
You should see the same month and titles, but everything else removed.

To embed on a web page, wrap the OWC URL in an HTML iframe.

..  code-block:: html

    <iframe src="https://open-web-calendar.hosted.quelltext.eu/calendar.html?url={fernet-url}"
        width="100%"
        height="600"
        frameborder="0">
    </iframe>

Troubleshooting
===============

If you don't see the calendar you expect, then try the following troubleshooting tips.

OWC shows an empty calendar
---------------------------

Open your Fernet URL in the browser.
This will download an iCalendar file to your computer.
Open the file, and if it doesn't start with ``BEGIN:VCALENDAR``, then the Google URL is wrong or Google's iCalendar feed is slow to pick up new events.
Updates can take 10–30 minutes.

Fields you expected to hide are still visible
---------------------------------------------

The Fernet token captures your field choices at the moment you generated it.
Changing the selected options later doesn't update an existing token.
You should generate a new link.

Query parameters aren't being applied
-------------------------------------

Make sure you URL-encoded the Fernet URL before passing it to OWC.

Related topics
==============

-   :doc:`../usage/web-service` is a reference for the ``/fetch`` and ``/fernet-generate`` endpoints.
