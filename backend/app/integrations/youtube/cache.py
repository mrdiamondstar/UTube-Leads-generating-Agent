"""Response cache for YouTube API calls.

Uses Redis when reachable (shared across workers), otherwise an in-process
TTL cache. Falls back gracefully so the app runs with or without Redis.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from app.core.logging import get_logger

log = get_logger("youtube.cache")


def make_key(endpoint: str, params: dict[str, Any]) -> str:
    # Exclude the API key from the cache key.
    safe = {k: v for k, v in params.items() if k != "key"}
    blob = json.dumps({"e": endpoint, "p": safe}, sort_keys=True, default=str)
    return "yt:" + hashlib.sha256(blob.encode()).hexdigest()[:32]


class InMemoryTTLCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}

    async def get(self, key: str) -> Any | None:
        item = self._store.get(key)
        if not item:
            return None
        expires_at, value = item
        if expires_at < time.time():
            self._store.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: Any, ttl: int) -> None:
        self._store[key] = (time.time() + ttl, value)


class RedisCache:
    def __init__(self, client: Any) -> None:
        self._client = client

    async def get(self, key: str) -> Any | None:
        raw = await self._client.get(key)
        return json.loads(raw) if raw else None

    async def set(self, key: str, value: Any, ttl: int) -> None:
        await self._client.set(key, json.dumps(value, default=str), ex=ttl)


async def build_cache(redis_url: str | None):
    """Return a Redis-backed cache if available, else an in-memory one."""
    if redis_url:
        try:
            import redis.asyncio as aioredis  # lazy: optional dependency

            client = aioredis.from_url(redis_url, decode_responses=True)
            await client.ping()
            log.info("cache.redis", url=redis_url)
            return RedisCache(client)
        except Exception as exc:  # noqa: BLE001
            log.warning("cache.redis_unavailable", error=str(exc))
    return InMemoryTTLCache()
