# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Tests for FastAPI web service endpoints."""

import io

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from icalendar_anonymizer.webapp.main import _credentials_to_header, app

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

# Realistic ICS content with accented French text, for encoding fallback
# tests. Uses RFC 5545 CRLF line endings, unlike this file's other
# fixtures, since encoding edge cases are exactly where staying close to
# real-world calendar output matters.
VALID_ICS_ACCENTED_TEXT = (
    "BEGIN:VCALENDAR\r\n"
    "VERSION:2.0\r\n"
    "PRODID:-//Test//Test//EN\r\n"
    "BEGIN:VEVENT\r\n"
    "UID:test@example.com\r\n"
    "DTSTART:20250101T100000Z\r\n"
    "DTEND:20250101T110000Z\r\n"
    "SUMMARY:Réunion à café Montréal\r\n"
    "END:VEVENT\r\n"
    "END:VCALENDAR\r\n"
)


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

    def test_upload_latin1_file_decodes_correctly(self):
        """Test a Latin-1 file with no declared charset is decoded and anonymized."""
        file_content = VALID_ICS_ACCENTED_TEXT.encode("latin-1")
        files = {"file": ("legacy.ics", io.BytesIO(file_content), "text/calendar")}

        response = client.post("/upload", files=files, data={"config": '{"summary": "keep"}'})

        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Réunion à café Montréal" in content

    def test_upload_honors_declared_charset_outside_detection_scope(self):
        """Test a client-declared charset (e.g. UTF-16) on the upload is honored."""
        file_content = VALID_ICS_ACCENTED_TEXT.encode("utf-16")
        files = {"file": ("legacy.ics", io.BytesIO(file_content), "text/calendar; charset=utf-16")}

        response = client.post("/upload", files=files, data={"config": '{"summary": "keep"}'})

        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Réunion à café Montréal" in content

    def test_upload_falls_back_when_declared_charset_is_wrong(self):
        """Test an upload lying about its own charset falls back to detection, not a crash."""
        file_content = VALID_ICS_ACCENTED_TEXT.encode("cp1252")
        files = {"file": ("legacy.ics", io.BytesIO(file_content), "text/calendar; charset=utf-8")}

        response = client.post("/upload", files=files, data={"config": '{"summary": "keep"}'})

        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Réunion à café Montréal" in content

    def test_upload_undecodable_bytes_falls_back_and_fails_ics_parsing(self):
        """Test that non-UTF-8 bytes decode via fallback, then fail ICS parsing, not decoding."""
        # These bytes are not valid UTF-8, but the encoding fallback chain
        # (UTF-8 -> detection -> Latin-1) always produces *some* text, so
        # this now fails as invalid ICS content rather than a decode error.
        invalid_bytes = b"BEGIN:VCALENDAR\xff\xfeINVALID"
        files = {"file": ("invalid.ics", io.BytesIO(invalid_bytes), "text/calendar")}

        response = client.post("/upload", files=files)

        assert response.status_code == 400
        assert "invalid ics format" in response.json()["detail"].lower()


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

    def test_fetch_latin1_url_decodes_correctly(self, httpx_mock):
        """Test fetching a Latin-1 encoded response decodes correctly."""
        test_url = "https://example.com/calendar.ics"
        # content= sends raw bytes over the wire; text= would implicitly
        # UTF-8-encode the string and defeat the point of this test.
        httpx_mock.add_response(url=test_url, content=VALID_ICS_ACCENTED_TEXT.encode("latin-1"))

        response = client.get(f"/fetch?url={test_url}&summary=keep")

        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Réunion à café Montréal" in content
        # httpx's own response.text uses errors="replace" and would have
        # silently corrupted this instead of decoding it correctly.
        assert "�" not in content

    def test_fetch_honors_declared_charset_outside_detection_scope(self, httpx_mock):
        """Test a server-declared charset outside cp1252/Latin-1 (e.g. UTF-16) is honored."""
        test_url = "https://example.com/calendar.ics"
        httpx_mock.add_response(
            url=test_url,
            content=VALID_ICS_ACCENTED_TEXT.encode("utf-16"),
            headers={"Content-Type": "text/calendar; charset=utf-16"},
        )

        response = client.get(f"/fetch?url={test_url}&summary=keep")

        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Réunion à café Montréal" in content

    def test_fetch_falls_back_when_declared_charset_is_wrong(self, httpx_mock):
        """Test a server lying about its own charset falls back to detection, not a crash."""
        test_url = "https://example.com/calendar.ics"
        # Server claims UTF-8 but actually sends cp1252 bytes that are not
        # valid UTF-8 - this must not raise an unhandled UnicodeDecodeError.
        httpx_mock.add_response(
            url=test_url,
            content=VALID_ICS_ACCENTED_TEXT.encode("cp1252"),
            headers={"Content-Type": "text/calendar; charset=utf-8"},
        )

        response = client.get(f"/fetch?url={test_url}&summary=keep")

        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Réunion à café Montréal" in content

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

        # Mock the redirect response. The redirect target is never actually
        # requested: it's blocked before being dialed, since each hop is
        # validated and resolved before its connection is made.
        httpx_mock.add_response(
            url=test_url,
            status_code=302,
            headers={"Location": redirect_url},
        )

        response = client.get(f"/fetch?url={test_url}")

        # Should be blocked when the redirect target is validated
        assert response.status_code == 400
        assert "private" in response.json()["detail"].lower()

    def test_fetch_redirect_missing_location_header(self, httpx_mock):
        """A 3xx response with no Location header must be a clean 400, not a 500."""
        test_url = "https://example.com/redirect"
        httpx_mock.add_response(url=test_url, status_code=302)

        response = client.get(f"/fetch?url={test_url}")

        assert response.status_code == 400
        assert "location" in response.json()["detail"].lower()

    def test_fetch_redirect_malformed_location_header(self, httpx_mock):
        """A malformed Location header must surface as a 400, not a 500.

        httpx raises RemoteProtocolError, a RequestError subclass, while
        building the redirect request. The endpoint's existing
        RequestError handler turns that into a clean 400.
        """
        test_url = "https://example.com/redirect"
        httpx_mock.add_response(url=test_url, status_code=302, headers={"Location": "http://[::1"})

        response = client.get(f"/fetch?url={test_url}")

        assert response.status_code == 400

    def test_fetch_connection_error(self, httpx_mock):
        """Test handling of connection errors."""
        test_url = "https://nonexistent.example.com/calendar.ics"
        httpx_mock.add_exception(httpx.ConnectError("Connection failed"), url=test_url)

        response = client.get(f"/fetch?url={test_url}")

        assert response.status_code == 400
        assert "failed" in response.json()["detail"].lower()


