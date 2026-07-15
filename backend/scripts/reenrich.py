"""One-off: re-run public contact enrichment over channels already in the DB.

Parses each channel's stored description for a public email / website / socials
and fills any missing fields. Safe to run repeatedly (idempotent).

    python -m scripts.reenrich
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.agents.enrichment import extract_contacts
from app.core.db import SessionLocal
from app.domain.models import Channel


async def main() -> None:
    updated = 0
    async with SessionLocal() as session:
        channels = (await session.execute(select(Channel))).scalars().all()
        for ch in channels:
            found = extract_contacts(ch.description or "")
            changed = False
            if not ch.public_email and found["public_email"]:
                ch.public_email = found["public_email"]
                changed = True
            if not ch.website and found["website"]:
                ch.website = found["website"]
                changed = True
            if found["social_links"]:
                merged = {**found["social_links"], **(ch.social_links or {})}
                if merged != (ch.social_links or {}):
                    ch.social_links = merged
                    changed = True
            if changed:
                updated += 1
        await session.commit()
    print(f"re-enriched {updated}/{len(channels)} channels")


if __name__ == "__main__":
    asyncio.run(main())
