.. SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
.. SPDX-License-Identifier: AGPL-3.0-or-later

===========
Web Service
===========

REST API service for anonymizing iCalendar files. Three endpoints for different input methods.

Installation
============

Install the web service dependencies:

.. code-block:: shell

    pip install icalendar-anonymizer[web]

This installs:

- ``fastapi>=0.125.0`` - Web framework
- ``uvicorn[standard]>=0.38.0`` - ASGI server
- ``python-multipart>=0.0.18`` - File upload support
- ``httpx>=0.28.0`` - Async HTTP client for URL fetching

Running the Server
==================

Start the server with uvicorn:

.. code-block:: shell

    uvicorn icalendar_anonymizer.webapp.main:app --reload

The server starts on http://127.0.0.1:8000 by default.

For production deployment:

.. code-block:: shell

    uvicorn icalendar_anonymizer.webapp.main:app --host 0.0.0.0 --port 8000

API Documentation
=================

Interactive API documentation is available at:

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

Frontend Interface
==================

The web service includes a user-friendly web interface at the root URL (``/``).

Features
--------

The frontend provides three input methods:

Upload File
    Drag and drop or click to select an ``.ics`` file from your device.
    Maximum file size: 10 MB.

Paste Content
    Copy and paste iCalendar content directly into a text area.
    Useful for small calendars or quick tests.

Fetch from URL
    Enter a URL to fetch and anonymize a remote calendar.
    Subject to SSRF protection (see security considerations).

Accessibility
-------------

The interface is fully accessible:

- **Keyboard navigation**: All controls keyboard accessible with proper tab order
- **Screen reader support**: ARIA labels and live regions for status updates
- **High contrast**: WCAG AA compliant color contrast ratios
- **Mobile responsive**: Works on all device sizes
- **Progressive enhancement**: Basic functionality works without JavaScript

Usage Example
-------------

1. Navigate to ``http://localhost:8000/``
2. Choose an input method (upload, paste, or fetch)
3. Submit your calendar
4. Click "Download" to save the anonymized result

The interface handles errors gracefully with informative messages.

No-JavaScript Fallback
----------------------

If JavaScript is disabled, file upload still works via direct form submission to the
``/upload`` endpoint. The file downloads automatically on success.

API Endpoints
=============

POST /anonymize
---------------

Anonymize iCalendar content provided as JSON.

**Request**

.. code-block:: http

    POST /anonymize HTTP/1.1
    Content-Type: application/json

    {
      "ics": "BEGIN:VCALENDAR\nVERSION:2.0\n..."
    }

**Response (200 OK)**

.. code-block:: http

    HTTP/1.1 200 OK
    Content-Type: text/calendar
    Content-Disposition: attachment; filename="anonymized.ics"

    BEGIN:VCALENDAR
    VERSION:2.0
    ...

**Error Responses**

- ``400 Bad Request`` - Invalid ICS format or empty input
- ``500 Internal Server Error`` - Anonymization failed

**Example with curl**

.. code-block:: shell

    curl -X POST http://localhost:8000/anonymize \
      -H "Content-Type: application/json" \
      -d '{"ics": "BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR"}' \
      -o anonymized.ics

POST /upload
------------

Anonymize an uploaded iCalendar file.

**Request**

.. code-block:: http

    POST /upload HTTP/1.1
    Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

    ------WebKitFormBoundary
    Content-Disposition: form-data; name="file"; filename="calendar.ics"
    Content-Type: text/calendar

    BEGIN:VCALENDAR
    VERSION:2.0
    ...

**Response (200 OK)**

.. code-block:: http

    HTTP/1.1 200 OK
    Content-Type: text/calendar
    Content-Disposition: attachment; filename="anonymized.ics"

    BEGIN:VCALENDAR
    VERSION:2.0
    ...

**Error Responses**

- ``400 Bad Request`` - Invalid ICS format, empty file, or non-UTF-8 encoding
- ``413 Payload Too Large`` - File exceeds size limit
- ``500 Internal Server Error`` - Anonymization failed