class TestCredentialsToHeader:
    """Tests for _credentials_to_header()."""

    def test_basic_credentials_produce_base64_header(self):
        header = _credentials_to_header(
            {"type": "basic", "username": "alice", "password": "secret"}
        )
        assert header == {"Authorization": "Basic YWxpY2U6c2VjcmV0"}

    def test_bearer_credentials_produce_plain_token_header(self):
        header = _credentials_to_header({"type": "bearer", "token": "abc123"})
        assert header == {"Authorization": "Bearer abc123"}

    def test_none_credentials_produce_no_header(self):
        assert _credentials_to_header(None) is None

    def test_rejects_unknown_type_instead_of_guessing(self):
        # A capitalized or unexpected "type" must not silently fall through
        # to the bearer branch and produce a wrong-but-valid-looking header.
        # Reachable from a stale/malformed Fernet token payload, which isn't
        # revalidated against FetchAuth on read.
        with pytest.raises(HTTPException) as exc_info:
            _credentials_to_header({"type": "Basic", "token": "x"})
        assert exc_info.value.status_code == 400

    def test_rejects_basic_credentials_missing_password(self):
        with pytest.raises(HTTPException) as exc_info:
            _credentials_to_header({"type": "basic", "username": "alice"})
        assert exc_info.value.status_code == 400

    def test_rejects_bearer_credentials_missing_token(self):
        with pytest.raises(HTTPException) as exc_info:
            _credentials_to_header({"type": "bearer"})
        assert exc_info.value.status_code == 400


