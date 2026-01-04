# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Pytest configuration for icalendar-anonymizer tests."""

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture(scope="session", autouse=True)
def mock_cloudflare_workers_modules():
    """Mock Cloudflare Workers runtime modules for testing.

    This allows importing worker.py in tests even though the Workers
    runtime modules (workers, asgi) are not available locally.
    """
    # Create mock workers module
    mock_workers = MagicMock()
    mock_workers.WorkerEntrypoint = MagicMock

    # Create mock asgi module
    mock_asgi = MagicMock()
    mock_asgi.handle_fetch = AsyncMock(return_value=MagicMock())

    # Add to sys.modules before any imports
    sys.modules["workers"] = mock_workers
    sys.modules["asgi"] = mock_asgi

    yield

    # Cleanup
    sys.modules.pop("workers", None)
    sys.modules.pop("asgi", None)
