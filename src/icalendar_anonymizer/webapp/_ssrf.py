# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""SSRF protection with DNS rebinding resistance for URL fetching endpoints.

Validating a URL's hostname and then letting the HTTP client resolve DNS
itself leaves a gap between the check and the connection. An attacker's
DNS name can resolve to a public IP when validated and a private one
(such as a cloud metadata endpoint) by the time the client actually
connects. This module closes that gap: it resolves each hostname once,
validates every address that comes back, and pins the connection to one
of them through a custom transport. DNS is never resolved a second time
after validation.
"""

import asyncio
import ipaddress
import socket

import httpcore
import httpx
from fastapi import HTTPException

MAX_REDIRECTS = 10


def is_private_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check if an IP address is not safe to connect to for an outbound fetch.

    An address is allowed only if it's globally routable and not
    multicast. `ip.is_global` alone still allows multicast addresses,
    which can't answer as an HTTP peer anyway. This also blocks loopback,
    private, link-local, unspecified, CGNAT, reserved, and benchmarking
    ranges, without maintaining our own list of blocked ranges.

    An IPv4-mapped IPv6 address such as ``::ffff:127.0.0.1`` is checked
    against its mapped IPv4 address, since `is_global` on the IPv6 form
    doesn't see through the mapping.

    Args:
        ip: The address to check

    Returns:
        True if the address is not safe to connect to
    """
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return not ip.is_global or ip.is_multicast


def validate_url_shape(url: str) -> str:
    """Validate a URL's scheme and literal hostname before any DNS lookup.

    Args:
        url: URL to validate

    Returns:
        The URL's hostname

    Raises:
        HTTPException: If the URL is invalid or blocked for security reasons
    """
    try:
        parsed = httpx.URL(url)
    except httpx.InvalidURL as e:
        raise HTTPException(status_code=400, detail=f"Invalid URL: {e}") from e

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid URL scheme: {parsed.scheme}. Only http:// and https:// allowed",
        )

    if parsed.userinfo:
        # Credentials are supplied separately via the auth parameter, never
        # embedded in the URL. This also closes a same-origin loophole: a
        # redirect target like https://mallory@example.com/b has the same
        # (scheme, host, port) as the original request, so it would
        # otherwise still receive our real Authorization header.
        raise HTTPException(
            status_code=400, detail="URLs with embedded credentials are not allowed"
        )

    hostname = parsed.host
    if not hostname:
        raise HTTPException(status_code=400, detail="Invalid URL: missing hostname")

    if hostname.lower() in ("localhost", "0.0.0.0"):  # noqa: S104
        raise HTTPException(status_code=400, detail="Access to localhost is not allowed")

    try:
        literal_ip = ipaddress.ip_address(hostname)
    except ValueError:
        # Not a literal IP. resolve_hostname() and pick_validated_ip()
        # handle DNS resolution and validation before any connection.
        return hostname

    if is_private_ip(literal_ip):
        raise HTTPException(
            status_code=400, detail=f"Access to private IP {hostname} is not allowed"
        )

    return hostname


