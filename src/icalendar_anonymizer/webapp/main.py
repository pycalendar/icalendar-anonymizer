# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""FastAPI web service for iCalendar anonymization.

Provides REST API endpoints for anonymizing iCalendar files through JSON input,
file upload, and URL fetching with SSRF protection.
"""

import ipaddress
import os
from typing import Annotated
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from icalendar import Calendar
from pydantic import BaseModel

from icalendar_anonymizer import anonymize
from icalendar_anonymizer.version import version

# Constants (configurable via environment variables)
try:
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE") or 10 * 1024 * 1024)  # Default 10MB
except ValueError as e:
    raise ValueError(
        f"MAX_FILE_SIZE must be a valid integer, got: {os.getenv('MAX_FILE_SIZE')!r}"
    ) from e
FETCH_TIMEOUT = 10.0  # seconds
MAX_RESPONSE_SIZE = MAX_FILE_SIZE  # Match file size limit

# Private IP ranges to block for SSRF protection
PRIVATE_IP_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("10.0.0.0/8"),  # Private
    ipaddress.ip_network("172.16.0.0/12"),  # Private
    ipaddress.ip_network("192.168.0.0/16"),  # Private
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),  # IPv6 private
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
]

app = FastAPI(
    title="iCalendar Anonymizer API",
    description="Anonymize iCalendar files while preserving technical properties",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - tighten in production
    allow_credentials=False,  # Cannot be True with wildcard origins
    allow_methods=["*"],
    allow_headers=["*"],
)

# Note: Static files are served by Cloudflare Workers static assets
# The frontend HTML, CSS, and JS files are configured in wrangler.jsonc


class HealthResponse(BaseModel):
    """Response model for /health endpoint."""

    status: str
    version: str
    r2_enabled: bool


@app.get("/health")
async def health() -> HealthResponse:
    """Health check endpoint for Docker and monitoring.

    Returns:
        HealthResponse: Service health status, version, and feature flags
    """
    return HealthResponse(
        status="healthy",
        version=version,
        r2_enabled=False,  # R2 support not yet implemented
    )


class AnonymizeRequest(BaseModel):
    """Request model for /anonymize endpoint."""

    ics: str


def _is_private_ip(hostname: str) -> bool:
    """Check if hostname string is a private IP address.

    Does not perform DNS resolution. Hostnames will return False and be
    resolved later by httpx.

    Args:
        hostname: Hostname or IP address to check

    Returns:
        True if hostname is private/blocked, False otherwise
    """
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        # Not a valid IP, likely a hostname - will be resolved by httpx
        return False

    return any(ip in network for network in PRIVATE_IP_RANGES)


def _validate_url(url: str) -> None:
    """Validate URL for SSRF protection.

    Args:
        url: URL to validate

    Raises:
        HTTPException: If URL is invalid or blocked for security reasons
    """
    parsed = urlparse(url)

    # Only allow http and https schemes
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid URL scheme: {parsed.scheme}. Only http:// and https:// allowed",
        )

    # Check if hostname is localhost or private IP
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="Invalid URL: missing hostname")

    # Block localhost variations
    if hostname.lower() in ("localhost", "0.0.0.0"):  # noqa: S104
        raise HTTPException(status_code=400, detail="Access to localhost is not allowed")

    # Block private IPs
    if _is_private_ip(hostname):
        raise HTTPException(
            status_code=400, detail=f"Access to private IP {hostname} is not allowed"
        )


def _anonymize_calendar(ics_content: str) -> bytes:
    """Anonymize iCalendar content.

    Args:
        ics_content: Raw iCalendar content as string

    Returns:
        Anonymized iCalendar content as bytes

    Raises:
        HTTPException: If ICS content is invalid
    """
    if not ics_content.strip():
        raise HTTPException(status_code=400, detail="Input is empty")

    try:
        cal = Calendar.from_ical(ics_content.encode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid ICS format: {e}") from e

    try:
        anonymized = anonymize(cal)
        return anonymized.to_ical()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Anonymization failed: {e}") from e


@app.post("/anonymize")
async def anonymize_endpoint(request: AnonymizeRequest) -> Response:
    """Anonymize iCalendar content provided as JSON.

    Args:
        request: Request containing ICS content

    Returns:
        Response with anonymized ICS file

    Raises:
        HTTPException: If ICS content is invalid or anonymization fails
    """
    anonymized_ics = _anonymize_calendar(request.ics)

    return Response(
        content=anonymized_ics,
        media_type="text/calendar",
        headers={"Content-Disposition": 'attachment; filename="anonymized.ics"'},
    )


@app.post("/upload")
async def upload_endpoint(file: Annotated[UploadFile, File()]) -> Response:
    """Anonymize uploaded iCalendar file.

    Args:
        file: Uploaded ICS file

    Returns:
        Response with anonymized ICS file

    Raises:
        HTTPException: If file is too large, invalid format, or anonymization fails
    """
    # Read file content with size limit
    content = bytearray()
    bytes_read = 0

    while chunk := await file.read(8192):
        bytes_read += len(chunk)
        if bytes_read > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413, detail=f"File too large (max {MAX_FILE_SIZE} bytes)"
            )
        content.extend(chunk)

    try:
        ics_content = content.decode("utf-8")
    except UnicodeDecodeError as e:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is not valid UTF-8 encoded text",
        ) from e

    anonymized_ics = _anonymize_calendar(ics_content)

    return Response(
        content=anonymized_ics,
        media_type="text/calendar",
        headers={"Content-Disposition": 'attachment; filename="anonymized.ics"'},
    )


@app.get("/fetch")
async def fetch_endpoint(url: str) -> Response:
    """Fetch and anonymize iCalendar from URL.

    Args:
        url: URL to fetch ICS file from

    Returns:
        Response with anonymized ICS file

    Raises:
        HTTPException: If URL is invalid, blocked, unreachable, or content is invalid
    """
    # Validate URL for SSRF protection
    _validate_url(url)

    # Fetch URL with timeout and size limit
    # Note: Known TOCTOU vulnerability with DNS rebinding - see Issue #70
    # URL validation occurs before DNS resolution, attacker could use DNS rebinding
    # to bypass private IP checks. Requires custom DNS resolver to fully mitigate.
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=FETCH_TIMEOUT) as client:
            response = await client.get(url)  # lgtm[py/full-ssrf]

            # Check final URL after redirects
            final_url = str(response.url)
            _validate_url(final_url)

            response.raise_for_status()

            # Check content size
            if len(response.content) > MAX_RESPONSE_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"Response too large (max {MAX_RESPONSE_SIZE} bytes)",
                )

            ics_content = response.text

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code, detail=f"Failed to fetch URL: {e}"
        ) from e
    except httpx.TimeoutException as e:
        raise HTTPException(
            status_code=408, detail=f"Request timeout after {FETCH_TIMEOUT}s"
        ) from e
    except httpx.RequestError as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {e}") from e

    anonymized_ics = _anonymize_calendar(ics_content)

    return Response(
        content=anonymized_ics,
        media_type="text/calendar",
        headers={"Content-Disposition": 'attachment; filename="anonymized.ics"'},
    )
