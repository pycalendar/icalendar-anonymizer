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

# Pyodide includes cryptography 46.0.3 as a built-in package
# Import it here to ensure it's available before FastAPI app initialization
import contextlib

with contextlib.suppress(ImportError):
    import cryptography  # noqa: F401

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

        # Copy secrets from Workers env to os.environ for app compatibility
        if hasattr(self.env, "FERNET_KEY"):
            os.environ["FERNET_KEY"] = self.env.FERNET_KEY

        return await asgi.fetch(app, request, self.env)
