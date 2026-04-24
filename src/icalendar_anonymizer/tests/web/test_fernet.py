# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Tests for Fernet-based encrypted shareable links."""

import base64
import json
import os
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient

from icalendar_anonymizer.webapp.main import app
from icalendar_anonymizer.webapp.vendored.fernet_compat import Fernet

client = TestClient(app)


def _extract_token_from_url(url: str) -> str:
    """Extract Fernet token from shareable URL."""
    return url.split("/fernet/")[1]


def _generate_fernet_token(key: str, calendar_url: str) -> str:
    """Test helper that generates a Fernet token via API and extracts it from URL.

    Calls POST /fernet-generate with the given URL and returns the token
    extracted from the response URL.

    Args:
        key: Fernet key
        calendar_url: Calendar URL to encrypt

    Returns:
        Extracted token string from the shareable URL
    """
    with patch.dict(os.environ, {"FERNET_KEY": key}):
        response = client.post("/fernet-generate", json={"url": calendar_url})
        assert response.status_code == 200
        return _extract_token_from_url(response.json()["url"])


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


class TestFernetGenerate:
    """Tests for POST /fernet-generate endpoint."""

    def test_generate_without_key(self):
        """Test that endpoint returns 503 when FERNET_KEY not set."""
        with patch.dict(os.environ, {}, clear=False):
            if "FERNET_KEY" in os.environ:
                del os.environ["FERNET_KEY"]

            response = client.post(
                "/fernet-generate", json={"url": "https://example.com/calendar.ics"}
            )

            assert response.status_code == 503
            assert "not configured" in response.json()["detail"]

    def test_generate_with_valid_url(self):
        """Test generating Fernet token with valid URL."""
        # Generate a valid Fernet key
        key = Fernet.generate_key().decode()

        with patch.dict(os.environ, {"FERNET_KEY": key}):
            response = client.post(
                "/fernet-generate", json={"url": "https://example.com/calendar.ics"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "url" in data
            assert "/fernet/" in data["url"]

            # Extract token from URL
            token = _extract_token_from_url(data["url"])

            # Verify token can be decrypted
            cipher = Fernet(key.encode())
            decrypted = cipher.decrypt(token.encode())
            payload = json.loads(decrypted.decode())

            assert payload["url"] == "https://example.com/calendar.ics"
            assert "salt" in payload
            # Verify salt is base64 encoded and 32 bytes
            salt_bytes = base64.b64decode(payload["salt"])
            assert len(salt_bytes) == 32

    def test_generate_with_invalid_url_scheme(self):
        """Test error handling for invalid URL scheme."""
        key = Fernet.generate_key().decode()

        with patch.dict(os.environ, {"FERNET_KEY": key}):
            response = client.post(
                "/fernet-generate", json={"url": "ftp://example.com/calendar.ics"}
            )

            assert response.status_code == 400
            assert "scheme" in response.json()["detail"].lower()

    def test_generate_with_localhost(self):
        """Test SSRF protection blocks localhost."""
        key = Fernet.generate_key().decode()

        with patch.dict(os.environ, {"FERNET_KEY": key}):
            response = client.post(
                "/fernet-generate", json={"url": "http://localhost/calendar.ics"}
            )

            assert response.status_code == 400
            assert "localhost" in response.json()["detail"].lower()

    def test_generate_with_private_ip(self):
        """Test SSRF protection blocks private IPs."""
        key = Fernet.generate_key().decode()

        with patch.dict(os.environ, {"FERNET_KEY": key}):
            response = client.post(
                "/fernet-generate", json={"url": "http://192.168.1.1/calendar.ics"}
            )

            assert response.status_code == 400
            assert "private" in response.json()["detail"].lower()

    @pytest.mark.parametrize(
        ("body", "expected"),
        [
            (
                {"url": "https://example.com/calendar.ics", "config": {"summary": "keep"}},
                {"SUMMARY": "keep"},
            ),
            ({"url": "https://example.com/calendar.ics"}, None),
        ],
        ids=["with_config", "without_config"],
    )
    def test_generate_field_modes_in_payload(self, body, expected):
        """field_modes is stored in the payload when config is provided, omitted otherwise."""
        key = Fernet.generate_key().decode()

        with patch.dict(os.environ, {"FERNET_KEY": key}):
            response = client.post("/fernet-generate", json=body)

            assert response.status_code == 200
            token = _extract_token_from_url(response.json()["url"])
            payload = json.loads(Fernet(key.encode()).decrypt(token.encode()).decode())

            assert payload.get("field_modes") == expected


class TestFernetFetch:
    """Tests for GET /fernet/{token} endpoint."""

    def test_fetch_without_key(self):
        """Test that endpoint returns 503 when FERNET_KEY not set."""
        with patch.dict(os.environ, {}, clear=False):
            if "FERNET_KEY" in os.environ:
                del os.environ["FERNET_KEY"]

            response = client.get("/fernet/dummy-token")

            assert response.status_code == 503
            assert "not configured" in response.json()["detail"]

    def test_fetch_with_invalid_token(self):
        """Test error handling for invalid token."""
        key = Fernet.generate_key().decode()

        with patch.dict(os.environ, {"FERNET_KEY": key}):
            response = client.get("/fernet/invalid-token-data")

            assert response.status_code == 400
            assert "invalid" in response.json()["detail"].lower()

    def test_fetch_with_malformed_payload(self):
        """Test error handling for token with malformed JSON payload."""
        key = Fernet.generate_key().decode()
        cipher = Fernet(key.encode())

        # Create token with invalid JSON
        token = cipher.encrypt(b"not json").decode()

        with patch.dict(os.environ, {"FERNET_KEY": key}):
            response = client.get(f"/fernet/{token}")

            assert response.status_code == 400
            assert "malformed" in response.json()["detail"].lower()

    def test_fetch_with_missing_url(self):
        """Test error handling for token missing URL field."""
        key = Fernet.generate_key().decode()
        cipher = Fernet(key.encode())

        # Create token without URL
        payload = {"salt": base64.b64encode(b"test").decode()}
        token = cipher.encrypt(json.dumps(payload).encode()).decode()

        with patch.dict(os.environ, {"FERNET_KEY": key}):
            response = client.get(f"/fernet/{token}")

            assert response.status_code == 400
            assert "missing" in response.json()["detail"].lower()

    def test_fetch_with_missing_salt(self, httpx_mock):
        """Test error handling for token missing salt field."""
        key = Fernet.generate_key().decode()
        cipher = Fernet(key.encode())
        calendar_url = "https://example.com/calendar.ics"

        httpx_mock.add_response(url=calendar_url, text=VALID_ICS)

        payload = {"url": calendar_url}
        token = cipher.encrypt(json.dumps(payload).encode()).decode()

        with patch.dict(os.environ, {"FERNET_KEY": key}):
            response = client.get(f"/fernet/{token}")

            assert response.status_code == 400
            assert "missing salt" in response.json()["detail"].lower()

    def test_fetch_with_invalid_salt_encoding(self, httpx_mock):
        """Test error handling for token with non-base64 salt."""
        key = Fernet.generate_key().decode()
        cipher = Fernet(key.encode())
        calendar_url = "https://example.com/calendar.ics"

        httpx_mock.add_response(url=calendar_url, text=VALID_ICS)

        payload = {"url": calendar_url, "salt": "!!!not-base64!!!"}
        token = cipher.encrypt(json.dumps(payload).encode()).decode()

        with patch.dict(os.environ, {"FERNET_KEY": key}):
            response = client.get(f"/fernet/{token}")

            assert response.status_code == 400
            assert "salt" in response.json()["detail"].lower()

    def test_fetch_with_wrong_salt_length(self, httpx_mock):
        """Test error handling for token with salt of incorrect length."""
        key = Fernet.generate_key().decode()
        cipher = Fernet(key.encode())
        calendar_url = "https://example.com/calendar.ics"

        httpx_mock.add_response(url=calendar_url, text=VALID_ICS)

        payload = {
            "url": calendar_url,
            "salt": base64.b64encode(b"short").decode(),
        }
        token = cipher.encrypt(json.dumps(payload).encode()).decode()

        with patch.dict(os.environ, {"FERNET_KEY": key}):
            response = client.get(f"/fernet/{token}")

            assert response.status_code == 400
            assert "salt length" in response.json()["detail"].lower()

    def test_fetch_request_error(self, httpx_mock):
        """Test handling of network-level request errors."""
        key = Fernet.generate_key().decode()
        calendar_url = "https://example.com/unreachable.ics"

        httpx_mock.add_exception(httpx.ConnectError("Connection refused"), url=calendar_url)

        token = _generate_fernet_token(key, calendar_url)

        with patch.dict(os.environ, {"FERNET_KEY": key}):
            response = client.get(f"/fernet/{token}")

            assert response.status_code == 400
            assert "failed to fetch" in response.json()["detail"].lower()

    def test_fetch_success(self, httpx_mock):
        """Test successful fetch and anonymization via Fernet token."""
        key = Fernet.generate_key().decode()
        calendar_url = "https://example.com/calendar.ics"

        # Mock the external calendar URL
        httpx_mock.add_response(url=calendar_url, text=VALID_ICS)

        # Generate token and fetch
        token = _generate_fernet_token(key, calendar_url)

        with patch.dict(os.environ, {"FERNET_KEY": key}):
            fetch_response = client.get(f"/fernet/{token}")

            assert fetch_response.status_code == 200
            assert fetch_response.headers["content-type"] == "text/calendar; charset=utf-8"
            assert "no-cache" in fetch_response.headers["cache-control"]

            # Verify content is anonymized
            content = fetch_response.content.decode("utf-8")
            assert "BEGIN:VCALENDAR" in content
            assert "Test Event" not in content
            assert "Test description" not in content
            assert "20250101T100000Z" in content

    def test_fetch_applies_field_modes(self, httpx_mock):
        """Field modes encoded in the token are applied on fetch."""
        key = Fernet.generate_key().decode()
        calendar_url = "https://example.com/calendar.ics"

        httpx_mock.add_response(url=calendar_url, text=VALID_ICS)

        cipher = Fernet(key.encode())
        payload = {
            "url": calendar_url,
            "salt": base64.b64encode(b"\x00" * 32).decode(),
            "field_modes": {"SUMMARY": "keep", "DESCRIPTION": "remove"},
        }
        token = cipher.encrypt(json.dumps(payload).encode()).decode()

        with patch.dict(os.environ, {"FERNET_KEY": key}):
            response = client.get(f"/fernet/{token}")

            assert response.status_code == 200
            content = response.content.decode("utf-8")

            assert "Test Event" in content
            assert "Test description" not in content
            assert "DESCRIPTION:" not in content

    def test_fetch_with_redirect(self, httpx_mock):
        """Test fetch follows redirects and validates final URL."""
        key = Fernet.generate_key().decode()
        original_url = "https://example.com/calendar"
        final_url = "https://example.com/calendar.ics"

        # Mock redirect
        httpx_mock.add_response(url=original_url, status_code=302, headers={"Location": final_url})
        httpx_mock.add_response(url=final_url, text=VALID_ICS)

        token = _generate_fernet_token(key, original_url)

        with patch.dict(os.environ, {"FERNET_KEY": key}):
            fetch_response = client.get(f"/fernet/{token}")

            assert fetch_response.status_code == 200
            content = fetch_response.content.decode("utf-8")
            assert "BEGIN:VCALENDAR" in content

    def test_fetch_redirect_to_private_ip_blocked(self, httpx_mock):
        """Test that redirects to private IPs are blocked by the event hook."""
        key = Fernet.generate_key().decode()
        original_url = "https://example.com/redirect"
        private_url = "http://127.0.0.1/calendar.ics"

        httpx_mock.add_response(
            url=original_url, status_code=302, headers={"Location": private_url}
        )

        token = _generate_fernet_token(key, original_url)

        with patch.dict(os.environ, {"FERNET_KEY": key}):
            response = client.get(f"/fernet/{token}")

            assert response.status_code == 400
            assert "private" in response.json()["detail"].lower()

    def test_fetch_timeout(self, httpx_mock):
        """Test timeout handling when fetching calendar."""
        key = Fernet.generate_key().decode()
        calendar_url = "https://example.com/slow-calendar.ics"

        # Mock timeout
        httpx_mock.add_exception(httpx.TimeoutException("Timeout"), url=calendar_url)

        token = _generate_fernet_token(key, calendar_url)

        with patch.dict(os.environ, {"FERNET_KEY": key}):
            fetch_response = client.get(f"/fernet/{token}")

            assert fetch_response.status_code == 408
            assert "timeout" in fetch_response.json()["detail"].lower()

    def test_fetch_http_error(self, httpx_mock):
        """Test handling of HTTP errors when fetching calendar."""
        key = Fernet.generate_key().decode()
        calendar_url = "https://example.com/missing.ics"

        # Mock 404
        httpx_mock.add_response(url=calendar_url, status_code=404)

        token = _generate_fernet_token(key, calendar_url)

        with patch.dict(os.environ, {"FERNET_KEY": key}):
            fetch_response = client.get(f"/fernet/{token}")

            assert fetch_response.status_code == 404

    def test_fetch_empty_response(self, httpx_mock):
        """Test error handling for empty calendar content."""
        key = Fernet.generate_key().decode()
        calendar_url = "https://example.com/empty.ics"

        # Mock empty response
        httpx_mock.add_response(url=calendar_url, content=b"")

        token = _generate_fernet_token(key, calendar_url)

        with patch.dict(os.environ, {"FERNET_KEY": key}):
            fetch_response = client.get(f"/fernet/{token}")

            assert fetch_response.status_code == 400
            assert "empty" in fetch_response.json()["detail"].lower()

    def test_fetch_invalid_ics(self, httpx_mock):
        """Test error handling for invalid ICS content."""
        key = Fernet.generate_key().decode()
        calendar_url = "https://example.com/invalid.ics"

        # Mock invalid ICS
        httpx_mock.add_response(url=calendar_url, content=b"Not a valid ICS file")

        token = _generate_fernet_token(key, calendar_url)

        with patch.dict(os.environ, {"FERNET_KEY": key}):
            fetch_response = client.get(f"/fernet/{token}")

            assert fetch_response.status_code == 400
            assert "invalid" in fetch_response.json()["detail"].lower()

    def test_fetch_size_limit(self, httpx_mock):
        """Test that oversized responses are rejected."""
        key = Fernet.generate_key().decode()
        calendar_url = "https://example.com/huge.ics"

        # Mock huge response (11MB, exceeds 10MB limit)
        huge_content = b"x" * (11 * 1024 * 1024)
        httpx_mock.add_response(url=calendar_url, content=huge_content)

        token = _generate_fernet_token(key, calendar_url)

        with patch.dict(os.environ, {"FERNET_KEY": key}):
            fetch_response = client.get(f"/fernet/{token}")

            assert fetch_response.status_code == 413
            assert "too large" in fetch_response.json()["detail"].lower()

    def test_fernet_generates_unique_salts(self):
        """Test that each token has a unique salt."""
        key = Fernet.generate_key().decode()

        with patch.dict(os.environ, {"FERNET_KEY": key}):
            # Generate two tokens for the same URL
            response1 = client.post(
                "/fernet-generate", json={"url": "https://example.com/calendar.ics"}
            )
            response2 = client.post(
                "/fernet-generate", json={"url": "https://example.com/calendar.ics"}
            )

            token1 = _extract_token_from_url(response1.json()["url"])
            token2 = _extract_token_from_url(response2.json()["url"])

            # Tokens should be different (different salts)
            assert token1 != token2

            # Decrypt both to verify salts are different
            cipher = Fernet(key.encode())
            payload1 = json.loads(cipher.decrypt(token1.encode()).decode())
            payload2 = json.loads(cipher.decrypt(token2.encode()).decode())

            assert payload1["salt"] != payload2["salt"]