class TestFetchAuth:
    """Tests for POST /fetch with auth credentials."""

    def test_get_fetch_still_works_unauthenticated(self, httpx_mock):
        """GET /fetch is unaffected by adding POST /fetch."""
        test_url = "https://example.com/calendar.ics"
        httpx_mock.add_response(url=test_url, text=VALID_ICS)

        response = client.get(f"/fetch?url={test_url}")

        assert response.status_code == 200

    def test_post_basic_auth_sends_authorization_header(self, httpx_mock):
        test_url = "https://example.com/calendar.ics"
        httpx_mock.add_response(url=test_url, text=VALID_ICS)

        response = client.post(
            "/fetch",
            json={
                "url": test_url,
                "auth": {"type": "basic", "username": "alice", "password": "secret"},
            },
        )

        assert response.status_code == 200
        request = httpx_mock.get_request(url=test_url)
        assert request.headers["authorization"] == "Basic YWxpY2U6c2VjcmV0"

    def test_post_bearer_auth_sends_authorization_header(self, httpx_mock):
        test_url = "https://example.com/calendar.ics"
        httpx_mock.add_response(url=test_url, text=VALID_ICS)

        response = client.post(
            "/fetch", json={"url": test_url, "auth": {"type": "bearer", "token": "abc123"}}
        )

        assert response.status_code == 200
        request = httpx_mock.get_request(url=test_url)
        assert request.headers["authorization"] == "Bearer abc123"

    def test_post_without_auth_matches_get_response(self, httpx_mock):
        test_url = "https://example.com/calendar.ics"
        httpx_mock.add_response(url=test_url, text=VALID_ICS)

        response = client.post("/fetch", json={"url": test_url})

        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Test Event" not in content
        assert "20250101T100000Z" in content

    def test_post_basic_auth_missing_password_returns_400(self):
        response = client.post(
            "/fetch",
            json={"url": "https://example.com/x", "auth": {"type": "basic", "username": "alice"}},
        )

        assert response.status_code == 400
        assert "password" in response.json()["detail"].lower()

    def test_post_bearer_auth_missing_token_returns_400(self):
        response = client.post(
            "/fetch", json={"url": "https://example.com/x", "auth": {"type": "bearer"}}
        )

        assert response.status_code == 400
        assert "token" in response.json()["detail"].lower()

    def test_post_wrong_credentials_returns_401(self, httpx_mock):
        test_url = "https://example.com/calendar.ics"
        httpx_mock.add_response(url=test_url, status_code=401)

        response = client.post(
            "/fetch",
            json={
                "url": test_url,
                "auth": {"type": "basic", "username": "alice", "password": "wrong"},
            },
        )

        assert response.status_code == 401

    def test_post_applies_field_modes(self, httpx_mock):
        test_url = "https://example.com/calendar.ics"
        httpx_mock.add_response(url=test_url, text=VALID_ICS)

        response = client.post("/fetch", json={"url": test_url, "config": {"summary": "keep"}})

        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Test Event" in content

    def test_post_basic_auth_rejects_stray_token_field(self):
        # A basic-auth payload carrying a bearer-only field is a client
        # mistake, not a valid request with an ignored extra - reject it
        # instead of silently dropping the field.
        response = client.post(
            "/fetch",
            json={
                "url": "https://example.com/x",
                "auth": {"type": "basic", "username": "alice", "password": "secret", "token": "x"},
            },
        )

        assert response.status_code == 422

    def test_post_bearer_auth_rejects_stray_username_field(self):
        response = client.post(
            "/fetch",
            json={
                "url": "https://example.com/x",
                "auth": {"type": "bearer", "token": "abc123", "username": "alice"},
            },
        )

        assert response.status_code == 422


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


