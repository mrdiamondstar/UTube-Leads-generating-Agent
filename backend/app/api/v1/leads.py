"""Leads + overview endpoints for the dashboard."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user, get_optional_user
from app.core.db import get_session
from app.domain.models import User, Video
from app.domain.schemas import (
    ChannelOut,
    LeadDetailOut,
    LeadOut,
    LeadScoreOut,
    LeadStatusOut,
    LeadStatusUpdate,
    VideoOut,
)
from app.repositories.leads import LeadRepository
from app.services.excel import build_leads_workbook

_XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

router = APIRouter()


@router.get("/leads", response_model=list[LeadOut])
async def list_leads(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    category: str | None = Query(None, pattern="^(hot|warm|cold|disqualified)$"),
    niche: list[str] | None = Query(None),
    run_id: list[str] | None = Query(None),
    status: str | None = Query(None, pattern="^(active|interested|closed|rejected)$"),
    underperforming: bool = Query(False),
    session: AsyncSession = Depends(get_session),
    user: User | None = Depends(get_optional_user),
) -> list[LeadOut]:
    repo = LeadRepository(session)
    user_id = user.id if user else None
    pairs = await repo.list_leads(
        limit=limit,
        offset=offset,
        category=category,
        niches=niche,
        run_ids=run_id,
        user_id=user_id,
        status=status,
        underperforming=underperforming,
    )
    channel_ids = [c.id for c, _ in pairs]
    latest = await repo.latest_videos(channel_ids)
    niche_by_run = await repo.niche_by_run({s.run_id for _, s in pairs})
    status_map = await repo.status_by_channel(user_id, channel_ids)
    return [
        LeadOut(
            channel=ChannelOut.model_validate(channel),
            score=LeadScoreOut.model_validate(score),
            latest_video=(
                VideoOut.model_validate(latest[channel.id])
                if channel.id in latest
                else None
            ),
            niche=niche_by_run.get(score.run_id),
            status=status_map.get(channel.id, "active"),
        )
        for channel, score in pairs
    ]


@router.put("/leads/{channel_id}/status", response_model=LeadStatusOut)
async def set_lead_status(
    channel_id: str,
    body: LeadStatusUpdate,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LeadStatusOut:
    """Set the current user's outreach status for a lead (channel)."""
    repo = LeadRepository(session)
    if await repo.get_channel(channel_id) is None:
        raise HTTPException(status_code=404, detail="channel not found")
    status = await repo.set_status(current.id, channel_id, body.status)
    return LeadStatusOut(channel_id=channel_id, status=status)


# NOTE: static path "/leads/export" MUST be declared before the dynamic
# "/leads/{channel_id}" route, otherwise "export" is captured as a channel id.
@router.get("/leads/export")
async def export_leads(
    category: str | None = Query(None, pattern="^(hot|warm|cold|disqualified)$"),
    niche: list[str] | None = Query(None),
    run_id: list[str] | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Download all scored leads as a formatted Excel (.xlsx) workbook."""
    repo = LeadRepository(session)
    pairs = await repo.list_leads(
        limit=100000, category=category, niches=niche, run_ids=run_id
    )
    latest = await repo.latest_videos([c.id for c, _ in pairs])
    content = build_leads_workbook(pairs, latest_videos=latest)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    filename = f"cip_leads_{stamp}.xlsx"
    return Response(
        content=content,
        media_type=_XLSX_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/leads/{channel_id}", response_model=ChannelOut)
async def get_channel(channel_id: str, session: AsyncSession = Depends(get_session)) -> ChannelOut:
    repo = LeadRepository(session)
    channel = await repo.get_channel(channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="channel not found")
    return ChannelOut.model_validate(channel)


@router.get("/leads/{channel_id}/detail", response_model=LeadDetailOut)
async def lead_detail(
    channel_id: str, session: AsyncSession = Depends(get_session)
) -> LeadDetailOut:
    repo = LeadRepository(session)
    channel = await repo.get_channel(channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="channel not found")
    score = await repo.latest_score(channel_id)
    videos = await repo.videos_for(channel_id)
    return LeadDetailOut(
        channel=ChannelOut.model_validate(channel),
        score=LeadScoreOut.model_validate(score) if score else None,
        videos=[VideoOut.model_validate(v) for v in videos],
    )


@router.get("/leads/{channel_id}/videos", response_model=list[VideoOut])
async def channel_videos(
    channel_id: str, session: AsyncSession = Depends(get_session)
) -> list[VideoOut]:
    rows = await session.execute(
        select(Video)
        .where(Video.channel_id == channel_id)
        .order_by(Video.published_at.desc())
    )
    return [VideoOut.model_validate(v) for v in rows.scalars().all()]


@router.get("/overview")
async def overview(session: AsyncSession = Depends(get_session)) -> dict:
    repo = LeadRepository(session)
    return await repo.overview()
