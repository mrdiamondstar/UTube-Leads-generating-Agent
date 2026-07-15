"""Niche catalog endpoint (database-driven, seeds itself if empty)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.domain.models import Niche
from app.domain.schemas import NicheOut
from app.niches.seed import count_niches, seed_niches

router = APIRouter()


@router.get("/niches", response_model=list[NicheOut])
async def list_niches(
    q: str | None = Query(default=None, description="Case-insensitive name search"),
    category: str | None = Query(default=None),
    recommended: bool | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> list[Niche]:
    # Lazily seed so a fresh database still returns the curated catalog.
    if await count_niches(session) == 0:
        await seed_niches(session)

    stmt = select(Niche)
    if q:
        stmt = stmt.where(Niche.name.ilike(f"%{q}%"))
    if category:
        stmt = stmt.where(Niche.category == category)
    if recommended is not None:
        stmt = stmt.where(Niche.recommended.is_(recommended))
    stmt = stmt.order_by(Niche.category, Niche.popularity.desc(), Niche.name)

    rows = await session.execute(stmt)
    return list(rows.scalars().all())
