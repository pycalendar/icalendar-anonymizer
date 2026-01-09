# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Tests for share endpoints (POST /share and GET /s/{id})."""

import io

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


class TestShareEndpoint:
    """Tests for POST /share endpoint."""

    def test_share_valid_file(self):
        """Test sharing valid ICS file returns URL."""
        file_content = VALID_ICS.encode("utf-8")
        files = {"file": ("calendar.ics", io.BytesIO(file_content), "text/calendar")}

        response = client.post("/share", files=files)

        assert response.status_code == 200
        data = response.json()
        assert "url" in data
        assert "/s/" in data["url"]

        # Extract share ID from URL
        share_id = data["url"].split("/s/")[-1]
        assert len(share_id) == 8

    def test_share_invalid_ics(self):
        """Test sharing invalid ICS file returns error."""
        file_content = b"This is not a valid ICS file"
        files = {"file": ("invalid.ics", io.BytesIO(file_content), "text/calendar")}

        response = client.post("/share", files=files)

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_share_empty_file(self):
        """Test sharing empty file returns error."""
        file_content = b""
        files = {"file": ("empty.ics", io.BytesIO(file_content), "text/calendar")}

        response = client.post("/share", files=files)

        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_share_and_retrieve(self):
        """Test end-to-end share and retrieve flow."""
        file_content = VALID_ICS.encode("utf-8")
        files = {"file": ("calendar.ics", io.BytesIO(file_content), "text/calendar")}

        # Share the file
        share_response = client.post("/share", files=files)
        assert share_response.status_code == 200

        share_url = share_response.json()["url"]
        share_id = share_url.split("/s/")[-1]

        # Retrieve the shared file
        get_response = client.get(f"/s/{share_id}")
        assert get_response.status_code == 200
        assert get_response.headers["content-type"] == "text/calendar; charset=utf-8"

        # Verify content is anonymized
        content = get_response.content.decode("utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "Test Event" not in content  # Anonymized
        assert "Test description" not in content  # Anonymized
        assert "20250101T100000Z" in content  # Preserved

    def test_share_multiple_files_unique_ids(self):
        """Test sharing multiple files generates unique IDs."""
        file_content = VALID_ICS.encode("utf-8")
        files = {"file": ("calendar.ics", io.BytesIO(file_content), "text/calendar")}

        # Share first file
        response1 = client.post("/share", files=files)
        url1 = response1.json()["url"]
        id1 = url1.split("/s/")[-1]

        # Share second file (reset BytesIO)
        files = {"file": ("calendar.ics", io.BytesIO(file_content), "text/calendar")}
        response2 = client.post("/share", files=files)
        url2 = response2.json()["url"]
        id2 = url2.split("/s/")[-1]

        # IDs should be different
        assert id1 != id2


class TestGetSharedCalendar:
    """Tests for GET /s/{id} endpoint."""

    def test_get_shared_calendar_success(self):
        """Test retrieving existing shared calendar."""
        # First share a file
        file_content = VALID_ICS.encode("utf-8")
        files = {"file": ("calendar.ics", io.BytesIO(file_content), "text/calendar")}
        share_response = client.post("/share", files=files)
        share_id = share_response.json()["url"].split("/s/")[-1]

        # Retrieve it
        response = client.get(f"/s/{share_id}")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/calendar; charset=utf-8"
        assert f'filename="calendar-{share_id}.ics"' in response.headers["content-disposition"]
        assert "Cache-Control" in response.headers
        assert "max-age=86400" in response.headers["cache-control"]

    def test_get_shared_calendar_not_found(self):
        """Test retrieving nonexistent share ID returns 404."""
        response = client.get("/s/notfound")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_shared_calendar_invalid_id_length(self):
        """Test invalid share ID length returns 400."""
        response = client.get("/s/short")

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_get_shared_calendar_invalid_id_chars(self):
        """Test invalid share ID characters returns 400."""
        # Use invalid characters (spaces, special chars)
        response = client.get("/s/inv@lid!")

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_get_shared_calendar_valid_id_chars(self):
        """Test valid URL-safe characters in share ID."""
        # First share a file to get a valid ID
        file_content = VALID_ICS.encode("utf-8")
        files = {"file": ("calendar.ics", io.BytesIO(file_content), "text/calendar")}
        share_response = client.post("/share", files=files)
        share_id = share_response.json()["url"].split("/s/")[-1]

        # Verify ID contains only URL-safe chars
        assert len(share_id) == 8
        assert share_id.replace("-", "").replace("_", "").isalnum()


class TestHealthEndpointR2:
    """Tests for /health endpoint R2 detection."""

    def test_health_r2_enabled(self):
        """Test health endpoint reports R2 enabled in local dev."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # In local dev (TestClient), MockR2Client is injected
        assert data["r2_enabled"] is True
        assert data["status"] == "healthy"
        assert "version" in data
