# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Tests for R2 storage functionality."""

import pytest

from icalendar_anonymizer.webapp.r2 import MockR2Client, generate_share_id, generate_unique_id


class TestMockR2Client:
    """Tests for MockR2Client implementation."""

    @pytest.mark.asyncio
    async def test_put_and_get(self):
        """Test storing and retrieving data."""
        client = MockR2Client()

        await client.put("test-key", b"test-data")
        data = await client.get("test-key")

        assert data == b"test-data"

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self):
        """Test retrieving nonexistent key returns None."""
        client = MockR2Client()
        data = await client.get("missing-key")
        assert data is None

    @pytest.mark.asyncio
    async def test_exists_true(self):
        """Test exists returns True for existing key."""
        client = MockR2Client()

        await client.put("test-key", b"data")
        assert await client.exists("test-key")

    @pytest.mark.asyncio
    async def test_exists_false(self):
        """Test exists returns False for missing key."""
        client = MockR2Client()
        assert not await client.exists("nonexistent-key")

    @pytest.mark.asyncio
    async def test_multiple_keys(self):
        """Test storing multiple distinct keys."""
        client = MockR2Client()

        await client.put("key1", b"data1")
        await client.put("key2", b"data2")

        assert await client.get("key1") == b"data1"
        assert await client.get("key2") == b"data2"

    @pytest.mark.asyncio
    async def test_overwrite_key(self):
        """Test overwriting existing key."""
        client = MockR2Client()

        await client.put("key", b"original")
        await client.put("key", b"updated")

        assert await client.get("key") == b"updated"


class TestShareID:
    """Tests for share ID generation."""

    def test_generate_share_id_length(self):
        """Test share ID is exactly 8 characters."""
        share_id = generate_share_id()
        assert len(share_id) == 8

    def test_generate_share_id_url_safe(self):
        """Test share ID contains only URL-safe characters."""
        share_id = generate_share_id()
        # URL-safe base64 uses alphanumeric, hyphen, and underscore
        assert share_id.replace("-", "").replace("_", "").isalnum()

    def test_generate_share_id_unique(self):
        """Test multiple calls generate different IDs."""
        ids = {generate_share_id() for _ in range(100)}
        # With 8 URL-safe base64 chars (64^8 possibilities), collisions are extremely unlikely
        assert len(ids) == 100


class TestUniqueID:
    """Tests for unique ID generation with collision detection."""

    @pytest.mark.asyncio
    async def test_generate_unique_id_success(self):
        """Test successful unique ID generation."""
        client = MockR2Client()

        share_id = await generate_unique_id(client)

        assert len(share_id) == 8
        assert not await client.exists(share_id)

    @pytest.mark.asyncio
    async def test_generate_unique_id_collision_retry(self):
        """Test collision detection and retry logic."""
        client = MockR2Client()

        # Generate first ID and store it
        id1 = await generate_unique_id(client)
        await client.put(id1, b"data")

        # Second ID should be different
        id2 = await generate_unique_id(client)

        assert id2 != id1
        assert len(id2) == 8

    @pytest.mark.asyncio
    async def test_generate_unique_id_max_attempts_exceeded(self):
        """Test failure after max attempts."""
        client = MockR2Client()

        # Mock exists to always return True
        async def always_exists(_key: str) -> bool:
            return True

        client.exists = always_exists

        with pytest.raises(RuntimeError, match="Failed to generate unique share ID"):
            await generate_unique_id(client, max_attempts=3)

    @pytest.mark.asyncio
    async def test_generate_unique_id_custom_max_attempts(self):
        """Test custom max_attempts parameter."""
        client = MockR2Client()
        attempt_count = 0

        async def count_attempts(_key: str) -> bool:
            nonlocal attempt_count
            attempt_count += 1
            return True

        client.exists = count_attempts

        with pytest.raises(RuntimeError):
            await generate_unique_id(client, max_attempts=10)

        assert attempt_count == 10
