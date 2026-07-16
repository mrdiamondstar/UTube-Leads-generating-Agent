"""Read-side repository for channels + their latest lead score (CQRS-ish)."""
from __future__ import annotations

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.domain.models import Channel, LeadScore, LeadStatus, PipelineRun, Video


class LeadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_leads(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        category: str | None = None,
        niches: list[str] | None = None,
        run_ids: list[str] | None = None,
        user_id: str | None = None,
        status: str | None = None,
        underperforming: bool = False,
    ) -> list[tuple[Channel, LeadScore]]:
        """Return (channel, latest_score) pairs, newest score first.

        Filtering (most specific wins):
        - ``run_ids``: only channels whose *latest* score came from one of these
          discovery runs. This powers "show only the current search" on the
          Leads page — precise, and never includes previous discoveries.
        - ``niches``: only channels whose latest score's run was for one of these
          niches (matched via LeadScore.run_id -> PipelineRun.query).
        - ``status`` (with ``user_id``): filter by the user's outreach status.
          "active" also matches leads the user has never touched (no row).
        """
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
        if run_ids:
            stmt = stmt.where(LeadScore.run_id.in_(run_ids))
        elif niches:
            stmt = stmt.join(PipelineRun, PipelineRun.id == LeadScore.run_id).where(
                PipelineRun.query.in_(niches)
            )
        if category:
            stmt = stmt.where(LeadScore.category == category)
        if underperforming:
            stmt = stmt.where(LeadScore.is_underperforming.is_(True))
        if status and user_id:
            ls = aliased(LeadStatus)
            stmt = stmt.outerjoin(
                ls, and_(ls.channel_id == Channel.id, ls.user_id == user_id)
            )
            if status == "active":
                stmt = stmt.where(or_(ls.status.is_(None), ls.status == "active"))
            else:
                stmt = stmt.where(ls.status == status)
        stmt = stmt.limit(limit).offset(offset)

        rows = await self.session.execute(stmt)
        return [(c, s) for c, s in rows.all()]

    async def status_by_channel(
        self, user_id: str | None, channel_ids: list[str]
    ) -> dict[str, str]:
        """Map channel id -> the user's outreach status (only channels with a row)."""
        if not user_id or not channel_ids:
            return {}
        rows = await self.session.execute(
            select(LeadStatus.channel_id, LeadStatus.status).where(
                LeadStatus.user_id == user_id,
                LeadStatus.channel_id.in_(channel_ids),
            )
        )
        return {cid: st for cid, st in rows.all()}

    async def set_status(self, user_id: str, channel_id: str, status: str) -> str:
        """Upsert the user's outreach status for a channel; returns the status."""
        row = (
            await self.session.execute(
                select(LeadStatus).where(
                    LeadStatus.user_id == user_id,
                    LeadStatus.channel_id == channel_id,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            row = LeadStatus(user_id=user_id, channel_id=channel_id, status=status)
            self.session.add(row)
        else:
            row.status = status
        await self.session.flush()
        return row.status

    async def niche_by_run(self, run_ids: set[str]) -> dict[str, str]:
        """Map pipeline run id -> its niche/query (for labelling leads)."""
        ids = [r for r in run_ids if r]
        if not ids:
            return {}
        rows = await self.session.execute(
            select(PipelineRun.id, PipelineRun.query).where(PipelineRun.id.in_(ids))
        )
        return {rid: q for rid, q in rows.all()}

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
        """Aggregate counts for the dashboard Overview page.

        Counts are computed *in the database* (one COUNT + one grouped aggregate
        over each channel's latest score) instead of loading every row into the
        app — far less data over the wire, which matters across regions.
        """
        total_channels = (
            await self.session.execute(select(func.count(Channel.id)))
        ).scalar() or 0

        # Rank scores newest-first within each channel, then aggregate row 1.
        rn = func.row_number().over(
            partition_by=LeadScore.channel_id,
            order_by=LeadScore.created_at.desc(),
        ).label("rn")
        latest = select(
            LeadScore.category.label("category"),
            LeadScore.is_underperforming.label("under"),
            rn,
        ).subquery()
        rows = (
            await self.session.execute(
                select(latest.c.category, latest.c.under, func.count().label("n"))
                .where(latest.c.rn == 1)
                .group_by(latest.c.category, latest.c.under)
            )
        ).all()

        by_category: dict[str, int] = {}
        total_scored = 0
        underperforming = 0
        for category, under, n in rows:
            by_category[category] = by_category.get(category, 0) + n
            total_scored += n
            if under:
                underperforming += n

        return {
            "total_channels": total_channels,
            "total_scored": total_scored,
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
