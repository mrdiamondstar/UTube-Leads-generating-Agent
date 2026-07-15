"""Leads + overview endpoints for the dashboard."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.domain.models import Video
from app.domain.schemas import (
    ChannelOut,
    LeadDetailOut,
    LeadOut,
    LeadScoreOut,
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
    session: AsyncSession = Depends(get_session),
) -> list[LeadOut]:
    repo = LeadRepository(session)
    pairs = await repo.list_leads(limit=limit, offset=offset, category=category)
    latest = await repo.latest_videos([c.id for c, _ in pairs])
    return [
        LeadOut(
            channel=ChannelOut.model_validate(channel),
            score=LeadScoreOut.model_validate(score),
            latest_video=(
                VideoOut.model_validate(latest[channel.id])
                if channel.id in latest
                else None
            ),
        )
        for channel, score in pairs
    ]


# NOTE: static path "/leads/export" MUST be declared before the dynamic
# "/leads/{channel_id}" route, otherwise "export" is captured as a channel id.
@router.get("/leads/export")
async def export_leads(
    category: str | None = Query(None, pattern="^(hot|warm|cold|disqualified)$"),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Download all scored leads as a formatted Excel (.xlsx) workbook."""
    repo = LeadRepository(session)
    pairs = await repo.list_leads(limit=100000, category=category)
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
