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
async def test_pipeline_disqualifies_inactive_creators(session):
    """Creators whose most recent upload is older than the activity window are
    disqualified, regardless of their metrics."""
    from datetime import datetime, timedelta, timezone

    from app.domain.schemas import RawVideo

    settings = get_settings()
    run = PipelineRun(query="tech reviews", stats={"max_results": 20})
    session.add(run)
    await session.flush()

    manager = ManagerAgent(session, settings)

    # Force every channel's latest upload to be ~1 year ago (well outside the
    # 180-day window), so the activity rule should disqualify them.
    stale = datetime.now(timezone.utc) - timedelta(days=365)

    async def _stale_videos(uploads_playlist_id, channel_youtube_id, max_results=10):
        return [
            RawVideo(
                video_id=f"old-{channel_youtube_id}",
                channel_youtube_id=channel_youtube_id,
                title="an old video",
                published_at=stale,
                view_count=1000,
                like_count=10,
                comment_count=1,
            )
        ]

    manager.provider.get_recent_videos = _stale_videos

    await manager.run(run)
    await session.commit()

    channels = {
        c.id: c for c in (await session.execute(select(Channel))).scalars().all()
    }
    scores = (await session.execute(select(LeadScore))).scalars().all()

    # Channels that reached the activity check (non-India) must be disqualified
    # for inactivity.
    non_india = [s for s in scores if channels[s.channel_id].country != "IN"]
    assert non_india, "expected at least one non-country-excluded channel"
    assert all(s.category == "disqualified" for s in non_india)
    assert all("inactive" in (s.reasoning or "") for s in non_india)
    assert run.stats.get("inactive", 0) > 0


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