async def resolve_hostname(hostname: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """Resolve a hostname to every address it currently maps to.

    Both IPv4 and IPv6 results are returned so callers can validate the
    full address set. An attacker's DNS response could mix one safe
    address with one unsafe one.

    Args:
        hostname: The hostname to resolve

    Returns:
        Deduplicated list of resolved addresses

    Raises:
        HTTPException: If the hostname cannot be resolved
    """
    loop = asyncio.get_running_loop()
    try:
        results = await loop.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except OSError as e:
        raise HTTPException(
            status_code=400, detail=f"Could not resolve hostname {hostname!r}: {e}"
        ) from e

    addresses = []
    for family, _, _, _, sockaddr in results:
        if family not in (socket.AF_INET, socket.AF_INET6):
            continue
        address = ipaddress.ip_address(sockaddr[0])
        if address not in addresses:
            addresses.append(address)

    if not addresses:
        raise HTTPException(status_code=400, detail=f"Could not resolve hostname {hostname!r}")

    return addresses


async def pick_validated_ip(hostname: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    """Resolve a hostname and return one address, failing closed on any unsafe result.

    Every resolved address must be safe, not just the one returned. An
    attacker offering a mixed record set shouldn't be able to retry into
    the unsafe address on a later connection.

    Args:
        hostname: The hostname to resolve and validate

    Returns:
        A validated address for `hostname` (IPv4 preferred when both
        families resolve)

    Raises:
        HTTPException: If any resolved address is private/loopback/link-local
    """
    addresses = await resolve_hostname(hostname)

    for address in addresses:
        if is_private_ip(address):
            raise HTTPException(
                status_code=400, detail=f"Access to private IP {address} is not allowed"
            )

    for address in addresses:
        if isinstance(address, ipaddress.IPv4Address):
            return address
    return addresses[0]


class _PinnedNetworkBackend(httpcore.AnyIOBackend):
    """Network backend that dials a fixed IP regardless of the requested host."""

    def __init__(self, pinned_ip: str) -> None:
        super().__init__()
        self._pinned_ip = pinned_ip

    async def connect_tcp(self, host, port, **kwargs):  # noqa: ARG002
        """Connect to the pinned IP instead of `host`.

        `host` is discarded for the connection itself. httpcore separately
        uses the original request's hostname for TLS SNI and certificate
        validation, so this doesn't weaken certificate checking.
        """
        return await super().connect_tcp(self._pinned_ip, port, **kwargs)


class _PinnedTransport(httpx.AsyncHTTPTransport):
    """HTTP transport that connects only to a pre-validated, pinned IP.

    `httpx.AsyncHTTPTransport.__init__` doesn't accept a `network_backend`
    parameter, it always builds its own `httpcore.AsyncConnectionPool`
    with a default backend. This subclass lets the parent constructor
    build that pool as normal, then swaps only the pool's network backend
    for the pinning one, keeping every other setting the caller passed.

    It doesn't override `handle_async_request`, which is inherited
    unchanged and only delegates to `self._pool`. That means test suites
    which patch `httpx.AsyncHTTPTransport.handle_async_request`, such as
    pytest-httpx, keep intercepting requests exactly as they do for the
    default transport. The pinning logic never runs against a mocked
    transport.
    """

    def __init__(self, pinned_ip: str, **kwargs: object) -> None:
        super().__init__(**kwargs)
        if not hasattr(self._pool, "_network_backend"):
            raise RuntimeError(
                "httpcore.AsyncConnectionPool no longer exposes _network_backend; "
                "_PinnedTransport needs updating for this httpcore version"
            )
        self._pool._network_backend = _PinnedNetworkBackend(pinned_ip)  # noqa: SLF001


def _origin(url: str) -> tuple[str, str | None, int | None]:
    """Return a URL's (scheme, host, port) for same-origin comparisons.

    `httpx.URL.port` normalizes default ports to `None`, so
    `https://example.com` and `https://example.com:443` compare equal.

    Args:
        url: The URL to extract the origin from

    Returns:
        A (scheme, host, port) tuple
    """
    parsed = httpx.URL(url)
    return (parsed.scheme, parsed.host, parsed.port)


async def fetch_with_pinned_redirects(
    url: str,
    *,
    timeout: float,  # noqa: ASYNC109 -- passed through to httpx.AsyncClient, not a cancellation scope
    max_response_size: int,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Fetch a URL, resolving and pinning DNS fresh for every redirect hop.

    Each hop is validated and resolved independently, and the resolved
    address is pinned for that hop's connection. DNS is never resolved
    again between validation and connection.

    Args:
        url: The URL to fetch
        timeout: Per-request timeout in seconds
        max_response_size: Maximum allowed response body size in bytes
        headers: Optional extra headers (for example, a caller-built
            `Authorization` header). Only sent to the original request's
            origin - dropped on any redirect to a different scheme, host,
            or port, since this module has no way to know whether a header
            is safe to forward to a different origin.

    Returns:
        The final, non-redirect response

    Raises:
        HTTPException: If a hop is blocked, redirects exceed the limit, or
            the response exceeds `max_response_size`
        httpx.HTTPStatusError: Propagated from the underlying request
        httpx.TimeoutException: Propagated from the underlying request
        httpx.RequestError: Propagated from the underlying request
    """
    current_url = url
    original_origin = None

    for _ in range(MAX_REDIRECTS):
        hostname = validate_url_shape(current_url)
        pinned_ip = await pick_validated_ip(hostname)

        current_origin = _origin(current_url)
        if original_origin is None:
            original_origin = current_origin

        request_headers = headers if headers and current_origin == original_origin else None

        transport = _PinnedTransport(pinned_ip=str(pinned_ip))
        async with httpx.AsyncClient(
            transport=transport, follow_redirects=False, timeout=timeout
        ) as client:
            response = await client.get(current_url, headers=request_headers)

        if response.is_redirect:
            location = response.headers.get("location")
            if not location:
                raise HTTPException(
                    status_code=400, detail="Redirect response missing Location header"
                )
            try:
                current_url = str(httpx.URL(current_url).join(location))
            except httpx.InvalidURL as e:
                raise HTTPException(status_code=400, detail=f"Invalid redirect target: {e}") from e
            continue

        if len(response.content) > max_response_size:
            raise HTTPException(
                status_code=413,
                detail=f"Response too large (max {max_response_size} bytes)",
            )

        return response

    raise HTTPException(status_code=400, detail="Too many redirects")
