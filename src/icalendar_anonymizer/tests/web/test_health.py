# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Tests for health check endpoint."""

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

    def test_health_r2_disabled_by_default(self):
        """Test R2 is disabled by default."""
        response = client.get("/health")
        data = response.json()

        assert data["r2_enabled"] is False
