"""Client-side rate limiting for the YouTube API.

Enforces a minimum interval between requests and a concurrency ceiling so we
stay well within API limits even under bursty pipeline runs.
"""
from __future__ import annotations

import asyncio
import time


class RateLimiter:
    def __init__(self, min_interval_ms: int = 50, max_concurrency: int = 5) -> None:
        self._min_interval = min_interval_ms / 1000.0
        self._sem = asyncio.Semaphore(max_concurrency)
        self._lock = asyncio.Lock()
        self._last_call = 0.0

    async def __aenter__(self) -> "RateLimiter":
        await self._sem.acquire()
        async with self._lock:
            now = time.monotonic()
            wait = self._min_interval - (now - self._last_call)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call = time.monotonic()
        return self

    async def __aexit__(self, *exc) -> None:
        self._sem.release()