**Example with curl**

.. code-block:: shell

    curl -X POST http://localhost:8000/upload \
      -F "file=@calendar.ics" \
      -o anonymized.ics

GET /fetch
----------

Fetch an iCalendar file from a URL and anonymize it.

**Security Features**

This endpoint includes SSRF (Server-Side Request Forgery) protection:

- Blocks private IP ranges (10.x, 172.16.x, 192.168.x, 169.254.x)
- Blocks localhost (127.0.0.1, ::1, 0.0.0.0)
- Blocks IPv6 private ranges (fc00::/7, fe80::/10)
- Only allows http:// and https:// schemes
- 10-second timeout
- 10 MB size limit
- Validates redirect destinations

**Request**

.. code-block:: http

    GET /fetch?url=https://example.com/calendar.ics HTTP/1.1

**Response (200 OK)**

.. code-block:: http

    HTTP/1.1 200 OK
    Content-Type: text/calendar
    Content-Disposition: attachment; filename="anonymized.ics"

    BEGIN:VCALENDAR
    VERSION:2.0
    ...

**Error Responses**

- ``400 Bad Request`` - Invalid URL, private IP, invalid ICS format, or connection failed
- ``408 Request Timeout`` - Request exceeded 10-second timeout
- ``413 Payload Too Large`` - Response exceeds 10 MB size limit
- ``Various HTTP status codes`` - Returns the actual HTTP status code from the upstream server (e.g., 404 Not Found, 500 Internal Server Error, 503 Service Unavailable)
- ``500 Internal Server Error`` - Anonymization failed

**Example with curl**

.. code-block:: shell

    curl "http://localhost:8000/fetch?url=https://example.com/calendar.ics" \
      -o anonymized.ics

**Known Limitations**

The SSRF protection has a Time-of-Check-Time-of-Use (TOCTOU) vulnerability to DNS rebinding attacks.
See `Issue #70 <https://github.com/mergecal/icalendar-anonymizer/issues/70>`_ for future enhancements.

Error Responses
===============

All error responses return JSON with the following format:

.. code-block:: json

    {
      "detail": "Error message describing what went wrong"
    }

Common error scenarios:

**Invalid ICS Format**

.. code-block:: json

    {
      "detail": "Invalid ICS format: Expected BEGIN:VCALENDAR"
    }

**Empty Input**

.. code-block:: json

    {
      "detail": "Input is empty"
    }

**Private IP Blocked**

.. code-block:: json

    {
      "detail": "Access to private IP 192.168.1.1 is not allowed"
    }

**URL Fetch Failed**

.. code-block:: json

    {
      "detail": "Failed to fetch URL: Connection timeout"
    }

CORS Configuration
==================

The server enables CORS with wildcard origins for development:

.. code-block:: python

    allow_origins=["*"]
    allow_credentials=False
    allow_methods=["*"]
    allow_headers=["*"]

**Production Hardening**

For production deployments, configure CORS to only allow your frontend domain:

.. code-block:: python

    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://yourdomain.com"],
        allow_credentials=True,
        allow_methods=["POST", "GET"],
        allow_headers=["Content-Type"],
    )

Self-Hosting
============

Docker Deployment
-----------------

Pull and run the Docker image:

.. code-block:: shell

    docker pull sashankbhamidi/icalendar-anonymizer
    docker run -p 8000:8000 sashankbhamidi/icalendar-anonymizer

The web service will be available at http://localhost:8000.

Build from source:

.. code-block:: shell

    docker build -t icalendar-anonymizer .
    docker run -p 8000:8000 icalendar-anonymizer

Manual Deployment
-----------------

For production deployment on a VPS or cloud server:

1. Install Python 3.11 or later
2. Create a virtual environment:

   .. code-block:: shell

       python -m venv venv
       source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install the package:

   .. code-block:: shell

       pip install icalendar-anonymizer[web]

