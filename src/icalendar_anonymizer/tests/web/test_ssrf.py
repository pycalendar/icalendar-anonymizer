# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Tests for SSRF protection with DNS-rebinding resistance."""

import ipaddress
import socket
from unittest.mock import AsyncMock

import httpcore
import httpx
import pytest
from fastapi import HTTPException

from icalendar_anonymizer.webapp import _ssrf

# Captured before the autouse _stub_dns_resolution fixture (see conftest.py)
# replaces _ssrf.resolve_hostname, so these tests can exercise the real
# implementation directly.
_real_resolve_hostname = _ssrf.resolve_hostname

# Real, globally routable addresses for tests that exercise is_private_ip's
# allowlist check. Unlike RFC 5737/3849 documentation ranges, these must
# actually be public or pick_validated_ip rejects them.
_PUBLIC_IPV4 = ipaddress.ip_address("93.184.216.34")  # example.com
_PUBLIC_IPV6 = ipaddress.ip_address("2001:4860:4860::8888")  # Google Public DNS


class TestIsPrivateIp:
    """Tests for is_private_ip()."""

    @pytest.mark.parametrize(
        "address",
        [
            "127.0.0.1",  # loopback
            "10.0.0.1",  # private
            "172.16.0.1",  # private
            "192.168.1.1",  # private
            "169.254.0.1",  # link-local
            "0.0.0.0",  # unspecified  # noqa: S104
            "100.64.0.1",  # shared/CGNAT
            "240.0.0.1",  # reserved
            "198.18.0.1",  # benchmarking
            "224.0.0.1",  # multicast (is_global is True, but not connectable)
            "::1",  # IPv6 loopback
            "fc00::1",  # IPv6 private
            "fe80::1",  # IPv6 link-local
            "::",  # IPv6 unspecified
            "ff02::1",  # IPv6 multicast
        ],
    )
    def test_blocked_ranges_are_private(self, address):
        assert _ssrf.is_private_ip(ipaddress.ip_address(address)) is True

    @pytest.mark.parametrize("address", ["8.8.8.8", "93.184.216.34", "2001:4860:4860::8888"])
    def test_public_addresses_are_not_private(self, address):
        assert _ssrf.is_private_ip(ipaddress.ip_address(address)) is False

    @pytest.mark.parametrize(
        "address",
        ["::ffff:127.0.0.1", "::ffff:10.0.0.1", "::ffff:169.254.169.254"],
    )
    def test_ipv4_mapped_private_addresses_are_private(self, address):
        # An IPv4-mapped IPv6 address (RFC 4291 ::ffff:0:0/96) targets the
        # mapped IPv4 host. is_global on the IPv6 form doesn't see through
        # the mapping, so it has to be unwrapped before checking.
        assert _ssrf.is_private_ip(ipaddress.ip_address(address)) is True

    def test_ipv4_mapped_public_address_is_not_private(self):
        assert _ssrf.is_private_ip(ipaddress.ip_address("::ffff:8.8.8.8")) is False


class TestValidateUrlShape:
    """Tests for validate_url_shape()."""

    def test_returns_hostname_for_valid_url(self):
        assert _ssrf.validate_url_shape("https://example.com/cal.ics") == "example.com"

    @pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com/x", "data:text/x,y"])
    def test_rejects_invalid_scheme(self, url):
        with pytest.raises(HTTPException) as exc_info:
            _ssrf.validate_url_shape(url)
        assert exc_info.value.status_code == 400
        assert "scheme" in exc_info.value.detail.lower()

    @pytest.mark.parametrize("hostname", ["localhost", "LOCALHOST", "0.0.0.0"])  # noqa: S104
    def test_rejects_localhost(self, hostname):
        with pytest.raises(HTTPException) as exc_info:
            _ssrf.validate_url_shape(f"http://{hostname}/x")
        assert exc_info.value.status_code == 400
        assert "localhost" in exc_info.value.detail.lower()

    def test_rejects_literal_private_ip(self):
        with pytest.raises(HTTPException) as exc_info:
            _ssrf.validate_url_shape("http://127.0.0.1/x")
        assert exc_info.value.status_code == 400
        assert "private" in exc_info.value.detail.lower()

    def test_rejects_missing_hostname(self):
        with pytest.raises(HTTPException) as exc_info:
            _ssrf.validate_url_shape("http:///path")
        assert exc_info.value.status_code == 400
        assert "hostname" in exc_info.value.detail.lower()

    @pytest.mark.parametrize(
        "url",
        [
            "http://example.com/\x00",
            "http://[::1",
            "http://user:pass@[gg::1]/",
        ],
    )
    def test_rejects_malformed_url_as_400_not_500(self, url):
        # httpx.URL() raises httpx.InvalidURL for these instead of returning
        # a parsed object, and that must surface as a 400, not an unhandled 500.
        with pytest.raises(HTTPException) as exc_info:
            _ssrf.validate_url_shape(url)
        assert exc_info.value.status_code == 400

    def test_allows_hostname_pending_dns_resolution(self):
        # A DNS name is never blocked here. Resolution and validation
        # happen later, in resolve_hostname() and pick_validated_ip().
        assert _ssrf.validate_url_shape("http://evil.attacker.example/x") == "evil.attacker.example"


