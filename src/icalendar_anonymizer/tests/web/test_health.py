# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Tests for health check endpoint."""

import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from icalendar_anonymizer.version import version
from icalendar_anonymizer.webapp.main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_200(self):
        """Test health endpoint returns 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_json(self):
        """Test health endpoint returns JSON."""
        response = client.get("/health")
        assert response.headers["content-type"] == "application/json"

    def test_health_response_structure(self):
        """Test health endpoint response has correct structure."""
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert "r2_enabled" in data
        assert "fernet_enabled" in data

    def test_health_status_is_healthy(self):
        """Test health endpoint reports healthy status."""
        response = client.get("/health")
        data = response.json()

        assert data["status"] == "healthy"

    def test_health_version_matches_package(self):
        """Test health endpoint version matches package version."""
        response = client.get("/health")
        data = response.json()

        assert data["version"] == version

    def test_health_r2_disabled_in_local_dev(self):
        """Test R2 is disabled in local dev (no CLOUDFLARE_WORKERS env)."""
        response = client.get("/health")
        data = response.json()

        # r2_enabled is False in local dev because shareable links
        # only make sense with persistent R2 storage (Cloudflare Workers)
        assert data["r2_enabled"] is False

    def test_health_fernet_disabled_without_key(self):
        """Test Fernet is disabled when FERNET_KEY not set."""
        with patch.dict(os.environ, {}, clear=False):
            if "FERNET_KEY" in os.environ:
                del os.environ["FERNET_KEY"]

            response = client.get("/health")
            data = response.json()

            assert data["fernet_enabled"] is False

    def test_health_fernet_enabled_with_key(self):
        """Test Fernet is enabled when FERNET_KEY is set."""
        with patch.dict(os.environ, {"FERNET_KEY": "test-key"}):
            response = client.get("/health")
            data = response.json()

            assert data["fernet_enabled"] is True
