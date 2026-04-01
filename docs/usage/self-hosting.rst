..
   SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
   SPDX-License-Identifier: AGPL-3.0-or-later

============
Self-Hosting
============

Run icalendar-anonymizer locally with Docker for complete data privacy.

Why Self-Host?
==============

Some people won't trust a web service with their calendar data. They need to run this locally. Docker makes that easy.

If your company policy says no external services, you can pull the Docker image, run it locally, and use it via localhost:8000. Your data never leaves your machine.

Quick Start
===========

Prerequisites
-------------

- Docker installed
- Docker Compose installed (included with Docker Desktop)

Basic Setup
-----------

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/pycalendar/icalendar-anonymizer.git
   cd icalendar-anonymizer

   # Start the service
   docker-compose up -d

   # View logs
   docker-compose logs -f

   # Stop the service
   docker-compose down

The service will be available at http://localhost:8000

Configuration
=============

Environment Variables
---------------------

Configure the service by editing ``docker-compose.yml`` or setting environment variables:

Server Configuration
~~~~~~~~~~~~~~~~~~~~

``HOST``
   Network interface to bind to (default: ``0.0.0.0``)

``PORT``
   Port number to listen on (default: ``8000``)

``WORKERS``
   Number of Gunicorn worker processes (default: ``4``)

File Handling
~~~~~~~~~~~~~

``MAX_FILE_SIZE``
   Maximum upload size in bytes (default: ``10485760`` = 10MB)

Shareable Links
~~~~~~~~~~~~~~~

``FERNET_KEY``
   Secret key for Fernet encryption (enables live proxy shareable links)

   Generate a key:

   .. code-block:: python

      from icalendar_anonymizer.webapp.vendored.fernet_compat import Fernet
      print(Fernet.generate_key().decode())

   Or use command line:

   .. code-block:: bash

      python -c "from icalendar_anonymizer.webapp.vendored.fernet_compat import Fernet; print(Fernet.generate_key().decode())"

   .. warning::

      Keep this key secret! Anyone with the key can decrypt shareable link tokens.
      Store it securely (e.g., in a secrets manager or environment file with restricted permissions).

Example docker-compose.yml
--------------------------

.. code-block:: yaml

   services:
     icalendar-anonymizer:
       build: .
       ports:
         - "8000:8000"
       environment:
         - HOST=0.0.0.0
         - PORT=8000
         - WORKERS=4
         - MAX_FILE_SIZE=10485760
         - FERNET_KEY=your-secret-key-here  # Optional: enables live proxy links
       restart: unless-stopped

Docker Commands
===============

Build the Image
---------------

.. code-block:: bash

   docker-compose build

Start the Service
-----------------

.. code-block:: bash

   # Start in background
   docker-compose up -d

   # Start with logs visible
   docker-compose up

View Logs
---------

.. code-block:: bash

   # Follow logs
   docker-compose logs -f

   # View last 100 lines
   docker-compose logs --tail=100

Stop the Service
----------------

.. code-block:: bash

   docker-compose down

Restart the Service
-------------------

.. code-block:: bash

   docker-compose restart

Update to Latest Version
------------------------

.. code-block:: bash

   git pull
   docker-compose build
   docker-compose up -d

Health Check
============

The service includes a health check endpoint at ``/health`` that returns:

.. code-block:: json

   {
     "status": "healthy",
     "version": "0.1.0",
     "r2_enabled": false,
     "fernet_enabled": false
   }

The ``fernet_enabled`` field indicates whether Fernet shareable links are available (``FERNET_KEY`` environment variable is set).

Docker uses this endpoint to monitor service health. You can also check it manually:

.. code-block:: bash

   curl http://localhost:8000/health

Security Considerations
=======================

Non-Root User
-------------

The Docker container runs as a non-root user (UID 1000) for security.

Network Isolation
-----------------

The service only exposes port 8000. No other services or ports are accessible.

SSRF Protection
---------------

URL fetching includes SSRF protection that blocks:

- Private IP ranges (10.0.0.0/8, 192.168.0.0/16, 172.16.0.0/12)
- Loopback addresses (127.0.0.1, localhost)
- Link-local addresses (169.254.0.0/16)

Known limitation: DNS rebinding attacks may bypass these checks. See Issue #70 for details.

File Size Limits
----------------

Default 10MB limit prevents DoS attacks via large file uploads. Adjust via ``MAX_FILE_SIZE`` if needed.

Production Deployment
=====================

For production environments:

1. **Use HTTPS**: Put the service behind a reverse proxy (nginx, Caddy, Traefik) with TLS
2. **Tighten CORS**: Edit ``main.py`` to allow only specific origins instead of ``*``
3. **Add authentication**: See Issue #79 for planned authentication support
4. **Monitor logs**: Set up log aggregation and monitoring
5. **Regular updates**: Subscribe to security advisories and update promptly

Reverse Proxy Example (nginx)
-----------------------------

.. code-block:: nginx

   server {
       listen 443 ssl http2;
       server_name calendar.example.com;

       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;

       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }

Troubleshooting
===============

Service Won't Start
-------------------

Check logs:

.. code-block:: bash

   docker-compose logs

Common issues:

- Port 8000 already in use: Change ``PORT`` in docker-compose.yml
- Permission denied: Ensure Docker daemon is running

Health Check Failing
--------------------

Check if the service is responding:

.. code-block:: bash

   docker-compose exec icalendar-anonymizer curl http://localhost:8000/health

If no response, check worker logs for errors.

Build Fails
-----------

Ensure you have the .git directory (needed for version detection):

.. code-block:: bash

   ls -la .git

If missing, clone the repository instead of downloading a ZIP archive.

Image Too Large
---------------

The image is built with multi-stage builds to stay under 200MB. If larger:

1. Clean Docker build cache: ``docker system prune``
2. Rebuild: ``docker-compose build --no-cache``

Performance Issues
------------------

Adjust worker count based on CPU cores:

.. code-block:: yaml

   environment:
     - WORKERS=8  # Increase for more cores

Recommended: (CPU cores * 2) + 1
