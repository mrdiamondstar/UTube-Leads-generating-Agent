"""In-process YouTube API quota tracker.

Tracks unit consumption per endpoint with the standard Data API v3 costs and
resets daily (UTC). The Manager persists snapshots to `api_quota_usage` after
each run so quota is observable across restarts.

Reference costs (units per call):
  search.list         100
  channels.list         1
  videos.list           1
  playlistItems.list    1
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.integrations.youtube.errors import QuotaExceededError

ENDPOINT_COST = {
    "search.list": 100,
    "channels.list": 1,
    "videos.list": 1,
    "playlistItems.list": 1,
}


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class QuotaTracker:
    def __init__(self, daily_quota: int = 10000, safety_margin: int = 100) -> None:
        self.daily_quota = daily_quota
        self.safety_margin = safety_margin
        self._lock = asyncio.Lock()
        self._day = _today()
        self.units_used = 0
        self.calls: dict[str, int] = {}

    def _roll_day_if_needed(self) -> None:
        today = _today()
        if today != self._day:
            self._day = today
            self.units_used = 0
            self.calls = {}

    async def reserve(self, endpoint: str) -> None:
        """Account for one call, raising if it would breach the safe budget."""
        cost = ENDPOINT_COST.get(endpoint, 1)
        async with self._lock:
            self._roll_day_if_needed()
            if self.units_used + cost > self.daily_quota - self.safety_margin:
                raise QuotaExceededError(
                    f"quota budget reached: used {self.units_used}, "
                    f"+{cost} for {endpoint} exceeds "
                    f"{self.daily_quota - self.safety_margin}"
                )
            self.units_used += cost
            self.calls[endpoint] = self.calls.get(endpoint, 0) + 1

    def snapshot(self) -> dict:
        self._roll_day_if_needed()
        return {
            "date": self._day,
            "units_used": self.units_used,
            "daily_quota": self.daily_quota,
            "remaining": max(0, self.daily_quota - self.units_used),
            "calls": dict(self.calls),
        }


_tracker: QuotaTracker | None = None


def get_quota_tracker() -> QuotaTracker:
    global _tracker
    if _tracker is None:
        from app.core.config import get_settings

        s = get_settings()
        _tracker = QuotaTracker(s.youtube_daily_quota, s.youtube_quota_safety_margin)
    return _tracker


def reset_quota_tracker() -> None:
    """Test helper."""
    global _tracker
    _tracker = None
