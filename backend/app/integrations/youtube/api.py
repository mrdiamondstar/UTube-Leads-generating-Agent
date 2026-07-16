"""Real YouTube Data API v3 client.

Enabled with YOUTUBE_PROVIDER=api and YOUTUBE_API_KEY (read from env; never
hardcoded). Implements the four required operations with quota accounting,
response caching, retry/backoff, pagination, and client-side rate limiting.

Operations -> endpoints (cost in quota units):
  Channel search    search.list        (100)
  Channel details   channels.list      (1)
  Recent videos     playlistItems.list (1)
  Video statistics  videos.list        (1)
"""
from __future__ import annotations

import asyncio
from datetime import datetime

import httpx

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.domain.schemas import RawChannel, RawVideo
from app.integrations.youtube.base import YouTubeProvider
from app.integrations.youtube.cache import build_cache, make_key
from app.integrations.youtube.errors import (
    ApiKeyMissingError,
    QuotaExceededError,
    TransientApiError,
    YouTubeError,
)
from app.integrations.youtube.quota import get_quota_tracker
from app.integrations.youtube.ratelimit import RateLimiter

log = get_logger("youtube.api")
# Trailing slash + relative paths so httpx preserves the /youtube/v3 prefix.
_BASE = "https://www.googleapis.com/youtube/v3/"
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}

# In-memory cache shared across provider instances in the same process
# (a real Redis cache is used automatically when REDIS_URL is reachable).
_SHARED_CACHE = None
_CACHE_LOCK = asyncio.Lock()


