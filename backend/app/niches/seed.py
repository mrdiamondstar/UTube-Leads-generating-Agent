"""Seed the niches table from the catalog (idempotent)."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domain.models import Niche
from app.niches.catalog import iter_catalog

log = get_logger("niches.seed")


async def seed_niches(session: AsyncSession) -> int:
    """Insert catalog niches that are not already present. Returns count added."""
    existing = set(
        (await session.execute(select(Niche.name))).scalars().all()
    )
    added = 0
    for name, category, popularity, recommended in iter_catalog():
        if name in existing:
            continue
        session.add(
            Niche(
                name=name,
                category=category,
                popularity=popularity,
                recommended=recommended,
                language="en",
            )
        )
        added += 1
    if added:
        await session.commit()
        log.info("niches.seeded", added=added)
    return added


async def count_niches(session: AsyncSession) -> int:
    return (await session.execute(select(func.count()).select_from(Niche))).scalar_one()
