"""Tests for the Redis cache wrapper."""

from __future__ import annotations

from fnmatch import fnmatch
from unittest.mock import patch
from uuid import uuid4

import pytest
from pydantic import BaseModel
from redis.exceptions import RedisError

from app.core.cache import CacheService


class FakeRedis:
    """Minimal async Redis stub for cache service tests."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.closed = False

    async def ping(self) -> bool:
        return True

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.store[key] = value
        return True

    async def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self.store:
                deleted += 1
                del self.store[key]
        return deleted

    async def scan_iter(self, match: str):
        for key in list(self.store):
            if fnmatch(key, match):
                yield key

    async def aclose(self) -> None:
        self.closed = True


class FakeSyncPingRedis(FakeRedis):
    """Redis stub whose ping() is synchronous."""

    def ping(self) -> bool:
        return True


class BrokenGetRedis(FakeRedis):
    """Redis stub that fails on get()."""

    async def get(self, key: str) -> str | None:
        raise RedisError("get failed")


class BrokenSetRedis(FakeRedis):
    """Redis stub that fails on set()."""

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        raise RedisError("set failed")


class BrokenDeleteRedis(FakeRedis):
    """Redis stub that fails on delete()."""

    async def delete(self, *keys: str) -> int:
        raise RedisError("delete failed")


class BrokenScanRedis(FakeRedis):
    """Redis stub that fails during scan_iter()."""

    async def scan_iter(self, match: str):
        raise RedisError("scan failed")
        yield match


class PayloadModel(BaseModel):
    """Pydantic payload used to cover model_dump serialization."""

    value: int


class TestCacheService:
    """Tests for cache service primitives."""

    @pytest.mark.asyncio
    async def test_get_set_delete_and_invalidate_pattern(self) -> None:
        """CacheService should serialize JSON values and remove matching keys."""
        cache = CacheService(redis_url="redis://test")
        fake_redis = FakeRedis()
        cache._client = fake_redis

        await cache.set("llm:key", {"value": 1}, ttl=60)
        await cache.set("vsearch:project:a", {"value": 2}, ttl=60)
        await cache.set("vsearch:project:b", {"value": 3}, ttl=60)

        assert await cache.get("llm:key") == {"value": 1}
        assert await cache.delete("llm:key") == 1
        assert await cache.get("llm:key") is None

        deleted = await cache.invalidate_pattern("vsearch:project:*")
        assert deleted == 2
        assert fake_redis.store == {}

    @pytest.mark.asyncio
    async def test_init_gracefully_disables_cache_when_redis_fails(self) -> None:
        """Redis init failures should not raise and should leave cache disconnected."""
        cache = CacheService(redis_url="redis://broken")

        with patch("app.core.cache.Redis.from_url", side_effect=RedisError("boom")):
            await cache.init()

        assert cache.is_connected is False

    def test_build_hash_is_stable_for_equivalent_payloads(self) -> None:
        """Cache hashes should not depend on dict insertion order."""
        first = CacheService.build_hash({"b": 2, "a": 1, "id": uuid4(), "payload": PayloadModel(value=1)})
        second = CacheService.build_hash({"payload": PayloadModel(value=1), "a": 1, "id": first and uuid4(), "b": 2})
        # Different UUIDs should produce different hashes.
        assert first != second

        shared_id = uuid4()
        stable_first = CacheService.build_hash({"b": 2, "a": 1, "id": shared_id, "payload": PayloadModel(value=1)})
        stable_second = CacheService.build_hash({"payload": PayloadModel(value=1), "a": 1, "id": shared_id, "b": 2})
        assert stable_first == stable_second

    @pytest.mark.asyncio
    async def test_init_reuses_existing_client_and_accepts_sync_ping(self) -> None:
        """init() should no-op with an existing client and support non-awaitable ping()."""
        cache = CacheService(redis_url="redis://test")
        existing = FakeRedis()
        cache._client = existing

        with patch("app.core.cache.Redis.from_url") as mock_from_url:
            await cache.init()

        assert cache._client is existing
        mock_from_url.assert_not_called()

        cache = CacheService(redis_url="redis://test")
        fake_redis = FakeSyncPingRedis()
        with patch("app.core.cache.Redis.from_url", return_value=fake_redis):
            await cache.init()
        assert cache.is_connected is True

    @pytest.mark.asyncio
    async def test_close_get_and_set_handle_edge_cases(self) -> None:
        """Cache operations should degrade gracefully on empty, invalid, and failing payloads."""
        cache = CacheService(redis_url="redis://test")
        assert await cache.get("missing") is None
        await cache.close()

        fake_redis = FakeRedis()
        fake_redis.store["broken"] = "not-json"
        cache._client = fake_redis
        assert await cache.get("broken") is None

        model_id = uuid4()
        await cache.set("model", {"id": model_id, "payload": PayloadModel(value=3)}, ttl=30)
        assert await cache.get("model") == {"id": str(model_id), "payload": {"value": 3}}

        await cache.close()
        assert fake_redis.closed is True
        assert cache.is_connected is False

    @pytest.mark.asyncio
    async def test_get_set_delete_and_scan_failures_return_safe_defaults(self) -> None:
        """Redis exceptions from individual operations should not escape the cache layer."""
        cache = CacheService(redis_url="redis://test")

        cache._client = BrokenGetRedis()
        assert await cache.get("x") is None

        cache._client = BrokenSetRedis()
        await cache.set("x", {"value": 1})

        cache._client = BrokenDeleteRedis()
        assert await cache.delete("x") == 0
        assert await cache.delete() == 0

        cache._client = BrokenScanRedis()
        assert await cache.invalidate_pattern("llm:*") == 0

    @pytest.mark.asyncio
    async def test_invalidate_pattern_returns_zero_when_no_keys_match(self) -> None:
        """invalidate_pattern() should short-circuit when scan finds no keys."""
        cache = CacheService(redis_url="redis://test")
        cache._client = FakeRedis()

        assert await cache.invalidate_pattern("none:*") == 0
