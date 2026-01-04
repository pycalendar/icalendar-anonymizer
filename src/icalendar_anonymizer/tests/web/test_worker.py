# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Tests for Cloudflare Workers entry point.

Note: worker.py requires Cloudflare Workers runtime modules (workers, asgi).
These are mocked in conftest.py to allow testing the module structure.
"""

from unittest.mock import AsyncMock, patch

import pytest


class TestWorkerModule:
    """Tests for Cloudflare Workers entry point module."""

    def test_worker_module_imports(self):
        """Test worker.py can be imported with mocked runtime modules."""
        from icalendar_anonymizer import worker

        assert worker is not None
        assert hasattr(worker, "Default")

    def test_default_class_structure(self):
        """Test Default class has correct structure."""
        from icalendar_anonymizer.worker import Default

        # Check class exists
        assert Default is not None

        # Check it has fetch method
        assert hasattr(Default, "fetch")

        # Check fetch is async
        import inspect

        assert inspect.iscoroutinefunction(Default.fetch)

    @pytest.mark.asyncio
    async def test_worker_fetch_method(self):
        """Test worker fetch method integrates with asgi.handle_fetch."""
        import sys

        from icalendar_anonymizer.worker import Default

        # Create a mock response
        mock_response = "test_response"
        mock_request = "test_request"

        # Create mock asgi module with handle_fetch
        mock_asgi = AsyncMock()
        mock_asgi.handle_fetch = AsyncMock(return_value=mock_response)

        # Patch asgi in sys.modules (since it's imported inside fetch method)
        with patch.dict(sys.modules, {"asgi": mock_asgi}):
            # Create worker instance and call fetch
            worker = Default()
            result = await worker.fetch(mock_request)

            # Verify asgi.handle_fetch was called
            mock_asgi.handle_fetch.assert_called_once()

            # Verify result
            assert result == mock_response

    def test_worker_imports_fastapi_app(self):
        """Test worker module imports the FastAPI app."""
        from icalendar_anonymizer.worker import app

        assert app is not None
        assert app.__class__.__name__ == "FastAPI"
