"""Read-side repository for channels + their latest lead score (CQRS-ish)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Channel, LeadScore, PipelineRun, Video


class LeadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_leads(
        self, *, limit: int = 50, offset: int = 0, category: str | None = None
    ) -> list[tuple[Channel, LeadScore]]:
        """Return (channel, latest_score) pairs, newest score first."""
        # Latest score per channel via a correlated subquery on created_at.
        # correlate(Channel) keeps lead_scores in the subquery's FROM while
        # binding channel_id to the outer Channel row.
        latest = (
            select(LeadScore.id)
            .where(LeadScore.channel_id == Channel.id)
            .order_by(LeadScore.created_at.desc())
            .limit(1)
            .correlate(Channel)
            .scalar_subquery()
        )
        stmt = (
            select(Channel, LeadScore)
            .join(LeadScore, LeadScore.id == latest)
            .order_by(LeadScore.score.desc())
        )
        if category:
            stmt = stmt.where(LeadScore.category == category)
        stmt = stmt.limit(limit).offset(offset)

        rows = await self.session.execute(stmt)
        return [(c, s) for c, s in rows.all()]

    async def latest_videos(self, channel_ids: list[str]) -> dict[str, Video]:
        """Most-recently-published video per channel (by published_at)."""
        if not channel_ids:
            return {}
        rows = (
            await self.session.execute(
                select(Video)
                .where(Video.channel_id.in_(channel_ids))
                .order_by(Video.published_at.desc().nullslast())
            )
        ).scalars().all()
        latest: dict[str, Video] = {}
        for v in rows:
            latest.setdefault(v.channel_id, v)  # first seen = newest
        return latest

    async def get_channel(self, channel_id: str) -> Channel | None:
        return (
            await self.session.execute(select(Channel).where(Channel.id == channel_id))
        ).scalar_one_or_none()

    async def latest_score(self, channel_id: str) -> LeadScore | None:
        return (
            await self.session.execute(
                select(LeadScore)
                .where(LeadScore.channel_id == channel_id)
                .order_by(LeadScore.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def videos_for(self, channel_id: str) -> list[Video]:
        rows = await self.session.execute(
            select(Video)
            .where(Video.channel_id == channel_id)
            .order_by(Video.published_at.desc().nullslast())
        )
        return list(rows.scalars().all())

    async def overview(self) -> dict:
        """Aggregate counts for the dashboard Overview page."""
        channels = (await self.session.execute(select(Channel))).scalars().all()
        scores = (await self.session.execute(select(LeadScore))).scalars().all()

        latest_by_channel: dict[str, LeadScore] = {}
        for s in scores:
            cur = latest_by_channel.get(s.channel_id)
            if cur is None or s.created_at > cur.created_at:
                latest_by_channel[s.channel_id] = s

        by_category: dict[str, int] = {}
        underperforming = 0
        for s in latest_by_channel.values():
            by_category[s.category] = by_category.get(s.category, 0) + 1
            if s.is_underperforming:
                underperforming += 1

        return {
            "total_channels": len(channels),
            "total_scored": len(latest_by_channel),
            "underperforming": underperforming,
            "by_category": by_category,
            "recent_runs": await self._recent_runs(),
        }

    async def _recent_runs(self, limit: int = 8) -> list[dict]:
        """Last N completed runs (oldest→newest) for sparklines/trend deltas."""
        rows = (
            await self.session.execute(
                select(PipelineRun)
                .where(PipelineRun.status == "done")
                .order_by(PipelineRun.created_at.desc())
                .limit(limit)
            )
        ).scalars().all()
        series = []
        for r in reversed(rows):  # oldest first
            stats = r.stats or {}
            cats = stats.get("categories", {}) if isinstance(stats, dict) else {}
            series.append(
                {
                    "discovered": r.discovered,
                    "qualified": r.qualified,
                    "underperforming": stats.get("underperforming", 0),
                    "hot": cats.get("hot", 0),
                }
            )
        return series