class TestResolveHostname:
    """Tests for resolve_hostname()."""

    async def test_returns_all_dual_stack_addresses(self, monkeypatch):
        fake_results = [
            (socket.AF_INET6, socket.SOCK_STREAM, 0, "", ("2001:db8::1", 0, 0, 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("203.0.113.5", 0)),
        ]
        monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: fake_results)

        addresses = await _real_resolve_hostname("example.com")

        assert ipaddress.ip_address("2001:db8::1") in addresses
        assert ipaddress.ip_address("203.0.113.5") in addresses

    async def test_dedupes_and_ignores_unsupported_families(self, monkeypatch):
        fake_results = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("203.0.113.5", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("203.0.113.5", 0)),  # duplicate
            (99, socket.SOCK_STREAM, 0, "", ("ignored",)),  # unsupported family
        ]
        monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: fake_results)

        addresses = await _real_resolve_hostname("example.com")

        assert addresses == [ipaddress.ip_address("203.0.113.5")]

    async def test_raises_when_no_addresses_returned(self, monkeypatch):
        monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [])

        with pytest.raises(HTTPException) as exc_info:
            await _real_resolve_hostname("example.com")
        assert exc_info.value.status_code == 400
        assert "resolve" in exc_info.value.detail.lower()

    async def test_raises_when_resolution_fails(self, monkeypatch):
        def raise_gaierror(*_args, **_kwargs):
            raise OSError("Name or service not known")

        monkeypatch.setattr(socket, "getaddrinfo", raise_gaierror)

        with pytest.raises(HTTPException) as exc_info:
            await _real_resolve_hostname("nonexistent.invalid")
        assert exc_info.value.status_code == 400


class TestPickValidatedIp:
    """Tests for pick_validated_ip()."""

    async def test_returns_public_address(self, monkeypatch):
        monkeypatch.setattr(_ssrf, "resolve_hostname", AsyncMock(return_value=[_PUBLIC_IPV4]))

        assert await _ssrf.pick_validated_ip("example.com") == _PUBLIC_IPV4

    async def test_returns_ipv6_when_only_family_resolved(self, monkeypatch):
        monkeypatch.setattr(_ssrf, "resolve_hostname", AsyncMock(return_value=[_PUBLIC_IPV6]))

        assert await _ssrf.pick_validated_ip("example.com") == _PUBLIC_IPV6

    async def test_rejects_when_any_resolved_address_is_private(self, monkeypatch):
        private_ip = ipaddress.ip_address("127.0.0.1")
        monkeypatch.setattr(
            _ssrf, "resolve_hostname", AsyncMock(return_value=[_PUBLIC_IPV4, private_ip])
        )

        with pytest.raises(HTTPException) as exc_info:
            await _ssrf.pick_validated_ip("evil.attacker.example")
        assert exc_info.value.status_code == 400
        assert "private" in exc_info.value.detail.lower()

    async def test_prefers_ipv4_when_both_families_resolve(self, monkeypatch):
        monkeypatch.setattr(
            _ssrf, "resolve_hostname", AsyncMock(return_value=[_PUBLIC_IPV6, _PUBLIC_IPV4])
        )

        assert await _ssrf.pick_validated_ip("example.com") == _PUBLIC_IPV4

    async def test_dns_rebinding_pin_holds(self, monkeypatch):
        """A single call resolves once and keeps that result.

        Simulates a DNS record flipping from a public to a private
        address between two lookups. pick_validated_ip() must resolve
        exactly once and use that one result, not re-resolve and pick up
        the rebound address.
        """
        private_ip = ipaddress.ip_address("127.0.0.1")
        resolver = AsyncMock(side_effect=[[_PUBLIC_IPV4], [private_ip]])
        monkeypatch.setattr(_ssrf, "resolve_hostname", resolver)

        result = await _ssrf.pick_validated_ip("evil.attacker.example")

        assert result == _PUBLIC_IPV4
        assert resolver.call_count == 1


