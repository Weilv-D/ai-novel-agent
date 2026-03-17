"""Redis-backed cache helpers with graceful degradation."""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable
from hashlib import sha256
from typing import Any
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _json_default(value: Any) -> Any:
    """Convert non-JSON-native values into stable cache-safe forms."""
    if isinstance(value, UUID):
        return str(value)
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return str(value)


class CacheService:
    """Thin async cache wrapper around Redis."""

    def __init__(self, redis_url: str | None = None) -> None:
        self.redis_url = redis_url or settings.redis_url
        self._client: Redis | None = None

    @property
    def is_connected(self) -> bool:
        """Whether the cache currently has a live Redis client."""
        return self._client is not None

    @staticmethod
    def build_hash(payload: Any) -> str:
        """Build a stable SHA-256 hash for arbitrary JSON-serializable payloads."""
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=_json_default,
        )
        return sha256(encoded.encode("utf-8")).hexdigest()

    async def init(self) -> None:
        """Initialize the Redis client, falling back to disabled cache on failure."""
        if self._client is not None:
            return

        try:
            client = Redis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)
            ping_result = client.ping()
            if isinstance(ping_result, Awaitable):
                await ping_result
        except RedisError as exc:
            logger.warning("Redis cache unavailable; continuing without cache: %s", exc)
            self._client = None
            return

        self._client = client
        logger.info("Redis cache initialized")

    async def close(self) -> None:
        """Close the Redis client."""
        if self._client is None:
            return

        await self._client.aclose()
        self._client = None

    async def get(self, key: str) -> Any | None:
        """Fetch a JSON value from cache."""
        if self._client is None:
            return None

        try:
            payload = await self._client.get(key)
        except RedisError as exc:
            logger.warning("Cache get failed for key %s: %s", key, exc)
            return None

        if payload is None:
            return None

        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            logger.warning("Cache payload for key %s is not valid JSON; ignoring", key)
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a JSON value in cache."""
        if self._client is None:
            return

        try:
            payload = json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
                default=_json_default,
            )
            await self._client.set(key, payload, ex=ttl)
        except RedisError as exc:
            logger.warning("Cache set failed for key %s: %s", key, exc)

    async def delete(self, *keys: str) -> int:
        """Delete explicit cache keys."""
        if self._client is None or not keys:
            return 0

        try:
            return int(await self._client.delete(*keys))
        except RedisError as exc:
            logger.warning("Cache delete failed for keys %s: %s", keys, exc)
            return 0

    async def invalidate_pattern(self, pattern: str) -> int:
        """Delete all keys matching a Redis glob pattern."""
        if self._client is None:
            return 0

        keys: list[str] = []
        try:
            async for key in self._client.scan_iter(match=pattern):
                keys.append(key)
        except RedisError as exc:
            logger.warning("Cache scan failed for pattern %s: %s", pattern, exc)
            return 0

        if not keys:
            return 0

        return await self.delete(*keys)


cache_service = CacheService()
