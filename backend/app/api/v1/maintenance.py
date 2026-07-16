"""Maintenance endpoints — YouTube API Terms data-retention compliance.

The YouTube API Services Terms require stored channel/video data to be deleted
or refreshed within 30 days. Re-discovering a niche refreshes its channels
(updated_at bumps); this endpoint purges channels that have NOT been refreshed
within `data_retention_days`, cascading to their videos/scores/snapshots/status.

Trigger it on a daily schedule with any free cron (e.g. cron-job.org) hitting
POST /api/v1/maintenance/cleanup with the X-Maintenance-Token header.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.domain.models import (
    Channel,
    ChannelSnapshot,
    LeadScore,
    LeadStatus,
    Video,
)

router = APIRouter()


@router.post("/maintenance/cleanup")
async def cleanup_stale_data(
    x_maintenance_token: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Delete channels (and their dependent rows) not refreshed within the
    retention window, per YouTube API Terms."""
    if settings.maintenance_token and x_maintenance_token != settings.maintenance_token:
        raise HTTPException(status_code=401, detail="invalid maintenance token")

    if settings.data_retention_days <= 0:
        return {"enabled": False, "deleted_channels": 0}

    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.data_retention_days)
    stale_ids = (
        (await session.execute(select(Channel.id).where(Channel.updated_at < cutoff)))
        .scalars()
        .all()
    )
    if not stale_ids:
        return {"enabled": True, "cutoff": cutoff.isoformat(), "deleted_channels": 0}

    # Delete dependents first (works regardless of DB-level cascade config).
    for model in (LeadStatus, LeadScore, Video, ChannelSnapshot):
        await session.execute(delete(model).where(model.channel_id.in_(stale_ids)))
    await session.execute(delete(Channel).where(Channel.id.in_(stale_ids)))

    return {
        "enabled": True,
        "cutoff": cutoff.isoformat(),
        "deleted_channels": len(stale_ids),
    }
