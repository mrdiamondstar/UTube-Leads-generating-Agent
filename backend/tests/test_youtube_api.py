"""Tests for the real YouTube Data API v3 client.

Uses httpx.MockTransport to simulate the API — verifies parsing, pagination,
quota accounting, caching, and retry without any network or API key.
"""
from __future__ import annotations

import httpx
import pytest

from app.core.config import get_settings
from app.integrations.youtube import api as api_mod
from app.integrations.youtube.api import YouTubeApiProvider
from app.integrations.youtube.cache import InMemoryTTLCache
from app.integrations.youtube.errors import QuotaExceededError, TransientApiError
from app.integrations.youtube.quota import QuotaTracker, get_quota_tracker, reset_quota_tracker


@pytest.fixture(autouse=True)
def _fresh_state():
    # Isolate the process-global quota tracker + shared cache between tests.
    reset_quota_tracker()
    api_mod._SHARED_CACHE = InMemoryTTLCache()
    yield
    api_mod._SHARED_CACHE = None
    reset_quota_tracker()


def _handler(request: httpx.Request) -> httpx.Response:
    path = "/" + request.url.path.rsplit("/", 1)[-1]  # last segment, e.g. /search
    params = dict(request.url.params)

    if path == "/search":
        if params.get("pageToken") == "p2":
            return httpx.Response(
                200, json={"items": [{"snippet": {"channelId": "c2"}}]}
            )
        return httpx.Response(
            200,
            json={
                "items": [
                    {"snippet": {"channelId": "c0"}},
                    {"snippet": {"channelId": "c1"}},
                ],
                "nextPageToken": "p2",
            },
        )

    if path == "/channels":
        ids = params["id"].split(",")
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": cid,
                        "snippet": {"title": f"Channel {cid}", "country": "US"},
                        "statistics": {
                            "subscriberCount": "100000",
                            "viewCount": "1000000",
                            "videoCount": "50",
                        },
                        "contentDetails": {"relatedPlaylists": {"uploads": f"UU_{cid}"}},
                    }
                    for cid in ids
                ]
            },
        )

    if path == "/playlistItems":
        return httpx.Response(
            200,
            json={
                "items": [
                    {"contentDetails": {"videoId": "v0"}},
                    {"contentDetails": {"videoId": "v1"}},
                ]
            },
        )

    if path == "/videos":
        ids = params["id"].split(",")
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": vid,
                        "snippet": {
                            "channelId": "c0",
                            "title": f"Video {vid}",
                            "publishedAt": "2024-01-01T00:00:00Z",
                        },
                        "statistics": {
                            "viewCount": "5000",
                            "likeCount": "200",
                            "commentCount": "30",
                        },
                    }
                    for vid in ids
                ]
            },
        )

    return httpx.Response(404, json={"error": "not found"})


def _provider() -> YouTubeApiProvider:
    return YouTubeApiProvider(
        api_key="test-key",
        settings=get_settings(),
        transport=httpx.MockTransport(_handler),
    )


@pytest.mark.asyncio
async def test_search_channels_paginates_and_parses():
    p = _provider()
    channels = await p.search_channels("python", max_results=3)
    await p.aclose()

    assert [c.youtube_id for c in channels] == ["c0", "c1", "c2"]
    assert channels[0].subscriber_count == 100000
    assert channels[0].uploads_playlist_id == "UU_c0"
    assert channels[0].country == "US"

    # 2 search.list (100 each) + 1 channels.list (1) = 201 units.
    assert get_quota_tracker().snapshot()["units_used"] == 201


@pytest.mark.asyncio
async def test_cache_prevents_repeat_quota_spend():
    p = _provider()
    await p.search_channels("python", max_results=3)
    first = get_quota_tracker().snapshot()["units_used"]
    # Identical request sequence -> all cache hits -> no additional quota.
    await p.search_channels("python", max_results=3)
    second = get_quota_tracker().snapshot()["units_used"]
    await p.aclose()
    assert first == second == 201


@pytest.mark.asyncio
async def test_recent_videos_and_statistics():
    p = _provider()
    videos = await p.get_recent_videos("UU_c0", "c0", max_results=2)
    await p.aclose()

    assert [v.video_id for v in videos] == ["v0", "v1"]
    assert videos[0].view_count == 5000
    assert videos[0].like_count == 200
    assert videos[0].published_at is not None
    # playlistItems.list (1) + videos.list (1) = 2 units.
    assert get_quota_tracker().snapshot()["units_used"] == 2


def test_quota_tracker_enforces_budget():
    import asyncio

    tracker = QuotaTracker(daily_quota=150, safety_margin=0)
    asyncio.run(tracker.reserve("search.list"))  # 100
    with pytest.raises(QuotaExceededError):
        asyncio.run(tracker.reserve("search.list"))  # +100 -> 200 > 150
    snap = tracker.snapshot()
    assert snap["units_used"] == 100
    assert snap["remaining"] == 50


@pytest.mark.asyncio
async def test_retry_on_transient_then_success():
    calls = {"n": 0}

    def flaky(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/search"):
            calls["n"] += 1
            if calls["n"] < 3:
                return httpx.Response(503, json={"error": "unavailable"})
            return httpx.Response(200, json={"items": [{"snippet": {"channelId": "c0"}}]})
        return _handler(request)

    p = YouTubeApiProvider(
        api_key="test-key",
        settings=get_settings(),
        transport=httpx.MockTransport(flaky),
    )
    channels = await p.search_channels("retry", max_results=1)
    await p.aclose()
    assert calls["n"] == 3
    assert channels[0].youtube_id == "c0"


@pytest.mark.asyncio
async def test_quota_exceeded_403_is_not_retried():
    def forbidden(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403, json={"error": {"errors": [{"reason": "quotaExceeded"}]}}
        )

    p = YouTubeApiProvider(
        api_key="test-key",
        settings=get_settings(),
        transport=httpx.MockTransport(forbidden),
    )
    with pytest.raises(QuotaExceededError):
        await p.search_channels("q", max_results=1)
    await p.aclose()
