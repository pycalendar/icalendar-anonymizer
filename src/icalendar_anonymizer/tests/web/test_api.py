# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Tests for FastAPI web service endpoints."""

import io

import httpx
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


class TestAnonymizeEndpoint:
    """Tests for POST /anonymize endpoint."""

    def test_anonymize_valid_ics(self):
        """Test anonymizing valid ICS content via JSON."""
        response = client.post("/anonymize", json={"ics": VALID_ICS})

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/calendar; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        assert "anonymized.ics" in response.headers["content-disposition"]

        # Verify content is valid ICS
        content = response.content.decode("utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "BEGIN:VEVENT" in content
        assert "END:VEVENT" in content
        assert "END:VCALENDAR" in content

        # Verify personal data is anonymized
        assert "Test Event" not in content
        assert "Test description" not in content
        assert "Test location" not in content

        # Verify technical properties preserved
        assert "20250101T100000Z" in content

    def test_anonymize_empty_input(self):
        """Test error handling for empty input."""
        response = client.post("/anonymize", json={"ics": ""})

        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_anonymize_invalid_ics(self):
        """Test error handling for invalid ICS format."""
        response = client.post("/anonymize", json={"ics": INVALID_ICS})

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_anonymize_whitespace_only(self):
        """Test error handling for whitespace-only input."""
        response = client.post("/anonymize", json={"ics": "   \n  \t  "})

        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()


class TestUploadEndpoint:
    """Tests for POST /upload endpoint."""

    def test_upload_valid_file(self):
        """Test uploading and anonymizing valid ICS file."""
        file_content = VALID_ICS.encode("utf-8")
        files = {"file": ("calendar.ics", io.BytesIO(file_content), "text/calendar")}

        response = client.post("/upload", files=files)

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/calendar; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]

        # Verify content is anonymized
        content = response.content.decode("utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "Test Event" not in content
        assert "20250101T100000Z" in content

    def test_upload_empty_file(self):
        """Test error handling for empty file upload."""
        files = {"file": ("empty.ics", io.BytesIO(b""), "text/calendar")}

        response = client.post("/upload", files=files)

        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_upload_invalid_file(self):
        """Test error handling for invalid ICS file upload."""
        file_content = INVALID_ICS.encode("utf-8")
        files = {"file": ("invalid.ics", io.BytesIO(file_content), "text/calendar")}

        response = client.post("/upload", files=files)

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_upload_large_file(self):
        """Test error handling for file exceeding size limit."""
        # Create file larger than 10MB
        large_content = b"x" * (11 * 1024 * 1024)
        files = {"file": ("large.ics", io.BytesIO(large_content), "text/calendar")}

        response = client.post("/upload", files=files)

        assert response.status_code == 413
        assert "too large" in response.json()["detail"].lower()

    def test_upload_utf8_encoding(self):
        """Test handling of UTF-8 encoded files."""
        ics_with_unicode = VALID_ICS.replace("Test Event", "Test Event 日本語 émojis 🎉")
        file_content = ics_with_unicode.encode("utf-8")
        files = {"file": ("unicode.ics", io.BytesIO(file_content), "text/calendar")}

        response = client.post("/upload", files=files)

        assert response.status_code == 200

    def test_upload_invalid_utf8(self):
        """Test error handling for non-UTF-8 encoded files."""
        # Invalid UTF-8 bytes
        invalid_utf8 = b"BEGIN:VCALENDAR\xff\xfeINVALID"
        files = {"file": ("invalid.ics", io.BytesIO(invalid_utf8), "text/calendar")}

        response = client.post("/upload", files=files)

        assert response.status_code == 400
        assert "utf-8" in response.json()["detail"].lower()


class TestFetchEndpoint:
    """Tests for GET /fetch endpoint."""

    def test_fetch_valid_url(self, httpx_mock):
        """Test fetching and anonymizing from valid URL."""
        test_url = "https://example.com/calendar.ics"
        httpx_mock.add_response(url=test_url, text=VALID_ICS)

        response = client.get(f"/fetch?url={test_url}")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/calendar; charset=utf-8"

        content = response.content.decode("utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "Test Event" not in content

    def test_fetch_localhost_blocked(self):
        """Test SSRF protection blocks localhost."""
        response = client.get("/fetch?url=http://localhost/calendar.ics")

        assert response.status_code == 400
        assert "localhost" in response.json()["detail"].lower()

    def test_fetch_127_0_0_1_blocked(self):
        """Test SSRF protection blocks 127.0.0.1."""
        response = client.get("/fetch?url=http://127.0.0.1/calendar.ics")

        assert response.status_code == 400
        assert "private" in response.json()["detail"].lower()

    def test_fetch_private_ip_blocked(self):
        """Test SSRF protection blocks private IP ranges."""
        private_ips = [
            "http://10.0.0.1/calendar.ics",
            "http://172.16.0.1/calendar.ics",
            "http://192.168.1.1/calendar.ics",
            "http://169.254.0.1/calendar.ics",
        ]

        for url in private_ips:
            response = client.get(f"/fetch?url={url}")
            assert response.status_code == 400
            assert "private" in response.json()["detail"].lower()

    def test_fetch_invalid_scheme(self):
        """Test rejection of non-http(s) schemes."""
        invalid_schemes = [
            "file:///etc/passwd",
            "ftp://example.com/calendar.ics",
            "data:text/calendar,BEGIN:VCALENDAR",
        ]

        for url in invalid_schemes:
            response = client.get(f"/fetch?url={url}")
            assert response.status_code == 400
            assert "scheme" in response.json()["detail"].lower()

    def test_fetch_404_error(self, httpx_mock):
        """Test handling of 404 errors from external URL."""
        test_url = "https://example.com/notfound.ics"
        httpx_mock.add_response(url=test_url, status_code=404)

        response = client.get(f"/fetch?url={test_url}")

        assert response.status_code == 404

    def test_fetch_timeout(self, httpx_mock):
        """Test handling of timeout errors."""
        test_url = "https://example.com/slow.ics"
        httpx_mock.add_exception(httpx.TimeoutException("Timeout"), url=test_url)

        response = client.get(f"/fetch?url={test_url}")

        assert response.status_code == 408
        assert "timeout" in response.json()["detail"].lower()

    def test_fetch_invalid_ics_from_url(self, httpx_mock):
        """Test handling of invalid ICS content from URL."""
        test_url = "https://example.com/invalid.ics"
        httpx_mock.add_response(url=test_url, text=INVALID_ICS)

        response = client.get(f"/fetch?url={test_url}")

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_fetch_large_response(self, httpx_mock):
        """Test handling of response exceeding size limit."""
        test_url = "https://example.com/large.ics"
        large_content = "x" * (11 * 1024 * 1024)
        httpx_mock.add_response(url=test_url, text=large_content)

        response = client.get(f"/fetch?url={test_url}")

        assert response.status_code == 413
        assert "too large" in response.json()["detail"].lower()

    def test_fetch_redirect_validation(self, httpx_mock):
        """Test that redirects to private IPs are blocked."""
        test_url = "https://example.com/redirect"
        redirect_url = "http://127.0.0.1/calendar.ics"

        # Mock the redirect chain
        httpx_mock.add_response(
            url=test_url,
            status_code=302,
            headers={"Location": redirect_url},
        )
        httpx_mock.add_response(url=redirect_url, text=VALID_ICS)

        response = client.get(f"/fetch?url={test_url}")

        # Should be blocked when final URL is validated
        assert response.status_code == 400
        assert "private" in response.json()["detail"].lower()

    def test_fetch_connection_error(self, httpx_mock):
        """Test handling of connection errors."""
        test_url = "https://nonexistent.example.com/calendar.ics"
        httpx_mock.add_exception(httpx.ConnectError("Connection failed"), url=test_url)

        response = client.get(f"/fetch?url={test_url}")

        assert response.status_code == 400
        assert "failed" in response.json()["detail"].lower()


class TestSSRFProtection:
    """Tests for SSRF protection mechanisms."""

    def test_ipv6_localhost_blocked(self):
        """Test IPv6 localhost is blocked."""
        response = client.get("/fetch?url=http://[::1]/calendar.ics")

        assert response.status_code == 400

    def test_ipv6_private_blocked(self):
        """Test IPv6 private addresses are blocked."""
        ipv6_private = [
            "http://[fc00::1]/calendar.ics",
            "http://[fe80::1]/calendar.ics",
        ]

        for url in ipv6_private:
            response = client.get(f"/fetch?url={url}")
            assert response.status_code == 400

    def test_zero_ip_blocked(self):
        """Test 0.0.0.0 is blocked."""
        response = client.get("/fetch?url=http://0.0.0.0/calendar.ics")

        assert response.status_code == 400
        assert "localhost" in response.json()["detail"].lower()

    def test_public_ip_allowed(self, httpx_mock):
        """Test public IP addresses are allowed."""
        test_url = "https://8.8.8.8/calendar.ics"
        httpx_mock.add_response(url=test_url, text=VALID_ICS)

        response = client.get(f"/fetch?url={test_url}")

        assert response.status_code == 200


class TestCORS:
    """Tests for CORS configuration."""

    def test_cors_headers_present(self):
        """Test CORS headers are present in responses."""
        response = client.post(
            "/anonymize",
            json={"ics": VALID_ICS},
            headers={"Origin": "https://example.com"},
        )

        assert "access-control-allow-origin" in response.headers


class TestResponseFormat:
    """Tests for response format consistency."""

    def test_content_type_header(self):
        """Test all endpoints return correct Content-Type."""
        # Test /anonymize
        response = client.post("/anonymize", json={"ics": VALID_ICS})
        assert "text/calendar" in response.headers["content-type"]

        # Test /upload
        files = {"file": ("test.ics", io.BytesIO(VALID_ICS.encode()), "text/calendar")}
        response = client.post("/upload", files=files)
        assert "text/calendar" in response.headers["content-type"]

    def test_content_disposition_header(self):
        """Test Content-Disposition header is set correctly."""
        response = client.post("/anonymize", json={"ics": VALID_ICS})

        assert "content-disposition" in response.headers
        assert "attachment" in response.headers["content-disposition"]
        assert "filename" in response.headers["content-disposition"]
        assert ".ics" in response.headers["content-disposition"]

    def test_error_response_format(self):
        """Test error responses return JSON with detail field."""
        response = client.post("/anonymize", json={"ics": ""})

        assert response.status_code == 400
        assert "detail" in response.json()
        assert isinstance(response.json()["detail"], str)
