# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""R2 storage client wrapper with local dev mock support."""

import secrets
from typing import Protocol


class R2Client(Protocol):
    """R2 client interface.

    Defines the interface for R2 storage operations. Implemented by both
    MockR2Client (local dev) and WorkersR2Client (production).
    """

    async def put(self, key: str, data: bytes) -> None:
        """Store data in R2.

        Args:
            key: Object key/identifier
            data: Binary data to store
        """
        ...

    async def get(self, key: str) -> bytes | None:
        """Retrieve data from R2.

        Args:
            key: Object key/identifier

        Returns:
            Binary data if found, None otherwise
        """
        ...

    async def exists(self, key: str) -> bool:
        """Check if key exists in R2.

        Args:
            key: Object key/identifier

        Returns:
            True if object exists, False otherwise
        """
        ...


class MockR2Client:
    """In-memory R2 mock for local development and testing.

    Stores objects in memory using a dictionary. Suitable for local dev
    and automated tests, but does not persist data between runs.
    """

    def __init__(self):
        """Initialize empty in-memory storage."""
        self._store: dict[str, bytes] = {}

    async def put(self, key: str, data: bytes) -> None:
        """Store data in memory.

        Args:
            key: Object key/identifier
            data: Binary data to store
        """
        self._store[key] = data

    async def get(self, key: str) -> bytes | None:
        """Retrieve data from memory.

        Args:
            key: Object key/identifier

        Returns:
            Binary data if found, None otherwise
        """
        return self._store.get(key)

    async def exists(self, key: str) -> bool:
        """Check if key exists in memory.

        Args:
            key: Object key/identifier

        Returns:
            True if object exists, False otherwise
        """
        return key in self._store


class WorkersR2Client:
    """Native Cloudflare Workers R2 client.

    Wraps the Cloudflare Workers R2 bucket binding to match our R2Client interface.
    Only works in Cloudflare Workers runtime with R2 binding configured.

    Note: Pyodide requires conversion between Python bytes and JavaScript
    ArrayBuffer/Uint8Array using to_js() and to_py().
    """

    def __init__(self, bucket):
        """Initialize with R2 bucket binding.

        Args:
            bucket: Cloudflare Workers R2 bucket binding from env
        """
        self._bucket = bucket

    async def put(self, key: str, data: bytes) -> None:
        """Store data in R2.

        Args:
            key: Object key/identifier
            data: Binary data to store
        """
        from pyodide.ffi import to_js

        # Convert Python bytes to JavaScript Uint8Array for R2
        js_data = to_js(data)
        await self._bucket.put(key, js_data)

    async def get(self, key: str) -> bytes | None:
        """Retrieve data from R2.

        Args:
            key: Object key/identifier

        Returns:
            Binary data if found, None otherwise
        """
        from pyodide.ffi import JsProxy

        obj = await self._bucket.get(key)
        # R2 returns JavaScript null when not found, check with isinstance
        if not isinstance(obj, JsProxy):
            return None
        # Get the ArrayBuffer and convert to Python bytes
        array_buffer = await obj.arrayBuffer()
        return array_buffer.to_bytes()

    async def exists(self, key: str) -> bool:
        """Check if key exists in R2.

        Args:
            key: Object key/identifier

        Returns:
            True if object exists, False otherwise
        """
        from pyodide.ffi import JsProxy

        obj = await self._bucket.head(key)
        # R2 returns JavaScript null when not found
        # In Pyodide, JS null becomes jsnull (not Python None)
        return isinstance(obj, JsProxy)


def generate_share_id() -> str:
    """Generate URL-safe random 8-character ID.

    Uses secrets.token_urlsafe() for cryptographically strong randomness.
    Characters are URL-safe (alphanumeric, hyphen, underscore).

    Returns:
        8-character random string suitable for URLs
    """
    return secrets.token_urlsafe(8)[:8]


async def generate_unique_id(r2_client: R2Client, max_attempts: int = 5) -> str:
    """Generate unique ID with collision detection.

    Generates random IDs and checks R2 to ensure uniqueness. Retries up to
    max_attempts times if collisions occur.

    Args:
        r2_client: R2 client to check for existing keys
        max_attempts: Maximum number of generation attempts

    Returns:
        Unique 8-character share ID

    Raises:
        RuntimeError: If unable to generate unique ID within max_attempts
    """
    for _ in range(max_attempts):
        share_id = generate_share_id()
        if not await r2_client.exists(share_id):
            return share_id
    raise RuntimeError("Failed to generate unique share ID")
