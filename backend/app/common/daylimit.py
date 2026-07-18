"""Helpers for the per-day lead limit.

The "day" boundary is IST (Asia/Kolkata) so "today" matches the user's local
calendar day, resetting at IST midnight.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


def day_start_utc(now: datetime | None = None) -> datetime:
    """Start of the current IST day, expressed in UTC (for created_at filters)."""
    now_ist = (now or datetime.now(timezone.utc)).astimezone(IST)
    start_ist = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
    return start_ist.astimezone(timezone.utc)
