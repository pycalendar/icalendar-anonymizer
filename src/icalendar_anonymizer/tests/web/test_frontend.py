# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Tests for frontend static file serving and integration."""

import io

from fastapi.testclient import TestClient

from icalendar_anonymizer.webapp.main import app

client = TestClient(app)


class TestStaticFiles:
    """Tests for static file serving."""

    def test_root_serves_html(self):
        """Test root endpoint serves index.html."""
        response = client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "<!DOCTYPE html>" in response.text
        assert "iCalendar Anonymizer" in response.text

    def test_css_file_served(self):
        """Test CSS file is accessible."""
        response = client.get("/static/style.css")

        assert response.status_code == 200
        assert "text/css" in response.headers["content-type"]
        assert "SPDX-FileCopyrightText" in response.text

    def test_js_file_served(self):
        """Test JavaScript file is accessible."""
        response = client.get("/static/app.js")

        assert response.status_code == 200
        # FastAPI may return different content-types for JS
        assert (
            "javascript" in response.headers["content-type"]
            or "application/javascript" in response.headers["content-type"]
            or "text/javascript" in response.headers["content-type"]
        )
        assert "SPDX-FileCopyrightText" in response.text

    def test_nonexistent_static_file(self):
        """Test 404 for nonexistent static files."""
        response = client.get("/static/nonexistent.txt")

        assert response.status_code == 404


class TestFrontendIntegration:
    """Tests for frontend-backend integration."""

    def test_html_contains_api_endpoints(self):
        """Test HTML references correct API endpoints."""
        response = client.get("/")
        html = response.text

        # Check that HTML form action references the upload endpoint
        assert 'action="/upload"' in html

        # Check that JavaScript file is loaded (which contains API calls)
        assert "/static/app.js" in html

    def test_html_contains_required_forms(self):
        """Test HTML contains necessary form elements."""
        response = client.get("/")
        html = response.text

        # Check for form elements
        assert 'type="file"' in html
        assert "<textarea" in html
        assert 'type="url"' in html or 'id="url-input"' in html

    def test_html_has_accessibility_features(self):
        """Test HTML includes accessibility attributes."""
        response = client.get("/")
        html = response.text

        # Check ARIA attributes and semantic HTML
        assert "aria-label" in html
        assert "<noscript>" in html
        assert "<header>" in html
        assert "<main>" in html
        assert "<footer>" in html

    def test_html_loads_css_and_js(self):
        """Test HTML references CSS and JS files."""
        response = client.get("/")
        html = response.text

        assert "/static/style.css" in html
        assert "/static/app.js" in html

    def test_html_has_tab_structure(self):
        """Test HTML contains tab-based interface."""
        response = client.get("/")
        html = response.text

        # Check for tab navigation
        assert 'role="tablist"' in html
        assert 'role="tab"' in html
        assert 'role="tabpanel"' in html

        # Check for three tabs
        assert 'id="upload-tab"' in html
        assert 'id="paste-tab"' in html
        assert 'id="fetch-tab"' in html

        # Check for three panels
        assert 'id="upload-panel"' in html
        assert 'id="paste-panel"' in html
        assert 'id="fetch-panel"' in html


class TestNoJSFallback:
    """Tests for progressive enhancement without JavaScript."""

    def test_form_submission_without_js(self):
        """Test form can submit directly to backend without JS."""
        # This simulates browser form submission with JS disabled
        # The existing /upload endpoint should handle this
        valid_ics = b"""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Test
END:VEVENT
END:VCALENDAR"""

        files = {"file": ("test.ics", io.BytesIO(valid_ics), "text/calendar")}
        response = client.post("/upload", files=files)

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/calendar; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
