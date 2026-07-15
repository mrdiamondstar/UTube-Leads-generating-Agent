"""Integration test: run the full agent pipeline against the mock provider."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.agents.manager import ManagerAgent
from app.core.config import get_settings
from app.domain.models import Channel, LeadScore, PipelineRun, Video


@pytest.mark.asyncio
async def test_pipeline_persists_and_excludes_india(session):
    settings = get_settings()
    run = PipelineRun(query="tech reviews", stats={"max_results": 40})
    session.add(run)
    await session.flush()

    manager = ManagerAgent(session, settings)
    await manager.run(run)
    await session.commit()

    assert run.status == "done"
    assert run.discovered > 0

    channels = (await session.execute(select(Channel))).scalars().all()
    scores = (await session.execute(select(LeadScore))).scalars().all()
    assert len(channels) == run.discovered
    assert len(scores) == run.discovered

    # Country validation: any India-based channel must be disqualified.
    by_channel = {c.id: c for c in channels}
    for s in scores:
        if by_channel[s.channel_id].country == "IN":
            assert s.category == "disqualified"

    # Recent videos are fetched + stored for non-excluded channels.
    videos = (await session.execute(select(Video))).scalars().all()
    assert len(videos) > 0
    excluded_channel_ids = {c.id for c in channels if c.country == "IN"}
    assert all(v.channel_id not in excluded_channel_ids for v in videos)


@pytest.mark.asyncio
async def test_pipeline_is_idempotent_on_repeat(session):
    settings = get_settings()
    for _ in range(2):
        run = PipelineRun(query="same query", stats={"max_results": 20})
        session.add(run)
        await session.flush()
        await ManagerAgent(session, settings).run(run)
        await session.commit()

    # Same deterministic query -> channels upserted, not duplicated.
    channels = (await session.execute(select(Channel))).scalars().all()
    assert len(channels) == 20