class TestCloudflareWorkersEnvironment:
    """Tests for Cloudflare Workers-specific behavior."""

    def test_static_files_mounted_in_local_dev(self):
        """Test static files are mounted when CLOUDFLARE_WORKERS is not set."""
        # In local dev mode (default), root endpoint should serve index.html
        response = client.get("/")
        assert response.status_code == 200

    def test_cloudflare_workers_env_check(self):
        """Test CLOUDFLARE_WORKERS environment variable detection."""
        import os

        # Verify the env var is not set by default in tests
        assert os.getenv("CLOUDFLARE_WORKERS") is None


class TestAnonymizeWithConfig:
    """Integration tests for /anonymize endpoint with field configuration."""

    def test_config_summary_keep(self):
        """Test config with summary=keep preserves summary."""
        response = client.post(
            "/anonymize",
            json={"ics": VALID_ICS, "config": {"summary": "keep"}},
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "Test Event" in content
        assert "Test description" not in content  # Other fields still anonymized

    def test_config_location_remove(self):
        """Test config with location=remove strips location."""
        response = client.post(
            "/anonymize",
            json={"ics": VALID_ICS, "config": {"location": "remove"}},
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "LOCATION" not in content
        assert "BEGIN:VEVENT" in content  # Event still valid

    def test_config_description_replace(self):
        """Test config with description=replace uses placeholder."""
        response = client.post(
            "/anonymize",
            json={"ics": VALID_ICS, "config": {"description": "replace"}},
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "[Content removed]" in content
        assert "Test description" not in content

    def test_config_mixed_modes(self):
        """Test config with multiple field modes."""
        response = client.post(
            "/anonymize",
            json={
                "ics": VALID_ICS,
                "config": {
                    "summary": "keep",
                    "location": "remove",
                    "description": "replace",
                },
            },
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "Test Event" in content  # kept
        assert "LOCATION" not in content  # removed
        assert "[Content removed]" in content  # replaced

    def test_config_uid_keep(self):
        """Test config with uid=keep preserves UID."""
        response = client.post(
            "/anonymize",
            json={"ics": VALID_ICS, "config": {"uid": "keep"}},
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "test@example.com" in content

    def test_config_uid_replace(self):
        """Test config with uid=replace uses placeholder."""
        response = client.post(
            "/anonymize",
            json={"ics": VALID_ICS, "config": {"uid": "replace"}},
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "redacted-" in content
        assert "@anonymous.local" in content
        assert "test@example.com" not in content

    def test_config_no_config_defaults_to_randomize(self):
        """Test that no config results in randomize behavior."""
        response = client.post("/anonymize", json={"ics": VALID_ICS})
        assert response.status_code == 200
        content = response.content.decode()
        assert "Test Event" not in content
        assert "Test description" not in content
        assert "Test location" not in content

    def test_config_invalid_field_rejected(self):
        """Test that invalid field names are rejected."""
        response = client.post(
            "/anonymize",
            json={"ics": VALID_ICS, "config": {"invalid_field": "keep"}},
        )
        # Pydantic validation should fail with 422
        assert response.status_code == 422

    def test_config_invalid_mode_rejected(self):
        """Test that invalid mode values are rejected."""
        response = client.post(
            "/anonymize",
            json={"ics": VALID_ICS, "config": {"summary": "invalid_mode"}},
        )
        # Pydantic validation should fail with 422
        assert response.status_code == 422


class TestFetchWithConfig:
    """Integration tests for /fetch endpoint with field configuration via query params."""

    def test_fetch_with_summary_keep(self, httpx_mock):
        """Test /fetch with summary=keep query param."""
        test_url = "https://example.com/cal.ics"
        httpx_mock.add_response(url=test_url, text=VALID_ICS)

        response = client.get(f"/fetch?url={test_url}&summary=keep")
        assert response.status_code == 200
        content = response.content.decode()
        assert "Test Event" in content

    def test_fetch_with_location_remove(self, httpx_mock):
        """Test /fetch with location=remove query param."""
        test_url = "https://example.com/cal.ics"
        httpx_mock.add_response(url=test_url, text=VALID_ICS)

        response = client.get(f"/fetch?url={test_url}&location=remove")
        assert response.status_code == 200
        content = response.content.decode()
        assert "LOCATION" not in content

    def test_fetch_with_description_replace(self, httpx_mock):
        """Test /fetch with description=replace query param."""
        test_url = "https://example.com/cal.ics"
        httpx_mock.add_response(url=test_url, text=VALID_ICS)

        response = client.get(f"/fetch?url={test_url}&description=replace")
        assert response.status_code == 200
        content = response.content.decode()
        assert "[Content removed]" in content
        assert "Test description" not in content

    def test_fetch_with_multiple_params(self, httpx_mock):
        """Test /fetch with multiple field config query params."""
        test_url = "https://example.com/cal.ics"
        httpx_mock.add_response(url=test_url, text=VALID_ICS)

        response = client.get(
            f"/fetch?url={test_url}&summary=keep&location=remove&description=replace"
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "Test Event" in content  # kept
        assert "LOCATION" not in content  # removed
        assert "[Content removed]" in content  # replaced

    def test_fetch_with_uid_keep(self, httpx_mock):
        """Test /fetch with uid=keep query param."""
        test_url = "https://example.com/cal.ics"
        httpx_mock.add_response(url=test_url, text=VALID_ICS)

        response = client.get(f"/fetch?url={test_url}&uid=keep")
        assert response.status_code == 200
        content = response.content.decode()
        assert "test@example.com" in content


class TestUploadWithConfig:
    """Integration tests for /upload endpoint with field configuration."""

    def test_upload_with_config_summary_keep(self):
        """Test /upload with config form field (summary=keep)."""
        files = {"file": ("test.ics", VALID_ICS.encode(), "text/calendar")}
        data = {"config": '{"summary": "keep"}'}
        response = client.post("/upload", files=files, data=data)
        assert response.status_code == 200
        content = response.content.decode()
        assert "Test Event" in content

    def test_upload_with_config_location_remove(self):
        """Test /upload with config form field (location=remove)."""
        files = {"file": ("test.ics", VALID_ICS.encode(), "text/calendar")}
        data = {"config": '{"location": "remove"}'}
        response = client.post("/upload", files=files, data=data)
        assert response.status_code == 200
        content = response.content.decode()
        assert "LOCATION" not in content

    def test_upload_with_config_mixed_modes(self):
        """Test /upload with multiple field modes in config."""
        files = {"file": ("test.ics", VALID_ICS.encode(), "text/calendar")}
        data = {"config": '{"summary": "keep", "location": "remove", "description": "replace"}'}
        response = client.post("/upload", files=files, data=data)
        assert response.status_code == 200
        content = response.content.decode()
        assert "Test Event" in content  # kept
        assert "LOCATION" not in content  # removed
        assert "[Content removed]" in content  # replaced

    def test_upload_with_invalid_config_json(self):
        """Test /upload with malformed config JSON."""
        files = {"file": ("test.ics", VALID_ICS.encode(), "text/calendar")}
        data = {"config": "not valid json"}
        response = client.post("/upload", files=files, data=data)
        assert response.status_code == 400
        assert "Invalid config" in response.json()["detail"]

    def test_upload_without_config_uses_defaults(self):
        """Test /upload without config uses default randomize behavior."""
        files = {"file": ("test.ics", VALID_ICS.encode(), "text/calendar")}
        response = client.post("/upload", files=files)
        assert response.status_code == 200
        content = response.content.decode()
        assert "Test Event" not in content
        assert "Test description" not in content
