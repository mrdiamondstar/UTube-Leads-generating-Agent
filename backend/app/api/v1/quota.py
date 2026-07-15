"""YouTube API quota monitoring endpoint."""
from __future__ import annotations

from fastapi import APIRouter

from app.domain.schemas import QuotaOut
from app.integrations.youtube.quota import get_quota_tracker

router = APIRouter()


@router.get("/quota", response_model=QuotaOut)
async def quota() -> QuotaOut:
    """Current-day YouTube Data API quota consumption (in-process tracker)."""
    return QuotaOut(**get_quota_tracker().snapshot())