class TestPinnedNetworkBackend:
    """Tests for _PinnedNetworkBackend."""

    async def test_connect_tcp_dials_pinned_ip_not_requested_host(self, monkeypatch):
        recorded_hosts = []

        async def fake_connect_tcp(self, host, port, **kwargs):  # noqa: ARG001
            recorded_hosts.append(host)

        monkeypatch.setattr(httpcore.AnyIOBackend, "connect_tcp", fake_connect_tcp)

        backend = _ssrf._PinnedNetworkBackend(str(_PUBLIC_IPV4))
        await backend.connect_tcp("evil.attacker.example", 443)

        assert recorded_hosts == [str(_PUBLIC_IPV4)]


class TestFetchWithPinnedRedirects:
    """Tests for fetch_with_pinned_redirects()."""

    async def test_stops_at_max_redirects(self, monkeypatch, httpx_mock):
        monkeypatch.setattr(
            _ssrf,
            "resolve_hostname",
            AsyncMock(return_value=[_PUBLIC_IPV4]),
        )
        httpx_mock.add_response(
            url="https://example.com/loop",
            status_code=302,
            headers={"Location": "https://example.com/loop"},
            is_reusable=True,
        )

        with pytest.raises(HTTPException) as exc_info:
            await _ssrf.fetch_with_pinned_redirects(
                "https://example.com/loop", timeout=5.0, max_response_size=1024
            )
        assert exc_info.value.status_code == 400
        assert "redirect" in exc_info.value.detail.lower()

    async def test_redirect_missing_location_header_is_400_not_500(self, monkeypatch, httpx_mock):
        monkeypatch.setattr(
            _ssrf,
            "resolve_hostname",
            AsyncMock(return_value=[_PUBLIC_IPV4]),
        )
        httpx_mock.add_response(url="https://example.com/redirect", status_code=302)

        with pytest.raises(HTTPException) as exc_info:
            await _ssrf.fetch_with_pinned_redirects(
                "https://example.com/redirect", timeout=5.0, max_response_size=1024
            )
        assert exc_info.value.status_code == 400
        assert "location" in exc_info.value.detail.lower()

    async def test_redirect_to_malformed_target_raises_request_error(self, monkeypatch, httpx_mock):
        # httpx raises RemoteProtocolError, an httpx.RequestError subclass,
        # while building the redirect request. See
        # test_api.py::test_fetch_redirect_malformed_location_header for
        # how main.py turns that into a 400.
        monkeypatch.setattr(
            _ssrf,
            "resolve_hostname",
            AsyncMock(return_value=[_PUBLIC_IPV4]),
        )
        httpx_mock.add_response(
            url="https://example.com/redirect",
            status_code=302,
            headers={"Location": "http://[::1"},
        )

        with pytest.raises(httpx.RequestError):
            await _ssrf.fetch_with_pinned_redirects(
                "https://example.com/redirect", timeout=5.0, max_response_size=1024
            )

    async def test_rejects_response_over_max_size(self, monkeypatch, httpx_mock):
        monkeypatch.setattr(
            _ssrf,
            "resolve_hostname",
            AsyncMock(return_value=[_PUBLIC_IPV4]),
        )
        httpx_mock.add_response(url="https://example.com/big", text="x" * 2048)

        with pytest.raises(HTTPException) as exc_info:
            await _ssrf.fetch_with_pinned_redirects(
                "https://example.com/big", timeout=5.0, max_response_size=1024
            )
        assert exc_info.value.status_code == 413

    async def test_allows_response_at_or_under_max_size(self, monkeypatch, httpx_mock):
        monkeypatch.setattr(
            _ssrf,
            "resolve_hostname",
            AsyncMock(return_value=[_PUBLIC_IPV4]),
        )
        httpx_mock.add_response(url="https://example.com/ok", text="x" * 1024)

        response = await _ssrf.fetch_with_pinned_redirects(
            "https://example.com/ok", timeout=5.0, max_response_size=1024
        )
        assert response.status_code == 200
