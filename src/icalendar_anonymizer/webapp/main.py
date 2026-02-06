# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""FastAPI web service for iCalendar anonymization.

Provides REST API endpoints for anonymizing iCalendar files through JSON input,
file upload, and URL fetching with SSRF protection.
"""

import base64
import ipaddress
import json
import os
import secrets
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from icalendar import Calendar
from pydantic import BaseModel

from icalendar_anonymizer import anonymize
from icalendar_anonymizer._config import CONFIGURABLE_FIELDS
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
SALT_SIZE_BYTES = 32  # Size of salt for anonymization (32 bytes = 256 bits)


async def _ensure_cryptography():
    """Ensure cryptography package is available.

    In Cloudflare Workers (Pyodide), we need to load cryptography via micropip
    since it's a Pyodide built-in package, not bundled in python_modules.
    """
    # Check if cryptography is already importable
    try:
        import cryptography  # noqa: F401
    except ImportError:
        # Try to load via micropip if in Pyodide environment
        pass
    else:
        return  # Already available

    # Load via micropip if in Pyodide environment
    if os.getenv("CLOUDFLARE_WORKERS"):
        try:
            import micropip

            await micropip.install("cryptography")
        except ImportError:
            # micropip not available - let the later import fail with clear error
            pass


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


# Shared R2 client for local dev (singleton pattern)
_local_r2_client = None


# R2 client injection middleware
@app.middleware("http")
async def inject_r2_client(request: Request, call_next):
    """Inject R2 client into request state.

    In Cloudflare Workers, uses native R2 bindings from env.
    In local dev, uses shared in-memory MockR2Client.

    Args:
        request: FastAPI request object
        call_next: Next middleware/route handler

    Returns:
        Response from next handler
    """
    global _local_r2_client  # noqa: PLW0603
    r2_client = None

    # Check if running in Cloudflare Workers
    if os.getenv("CLOUDFLARE_WORKERS"):
        # Access env from ASGI scope (passed by worker.py via asgi.fetch)
        # Per Cloudflare docs: env is available directly at scope["env"]
        scope = request.scope
        cloudflare_env = scope.get("env", {})
        if cloudflare_env and hasattr(cloudflare_env, "CALENDAR_SHARE_BUCKET"):
            from icalendar_anonymizer.webapp.r2 import WorkersR2Client

            # env is a JsProxy object, access with attribute notation
            r2_client = WorkersR2Client(cloudflare_env.CALENDAR_SHARE_BUCKET)
    else:
        # Local development: use shared mock instance
        if _local_r2_client is None:
            from icalendar_anonymizer.webapp.r2 import MockR2Client

            _local_r2_client = MockR2Client()
        r2_client = _local_r2_client

    request.state.r2_client = r2_client
    return await call_next(request)


# Static files directory (only used in local dev, not in Cloudflare Workers)
# In Cloudflare Workers, static files are served via Assets, not FastAPI
if not os.getenv("CLOUDFLARE_WORKERS"):
    STATIC_DIR = Path(__file__).parent / "static"

    # Mount static files (for local dev/testing - Cloudflare Workers handles via Assets)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    async def root() -> FileResponse:
        """Serve the frontend HTML page.

        Returns:
            FileResponse: The index.html file
        """
        return FileResponse(STATIC_DIR / "index.html")


class HealthResponse(BaseModel):
    """Response model for /health endpoint."""

    status: str
    version: str
    r2_enabled: bool
    fernet_enabled: bool


class FieldConfig(BaseModel):
    """Per-field anonymization configuration."""

    model_config = {"extra": "forbid"}

    summary: Literal["keep", "remove", "randomize", "replace"] | None = None
    description: Literal["keep", "remove", "randomize", "replace"] | None = None
    location: Literal["keep", "remove", "randomize", "replace"] | None = None
    comment: Literal["keep", "remove", "randomize", "replace"] | None = None
    contact: Literal["keep", "remove", "randomize", "replace"] | None = None
    resources: Literal["keep", "remove", "randomize", "replace"] | None = None
    categories: Literal["keep", "remove", "randomize", "replace"] | None = None
    attendee: Literal["keep", "remove", "randomize", "replace"] | None = None
    organizer: Literal["keep", "remove", "randomize", "replace"] | None = None
    uid: Literal["keep", "randomize", "replace"] | None = None  # No "remove"


@app.get("/health")
async def health(request: Request) -> HealthResponse:
    """Health check endpoint for Docker and monitoring.

    Args:
        request: FastAPI request object (used to check R2 client availability)

    Returns:
        HealthResponse: Service health status, version, and feature flags
    """
    # R2 is only truly enabled in Cloudflare Workers with real R2 bucket
    # Local dev uses MockR2Client which is in-memory and non-persistent
    r2_enabled = bool(os.getenv("CLOUDFLARE_WORKERS"))
    if r2_enabled and hasattr(request.state, "r2_client"):
        r2_enabled = request.state.r2_client is not None

    return HealthResponse(
        status="healthy",
        version=version,
        r2_enabled=r2_enabled,
        fernet_enabled=bool(os.getenv("FERNET_KEY")),
    )


class AnonymizeRequest(BaseModel):
    """Request model for /anonymize endpoint."""

    ics: str
    config: FieldConfig | None = None


def _build_field_modes(config: FieldConfig | None) -> dict[str, str] | None:
    """Convert FieldConfig to field_modes dict.

    Args:
        config: Optional field configuration

    Returns:
        Dict mapping field names to modes, or None if no config
    """
    if not config:
        return None
    modes = {}
    # Iterate over CONFIGURABLE_FIELDS to avoid duplication
    for field in CONFIGURABLE_FIELDS:
        val = getattr(config, field.lower(), None)
        if val:
            modes[field] = val
    return modes or None


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


def _anonymize_calendar(
    ics_content: str,
    field_modes: dict[str, str] | None = None,
    salt: bytes | None = None,
) -> Calendar:
    """Anonymize iCalendar content.

    Args:
        ics_content: Raw iCalendar content as string
        field_modes: Optional dict mapping field names to anonymization modes
        salt: Optional salt for deterministic anonymization

    Returns:
        Anonymized Calendar object

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
        kwargs: dict = {}
        if field_modes is not None:
            kwargs["field_modes"] = field_modes
        if salt is not None:
            kwargs["salt"] = salt
        return anonymize(cal, **kwargs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Anonymization failed: {e}") from e


async def _anonymize_from_upload(
    file: UploadFile, field_modes: dict[str, str] | None = None
) -> Calendar:
    """Read and anonymize uploaded iCalendar file.

    Args:
        file: Uploaded ICS file
        field_modes: Optional dict mapping field names to anonymization modes

    Returns:
        Anonymized Calendar object

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

    return _anonymize_calendar(ics_content, field_modes=field_modes)


@app.post("/anonymize")
async def anonymize_endpoint(request: AnonymizeRequest) -> Response:
    """Anonymize iCalendar content provided as JSON.

    Args:
        request: Request containing ICS content and optional field configuration

    Returns:
        Response with anonymized ICS file

    Raises:
        HTTPException: If ICS content is invalid or anonymization fails
    """
    field_modes = _build_field_modes(request.config)
    anonymized_cal = _anonymize_calendar(request.ics, field_modes=field_modes)

    return Response(
        content=anonymized_cal.to_ical(),
        media_type="text/calendar",
        headers={"Content-Disposition": 'attachment; filename="anonymized.ics"'},
    )


@app.api_route("/anonymized", methods=["GET", "POST"])
async def anonymized_endpoint(
    request: Request,
    ics: str | None = Query(
        default=None,
        description="ICS content as query parameter for GET requests; ignored for POST requests",
    ),
) -> Response:
    """Anonymize iCalendar content via curl-friendly interface.

    Supports two methods for easy scripting and testing:
    - GET with query param: curl "http://server/anonymized?ics=BEGIN:VCALENDAR..."
    - POST with raw body: curl -X POST --data-binary @file.ics http://server/anonymized

    Args:
        request: FastAPI request object
        ics: ICS content as query parameter for GET requests; ignored for POST

    Returns:
        Anonymized ICS with text/calendar content type (no Content-Disposition)

    Raises:
        HTTPException: If no content provided or invalid ICS
    """
    if request.method == "GET":
        if not ics:
            raise HTTPException(status_code=400, detail="Missing 'ics' query parameter")
        content = ics
    else:  # POST
        body = await request.body()
        if not body:
            raise HTTPException(status_code=400, detail="Empty request body")
        try:
            content = body.decode("utf-8")
        except UnicodeDecodeError as e:
            raise HTTPException(status_code=400, detail="Invalid UTF-8 encoding") from e

    anonymized_cal = _anonymize_calendar(content)

    return Response(
        content=anonymized_cal.to_ical(),
        media_type="text/calendar",
        # No Content-Disposition header - allows piping output directly
    )


@app.post("/upload")
async def upload_endpoint(
    file: Annotated[UploadFile, File()],
    config: Annotated[str | None, Form()] = None,
) -> Response:
    """Anonymize uploaded iCalendar file.

    Args:
        file: Uploaded ICS file
        config: Optional JSON string with field configuration

    Returns:
        Response with anonymized ICS file

    Raises:
        HTTPException: If file is too large, invalid format, or anonymization fails
    """
    field_modes = None
    if config:
        try:
            parsed = FieldConfig.model_validate_json(config)
            field_modes = _build_field_modes(parsed)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid config: {e}") from e

    anonymized_cal = await _anonymize_from_upload(file, field_modes=field_modes)

    return Response(
        content=anonymized_cal.to_ical(),
        media_type="text/calendar",
        headers={"Content-Disposition": 'attachment; filename="anonymized.ics"'},
    )


@app.get("/fetch")
async def fetch_endpoint(
    url: str,
    summary: Literal["keep", "remove", "randomize", "replace"] | None = None,
    description: Literal["keep", "remove", "randomize", "replace"] | None = None,
    location: Literal["keep", "remove", "randomize", "replace"] | None = None,
    comment: Literal["keep", "remove", "randomize", "replace"] | None = None,
    contact: Literal["keep", "remove", "randomize", "replace"] | None = None,
    resources: Literal["keep", "remove", "randomize", "replace"] | None = None,
    categories: Literal["keep", "remove", "randomize", "replace"] | None = None,
    attendee: Literal["keep", "remove", "randomize", "replace"] | None = None,
    organizer: Literal["keep", "remove", "randomize", "replace"] | None = None,
    uid: Literal["keep", "randomize", "replace"] | None = None,
) -> Response:
    """Fetch and anonymize iCalendar from URL.

    Args:
        url: URL to fetch ICS file from
        summary: Mode for SUMMARY field
        description: Mode for DESCRIPTION field
        location: Mode for LOCATION field
        comment: Mode for COMMENT field
        contact: Mode for CONTACT field
        resources: Mode for RESOURCES field
        categories: Mode for CATEGORIES field
        attendee: Mode for ATTENDEE field
        organizer: Mode for ORGANIZER field
        uid: Mode for UID field (remove not allowed)

    Returns:
        Response with anonymized ICS file

    Raises:
        HTTPException: If URL is invalid, blocked, unreachable, or content is invalid
    """
    # Build field_modes from query params
    field_modes = {}
    params = {
        "SUMMARY": summary,
        "DESCRIPTION": description,
        "LOCATION": location,
        "COMMENT": comment,
        "CONTACT": contact,
        "RESOURCES": resources,
        "CATEGORIES": categories,
        "ATTENDEE": attendee,
        "ORGANIZER": organizer,
        "UID": uid,
    }
    field_modes = {field: val for field, val in params.items() if val}

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

    anonymized_cal = _anonymize_calendar(ics_content, field_modes=field_modes or None)

    return Response(
        content=anonymized_cal.to_ical(),
        media_type="text/calendar",
        headers={"Content-Disposition": 'attachment; filename="anonymized.ics"'},
    )


class ShareResponse(BaseModel):
    """Response model for /share endpoint."""

    url: str


class FernetGenerateRequest(BaseModel):
    """Request model for /fernet-generate endpoint."""

    url: str


class FernetShareResponse(BaseModel):
    """Response model for /fernet-generate endpoint."""

    url: str


@app.post("/share")
async def share_calendar(
    request: Request,
    file: Annotated[UploadFile, File()],
    config: Annotated[str | None, Form()] = None,
) -> ShareResponse:
    """Anonymize calendar and generate shareable link.

    Anonymizes the uploaded calendar file and stores it in R2 storage,
    returning a shareable URL with 30-day expiry.

    Args:
        request: FastAPI request object (provides R2 client)
        file: Uploaded ICS file
        config: Optional JSON string with field configuration

    Returns:
        ShareResponse with shareable URL

    Raises:
        HTTPException: If R2 unavailable, file invalid, or storage fails
    """
    # Check R2 availability
    if not hasattr(request.state, "r2_client") or request.state.r2_client is None:
        raise HTTPException(
            status_code=503,
            detail="Shareable links are not available",
        )

    # Parse config if provided
    field_modes = None
    if config:
        try:
            parsed = FieldConfig.model_validate_json(config)
            field_modes = _build_field_modes(parsed)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid config: {e}") from e

    # Validate and anonymize
    anonymized_cal = await _anonymize_from_upload(file, field_modes=field_modes)

    # Generate unique ID and store
    from icalendar_anonymizer.webapp.r2 import generate_unique_id

    share_id = await generate_unique_id(request.state.r2_client)
    await request.state.r2_client.put(share_id, anonymized_cal.to_ical())

    # Return shareable URL
    base_url = str(request.base_url).rstrip("/")
    share_url = f"{base_url}/s/{share_id}"

    return ShareResponse(url=share_url)


@app.get("/s/{share_id}")
async def get_shared_calendar(
    request: Request,
    share_id: str,
) -> Response:
    """Retrieve shared calendar file.

    Args:
        request: FastAPI request object (provides R2 client)
        share_id: 8-character share ID

    Returns:
        Response with calendar file

    Raises:
        HTTPException: If R2 unavailable, ID invalid, or file not found
    """
    # Check R2 availability
    if not hasattr(request.state, "r2_client") or request.state.r2_client is None:
        raise HTTPException(
            status_code=503,
            detail="Shareable links are not available",
        )

    # Validate ID format (8 chars, URL-safe)
    if len(share_id) != 8 or not share_id.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid share ID")

    # Retrieve from R2
    data = await request.state.r2_client.get(share_id)
    if data is None:
        raise HTTPException(
            status_code=404,
            detail="Shared calendar not found or expired",
        )

    # Return with caching headers
    return Response(
        content=data,
        media_type="text/calendar",
        headers={
            "Content-Disposition": f'attachment; filename="calendar-{share_id}.ics"',
            "Cache-Control": "public, max-age=86400",  # 24-hour CDN cache
        },
    )


@app.post("/fernet-generate")
async def generate_fernet_token(
    request: Request,
    body: FernetGenerateRequest,
) -> FernetShareResponse:
    """Generate encrypted token for live calendar proxy.

    Encrypts the source calendar URL and a random salt into a Fernet token.
    The token can be used with /fernet/{token} to fetch and anonymize
    the calendar on-the-fly.

    Args:
        request: FastAPI request object
        body: Request containing calendar URL

    Returns:
        FernetShareResponse with shareable URL

    Raises:
        HTTPException: If Fernet not configured or URL invalid
    """
    await _ensure_cryptography()
    from cryptography.fernet import Fernet

    fernet_key = os.getenv("FERNET_KEY")
    if not fernet_key:
        raise HTTPException(
            status_code=503,
            detail="Encrypted sharing is not configured",
        )

    # Validate URL for SSRF protection
    _validate_url(body.url)

    # Create payload with URL and random salt
    payload = {
        "url": body.url,
        "salt": base64.b64encode(secrets.token_bytes(SALT_SIZE_BYTES)).decode(),
    }

    # Encrypt payload
    cipher = Fernet(fernet_key.encode())
    token = cipher.encrypt(json.dumps(payload).encode()).decode()

    # Build shareable URL
    base_url = str(request.base_url).rstrip("/")
    share_url = f"{base_url}/fernet/{token}"

    return FernetShareResponse(url=share_url)


@app.get("/fernet/{token}")
async def fernet_fetch(token: str) -> Response:
    """Fetch and anonymize calendar using encrypted token.

    Decrypts the Fernet token to retrieve the source URL and salt,
    fetches the calendar, anonymizes it with the stored salt, and returns it.

    This provides live calendar proxying - the source is fetched each time,
    ensuring the anonymized calendar stays up-to-date.

    Args:
        token: Fernet-encrypted token containing URL and salt

    Returns:
        Response with anonymized calendar

    Raises:
        HTTPException: If Fernet not configured, token invalid, or fetch fails
    """
    await _ensure_cryptography()
    from cryptography.fernet import Fernet, InvalidToken

    fernet_key = os.getenv("FERNET_KEY")
    if not fernet_key:
        raise HTTPException(
            status_code=503,
            detail="Encrypted sharing is not configured",
        )

    # Decrypt token
    cipher = Fernet(fernet_key.encode())
    try:
        decrypted = cipher.decrypt(token.encode())
        payload = json.loads(decrypted.decode())
    except InvalidToken:
        raise HTTPException(status_code=400, detail="Invalid token") from None
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Malformed token payload") from None

    # Validate URL (defense in depth - Fernet authenticates payload preventing tampering)
    url = payload.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Token missing URL")

    _validate_url(url)

    # Fetch calendar from source
    try:
        # Validate redirect targets for SSRF protection (defense in depth)
        async def validate_redirect(request: httpx.Request) -> None:
            """Validate redirect URLs for SSRF protection (defense in depth)."""
            _validate_url(str(request.url))

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=FETCH_TIMEOUT,
            event_hooks={"request": [validate_redirect]},
        ) as client:
            response = await client.get(url)
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
            status_code=e.response.status_code,
            detail=f"Failed to fetch calendar: {e}",
        ) from e
    except httpx.TimeoutException as e:
        raise HTTPException(
            status_code=408,
            detail=f"Request timeout after {FETCH_TIMEOUT}s",
        ) from e
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch calendar: {e}",
        ) from e

    # Validate and decode salt
    salt_b64 = payload.get("salt")
    if not salt_b64:
        raise HTTPException(status_code=400, detail="Token missing salt")

    try:
        salt = base64.b64decode(salt_b64)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid salt encoding") from e

    if len(salt) != SALT_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid salt length (expected {SALT_SIZE_BYTES} bytes)",
        )

    anonymized_cal = _anonymize_calendar(ics_content, salt=salt)

    return Response(
        content=anonymized_cal.to_ical(),
        media_type="text/calendar",
        headers={
            "Content-Disposition": 'attachment; filename="anonymized.ics"',
            # No caching - live data should be fresh
            "Cache-Control": "no-cache",
        },
    )