4. Run with production settings:

   .. code-block:: shell

       uvicorn icalendar_anonymizer.webapp.main:app \
         --host 0.0.0.0 \
         --port 8000 \
         --workers 4 \
         --log-level info

5. Use a reverse proxy (nginx/Apache) for HTTPS and load balancing

Systemd Service
^^^^^^^^^^^^^^^

Create ``/etc/systemd/system/icalendar-anonymizer.service``:

.. code-block:: ini

    [Unit]
    Description=iCalendar Anonymizer Web Service
    After=network.target

    [Service]
    Type=notify
    User=www-data
    Group=www-data
    WorkingDirectory=/opt/icalendar-anonymizer
    Environment="PATH=/opt/icalendar-anonymizer/venv/bin"
    ExecStart=/opt/icalendar-anonymizer/venv/bin/uvicorn \
      icalendar_anonymizer.webapp.main:app \
      --host 0.0.0.0 \
      --port 8000 \
      --workers 4

    [Install]
    WantedBy=multi-user.target

Enable and start:

.. code-block:: shell

    sudo systemctl enable icalendar-anonymizer
    sudo systemctl start icalendar-anonymizer

Nginx Reverse Proxy
^^^^^^^^^^^^^^^^^^^

Example nginx configuration:

.. code-block:: nginx

    server {
        listen 80;
        server_name anonymizer.example.com;

        location / {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }

Add SSL with Let's Encrypt:

.. code-block:: shell

    sudo certbot --nginx -d anonymizer.example.com

Security Considerations
=======================

**SSRF Protection**

The ``/fetch`` endpoint implements SSRF protection but has known limitations.
For high-security deployments:

- Use network-level firewall rules
- Deploy in an isolated network segment
- Implement additional rate limiting
- Monitor for suspicious URL patterns

See `Issue #70 <https://github.com/mergecal/icalendar-anonymizer/issues/70>`_ for planned enhancements.

**Input Validation**

All endpoints validate:

- UTF-8 encoding (no binary corruption)
- iCalendar format (BEGIN:VCALENDAR required)
- File size limits (10 MB for URL fetching)

**Error Disclosure**

Error messages include technical details to aid debugging.
For production, consider customizing error handlers to limit information disclosure.

Testing
=======

Run the test suite:

.. code-block:: shell

    pip install -e ".[test,web]"
    pytest src/icalendar_anonymizer/tests/web/

Test coverage includes:

- All three endpoints with valid and invalid inputs
- SSRF protection (private IPs, localhost, redirects)
- UTF-8 encoding validation
- Error handling scenarios
- Large file handling

Performance
===========

**Benchmarks**

Approximate performance on a modern server:

- JSON input (``/anonymize``): ~50ms for typical calendar
- File upload (``/upload``): ~60ms including multipart parsing
- URL fetch (``/fetch``): ~200ms including network latency

**Scaling**

For high-traffic deployments:

- Increase uvicorn workers: ``--workers 8``
- Use multiple server instances behind a load balancer
- Consider async worker pools for URL fetching
- Implement caching for frequently accessed URLs (see `Issue #30 <https://github.com/mergecal/icalendar-anonymizer/issues/30>`_)

Troubleshooting
===============

**ImportError: No module named 'fastapi'**

Install the web extras:

.. code-block:: shell

    pip install icalendar-anonymizer[web]

**Connection Refused**

Check if the server is running:

.. code-block:: shell

    curl http://localhost:8000/docs

If not, start it:

.. code-block:: shell

    uvicorn icalendar_anonymizer.webapp.main:app --reload

**CORS Errors in Browser**

The server allows all origins by default.
If you're seeing CORS errors, check that your frontend is making requests to the correct URL.

**Timeout on /fetch**

The endpoint has a 10-second timeout.
For slow servers, the request will fail with a timeout error.
This is intentional to prevent resource exhaustion.

See Also
========

- :doc:`python-api` - Using the Python library directly
- :doc:`cli` - Command-line interface
- :doc:`../contributing` - Development guide