def _chunks(items: list[str], size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class YouTubeApiProvider(YouTubeProvider):
    def __init__(
        self,
        api_key: str,
        settings: Settings | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise ApiKeyMissingError("YOUTUBE_API_KEY is required when YOUTUBE_PROVIDER=api")
        self._key = api_key
        self._s = settings or get_settings()
        self._client = httpx.AsyncClient(base_url=_BASE, timeout=20.0, transport=transport)
        self._limiter = RateLimiter(
            self._s.youtube_min_request_interval_ms, self._s.youtube_max_concurrency
        )
        self._quota = get_quota_tracker()
        self._cache = None

    # ---- infrastructure ----------------------------------------------------
    async def _get_cache(self):
        global _SHARED_CACHE
        if _SHARED_CACHE is None:
            async with _CACHE_LOCK:
                if _SHARED_CACHE is None:
                    _SHARED_CACHE = await build_cache(self._s.redis_url)
        self._cache = _SHARED_CACHE
        return self._cache

    async def _request(self, endpoint: str, params: dict) -> dict:
        """One API call: cache -> quota -> rate limit -> retry -> parse.

        `endpoint` is e.g. "search.list"; the path is derived from it.
        """
        path = endpoint.split(".")[0]  # search.list -> search (relative to _BASE)
        full_params = {**params, "key": self._key}
        cache = await self._get_cache()
        cache_key = make_key(endpoint, full_params)

        cached = await cache.get(cache_key)
        if cached is not None:
            log.info("api.cache_hit", endpoint=endpoint)
            return cached

        # Reserve quota only for a real network call (cache hits are free).
        await self._quota.reserve(endpoint)

        data = await self._request_with_retry(endpoint, path, full_params)
        await cache.set(cache_key, data, self._s.youtube_cache_ttl_seconds)
        return data

    async def _request_with_retry(self, endpoint: str, path: str, params: dict) -> dict:
        attempt = 0
        while True:
            attempt += 1
            try:
                async with self._limiter:
                    resp = await self._client.get(path, params=params)
                if resp.status_code == 200:
                    return resp.json()
                self._raise_for_status(resp)
            except (httpx.TransportError, TransientApiError) as exc:
                if attempt > self._s.youtube_max_retries:
                    raise TransientApiError(f"{endpoint} failed after {attempt} attempts: {exc}")
                backoff = min(2 ** (attempt - 1), 30) * 0.5
                log.warning("api.retry", endpoint=endpoint, attempt=attempt, backoff=backoff)
                await asyncio.sleep(backoff)

    @staticmethod
    def _raise_for_status(resp: httpx.Response) -> None:
        if resp.status_code in _RETRYABLE_STATUS:
            raise TransientApiError(f"HTTP {resp.status_code}")
        if resp.status_code == 403:
            reason = ""
            try:
                errors = resp.json().get("error", {}).get("errors", [{}])
                reason = errors[0].get("reason", "")
            except Exception:  # noqa: BLE001
                pass
            if reason in ("quotaExceeded", "dailyLimitExceeded"):
                raise QuotaExceededError(f"YouTube quota exceeded: {reason}")
            if reason in ("rateLimitExceeded", "userRateLimitExceeded"):
                raise TransientApiError(f"rate limited: {reason}")
            raise YouTubeError(f"forbidden: {reason or resp.text}")
        raise YouTubeError(f"HTTP {resp.status_code}: {resp.text[:200]}")

    # ---- operations --------------------------------------------------------
    async def search_channels(self, query: str, max_results: int = 25) -> list[RawChannel]:
        channel_ids = await self._search_channel_ids(query, max_results)
        if not channel_ids:
            return []
        return await self._get_channel_details(channel_ids)

    async def _search_channel_ids(self, query: str, max_results: int) -> list[str]:
        """Paginated channel search."""
        ids: list[str] = []
        page_token: str | None = None
        while len(ids) < max_results:
            page_size = min(self._s.youtube_page_size, max_results - len(ids))
            params = {
                "q": query,
                "type": "channel",
                "part": "snippet",
                "maxResults": page_size,
            }
            if page_token:
                params["pageToken"] = page_token
            data = await self._request("search.list", params)
            for item in data.get("items", []):
                cid = item.get("snippet", {}).get("channelId") or item.get("id", {}).get(
                    "channelId"
                )
                if cid and cid not in ids:
                    ids.append(cid)
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        return ids[:max_results]

    async def _get_channel_details(self, channel_ids: list[str]) -> list[RawChannel]:
        """Batched channels.list (<=50 ids/call)."""
        out: list[RawChannel] = []
        for batch in _chunks(channel_ids, 50):
            data = await self._request(
                "channels.list",
                {
                    "id": ",".join(batch),
                    "part": "snippet,statistics,contentDetails",
                    "maxResults": 50,
                },
            )
            for item in data.get("items", []):
                out.append(self._to_channel(item))
        return out

    async def get_recent_videos(
        self, uploads_playlist_id: str, channel_youtube_id: str, max_results: int = 10
    ) -> list[RawVideo]:
        if not uploads_playlist_id:
            return []
        video_ids = await self._recent_video_ids(uploads_playlist_id, max_results)
        if not video_ids:
            return []
        return await self._get_video_statistics(video_ids, channel_youtube_id)

    async def _recent_video_ids(self, uploads_playlist_id: str, max_results: int) -> list[str]:
        ids: list[str] = []
        page_token: str | None = None
        while len(ids) < max_results:
            page_size = min(self._s.youtube_page_size, max_results - len(ids))
            params = {
                "playlistId": uploads_playlist_id,
                "part": "contentDetails",
                "maxResults": page_size,
            }
            if page_token:
                params["pageToken"] = page_token
            data = await self._request("playlistItems.list", params)
            for item in data.get("items", []):
                vid = item.get("contentDetails", {}).get("videoId")
                if vid:
                    ids.append(vid)
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        return ids[:max_results]

    async def _get_video_statistics(
        self, video_ids: list[str], channel_youtube_id: str
    ) -> list[RawVideo]:
        out: list[RawVideo] = []
        for batch in _chunks(video_ids, 50):
            data = await self._request(
                "videos.list",
                {"id": ",".join(batch), "part": "snippet,statistics", "maxResults": 50},
            )
            for item in data.get("items", []):
                out.append(self._to_video(item, channel_youtube_id))
        return out

    # ---- mappers -----------------------------------------------------------
    @staticmethod
    def _to_channel(item: dict) -> RawChannel:
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        uploads = (
            item.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
        )
        return RawChannel(
            youtube_id=item["id"],
            title=snippet.get("title", ""),
            description=snippet.get("description", ""),
            country=snippet.get("country"),
            category=None,
            subscriber_count=int(stats.get("subscriberCount", 0) or 0),
            view_count=int(stats.get("viewCount", 0) or 0),
            video_count=int(stats.get("videoCount", 0) or 0),
            default_language=snippet.get("defaultLanguage"),
            uploads_playlist_id=uploads,
            website=None,
            public_email=None,  # never scraped; Phase-2 enrichment uses public sources
            social_links={},
        )

    @staticmethod
    def _to_video(item: dict, channel_youtube_id: str) -> RawVideo:
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        return RawVideo(
            video_id=item["id"],
            channel_youtube_id=snippet.get("channelId") or channel_youtube_id,
            title=snippet.get("title", ""),
            published_at=_parse_dt(snippet.get("publishedAt")),
            view_count=int(stats.get("viewCount", 0) or 0),
            like_count=int(stats.get("likeCount", 0) or 0),
            comment_count=int(stats.get("commentCount", 0) or 0),
        )

    async def aclose(self) -> None:
        await self._client.aclose()
