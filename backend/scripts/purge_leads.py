"""One-off: delete every discovered creator record, keeping accounts and config.

Clears the tables the pipeline writes to — channels with their videos, snapshots,
scores and outreach statuses — plus the pipeline run history. Users, the niche
catalog, subscriptions and quota accounting are left untouched.

Written for the switch from the mock provider to the real YouTube API, where
leaving fabricated channels behind would mix test doubles into real results.

Clearing the run history matters as much as clearing the channels: the reuse
guard serves any niche discovered within DISCOVERY_REUSE_HOURS straight from
that history, so a surviving mock run would make the first *real* search for
that niche return the old empty result instead of calling YouTube.

Dry run by default; pass --yes to actually delete.

    python -m scripts.purge_leads
    python -m scripts.purge_leads --yes
"""
from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import delete, func, select

from app.core.db import SessionLocal
from app.domain.models import (
    Channel,
    ChannelSnapshot,
    LeadScore,
    LeadStatus,
    PipelineRun,
    Video,
)

# Dependents before their parents: lead_scores references channels *and*
# pipeline_runs, so both parents have to come after it.
_ORDER = (LeadStatus, LeadScore, Video, ChannelSnapshot, Channel, PipelineRun)


async def main(confirmed: bool) -> None:
    async with SessionLocal() as session:
        counts = {}
        for model in _ORDER:
            counts[model.__tablename__] = (
                await session.execute(select(func.count()).select_from(model))
            ).scalar_one()

        total = sum(counts.values())
        for name, n in counts.items():
            print(f"  {name:<20}{n:>9}")
        print(f"  {'total':<20}{total:>9}")

        if total == 0:
            print("\nAlready empty; nothing to do.")
            return

        if not confirmed:
            print("\nDry run — nothing deleted. Re-run with --yes to apply.")
            return

        for model in _ORDER:
            await session.execute(delete(model))
        await session.commit()
        print(f"\nDeleted {total} rows. Users, niches and quota history kept.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Purge discovered creator data.")
    parser.add_argument("--yes", action="store_true", help="perform the deletion")
    asyncio.run(main(parser.parse_args().yes))
