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

from app.api.v1.auth import get_current_user
from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.core.logging import get_logger
from app.domain.models import (
    Channel,
    ChannelSnapshot,
    LeadScore,
    LeadStatus,
    PipelineRun,
    User,
    Video,
)

router = APIRouter()
log = get_logger("maintenance")

# Dependents before their parents: lead_scores references channels *and*
# pipeline_runs, so both parents have to be deleted after it.
_PURGE_ORDER = (LeadStatus, LeadScore, Video, ChannelSnapshot, Channel, PipelineRun)


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


@router.post("/maintenance/reset")
async def reset_dashboard(
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Delete every discovered creator record, returning the dashboard to empty.

    Clears channels with their videos, snapshots, scores and outreach statuses,
    plus the pipeline run history. Accounts, the niche catalog, subscriptions
    and quota accounting survive.

    The run history is cleared alongside the channels deliberately: the reuse
    guard serves any niche discovered inside the reuse window straight from that
    history, so leaving it behind would make the next discovery for those niches
    return the stale empty result instead of calling YouTube.

    Creator data is shared across accounts in this deployment, so this clears it
    for everyone — not only the caller.
    """
    deleted: dict[str, int] = {}
    for model in _PURGE_ORDER:
        result = await session.execute(delete(model))
        deleted[model.__tablename__] = result.rowcount or 0

    total = sum(deleted.values())
    log.warning("maintenance.reset", by=current.email, total=total, deleted=deleted)
    return {"deleted": deleted, "total": total}
