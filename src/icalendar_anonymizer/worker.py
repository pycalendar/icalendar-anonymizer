# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Cloudflare Workers entry point for iCalendar anonymizer web service.

This module provides the Worker entry point that integrates the FastAPI application
with Cloudflare Workers runtime using Pyodide (Python WebAssembly).
"""

from workers import WorkerEntrypoint

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
