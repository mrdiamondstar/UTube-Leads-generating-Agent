"""Seed the niches table from the catalog (idempotent)."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domain.models import Niche
from app.niches.catalog import iter_catalog

log = get_logger("niches.seed")


async def seed_niches(session: AsyncSession) -> int:
    """Bring the niches table in line with the catalog. Returns count added.

    Inserts anything missing and refreshes category/popularity/recommended on
    rows that already exist — the catalog is the source of truth, so re-ranking
    it there has to reach a database that was seeded from an older version.
    """
    existing = {
        n.name: n for n in (await session.execute(select(Niche))).scalars().all()
    }
    added = 0
    changed = 0
    for name, category, popularity, recommended in iter_catalog():
        row = existing.get(name)
        if row is None:
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
            continue
        if (row.category, row.popularity, row.recommended) != (
            category,
            popularity,
            recommended,
        ):
            row.category = category
            row.popularity = popularity
            row.recommended = recommended
            changed += 1
    if added or changed:
        await session.commit()
        log.info("niches.seeded", added=added, updated=changed)
    return added


async def count_niches(session: AsyncSession) -> int:
    return (await session.execute(select(func.count()).select_from(Niche))).scalar_one()
