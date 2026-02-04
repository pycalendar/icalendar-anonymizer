# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Tests for /anonymized curl-friendly endpoint."""

from fastapi.testclient import TestClient

from icalendar_anonymizer.webapp.main import app

client = TestClient(app)

# Sample valid ICS content
VALID_ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:test@example.com
DTSTART:20250101T100000Z
DTEND:20250101T110000Z
SUMMARY:Test Event
DESCRIPTION:Test description
LOCATION:Test location
END:VEVENT
END:VCALENDAR
"""

INVALID_ICS = "This is not a valid ICS file"


class TestAnonymizedGetEndpoint:
    """Tests for GET /anonymized endpoint."""

    def test_get_valid_ics(self):
        """Test GET with valid ICS query parameter."""
        response = client.get("/anonymized", params={"ics": VALID_ICS})

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/calendar; charset=utf-8"

        content = response.content.decode("utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "BEGIN:VEVENT" in content

        # Verify personal data is anonymized
        assert "Test Event" not in content
        assert "Test description" not in content

    def test_get_missing_param(self):
        """Test GET without ics parameter returns 400."""
        response = client.get("/anonymized")

        assert response.status_code == 400
        assert "Missing 'ics' query parameter" in response.json()["detail"]

    def test_get_empty_param(self):
        """Test GET with empty ics parameter returns 400."""
        response = client.get("/anonymized", params={"ics": ""})

        assert response.status_code == 400

    def test_get_invalid_ics(self):
        """Test GET with invalid ICS returns 400."""
        response = client.get("/anonymized", params={"ics": INVALID_ICS})

        assert response.status_code == 400
        assert "Invalid ICS format" in response.json()["detail"]


class TestAnonymizedPostEndpoint:
    """Tests for POST /anonymized endpoint."""

    def test_post_valid_ics(self):
        """Test POST with valid ICS body."""
        response = client.post(
            "/anonymized",
            content=VALID_ICS.encode("utf-8"),
            headers={"Content-Type": "text/plain"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/calendar; charset=utf-8"

        content = response.content.decode("utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "BEGIN:VEVENT" in content

        # Verify personal data is anonymized
        assert "Test Event" not in content
        assert "Test description" not in content

    def test_post_empty_body(self):
        """Test POST with empty body returns 400."""
        response = client.post(
            "/anonymized",
            content=b"",
            headers={"Content-Type": "text/plain"},
        )

        assert response.status_code == 400
        assert "Empty request body" in response.json()["detail"]

    def test_post_invalid_utf8(self):
        """Test POST with invalid UTF-8 returns 400."""
        response = client.post(
            "/anonymized",
            content=b"\xff\xfe",  # Invalid UTF-8 bytes
            headers={"Content-Type": "text/plain"},
        )

        assert response.status_code == 400
        assert "Invalid UTF-8 encoding" in response.json()["detail"]

    def test_post_invalid_ics(self):
        """Test POST with invalid ICS returns 400."""
        response = client.post(
            "/anonymized",
            content=INVALID_ICS.encode("utf-8"),
            headers={"Content-Type": "text/plain"},
        )

        assert response.status_code == 400
        assert "Invalid ICS format" in response.json()["detail"]


class TestAnonymizedResponseFormat:
    """Tests for /anonymized response format."""

    def test_response_content_type(self):
        """Test response has text/calendar content type."""
        response = client.post(
            "/anonymized",
            content=VALID_ICS.encode("utf-8"),
        )

        assert response.status_code == 200
        assert "text/calendar" in response.headers["content-type"]

    def test_no_content_disposition_post(self):
        """Test POST response has no Content-Disposition header (allows piping)."""
        response = client.post(
            "/anonymized",
            content=VALID_ICS.encode("utf-8"),
        )

        assert response.status_code == 200
        assert "content-disposition" not in response.headers

    def test_no_content_disposition_get(self):
        """Test GET response has no Content-Disposition header (allows piping)."""
        response = client.get("/anonymized", params={"ics": VALID_ICS})

        assert response.status_code == 200
        assert "content-disposition" not in response.headers

    def test_technical_properties_preserved(self):
        """Test technical properties like dates are preserved."""
        response = client.post(
            "/anonymized",
            content=VALID_ICS.encode("utf-8"),
        )

        content = response.content.decode("utf-8")
        assert "20250101T100000Z" in content  # DTSTART preserved
        assert "20250101T110000Z" in content  # DTEND preserved
