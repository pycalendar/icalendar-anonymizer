# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Cloudflare Workers entry point for iCalendar anonymizer web service.

This module provides the Worker entry point that integrates the FastAPI application
with Cloudflare Workers runtime using Pyodide (Python WebAssembly).

This file must be at the root level so that python_modules/ is in the import path.
"""

import os

from workers import WorkerEntrypoint

# Set environment marker before importing app to disable static file mounting
# In Cloudflare Workers, static files are served via Assets, not FastAPI
os.environ["CLOUDFLARE_WORKERS"] = "true"

from icalendar_anonymizer.webapp.main import app


class Default(WorkerEntrypoint):
    """Default Worker entry point for Cloudflare Workers.

    Handles incoming HTTP requests and routes them to the FastAPI application.
    """

    async def fetch(self, request):
        """Handle incoming HTTP request.

        Args:
            request: Cloudflare Workers Request object

        Returns:
            Cloudflare Workers Response object
        """
        import asgi

        return await asgi.handle_fetch(app, request)
