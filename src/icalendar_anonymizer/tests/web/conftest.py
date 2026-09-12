# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Pytest configuration for web service tests."""

import ipaddress

import pytest

from icalendar_anonymizer.webapp import _ssrf

# example.com's actual IP. It's never dialed, since httpx_mock intercepts
# the mocked transport first, but it still needs to pass is_private_ip's
# allowlist check, which a documentation-only address like RFC 5737's
# TEST-NET-3 would not.
_FAKE_PUBLIC_IP = ipaddress.ip_address("93.184.216.34")


@pytest.fixture(autouse=True)
def _stub_dns_resolution(monkeypatch):
    """Stub DNS resolution so web tests never depend on real network access.

    Literal IP hostnames resolve to themselves. Any other hostname
    resolves to a fixed public placeholder address. The resolved IP
    doesn't matter for these tests, since pytest-httpx intercepts
    requests at the transport layer before the pinned connection would
    ever be dialed.
    """

    async def fake_resolve_hostname(hostname: str) -> list:
        try:
            return [ipaddress.ip_address(hostname)]
        except ValueError:
            return [_FAKE_PUBLIC_IP]

    monkeypatch.setattr(_ssrf, "resolve_hostname", fake_resolve_hostname)
