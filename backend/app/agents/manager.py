"""Manager Agent — orchestrates the discovery→scoring pipeline and persists results.

Sequence:
    Discovery -> Channel Analysis -> Performance -> Country Validation ->
    Scoring -> (per channel) Recent Videos + Activity check -> persist

The activity check disqualifies creators whose most recent upload is older than
`settings.active_within_days` (default ~6 months), so stale/abandoned channels
never surface as leads.

Persistence is idempotent per channel (upsert by youtube_id) and per video
(upsert by youtube_video_id). Records a PipelineRun audit row and persists the
YouTube API quota snapshot to `api_quota_usage`.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.channel_analysis import ChannelAnalysisAgent
from app.agents.country_validation import CountryValidationAgent
from app.agents.discovery import DiscoveryAgent
from app.agents.enrichment import PublicContactEnrichmentAgent
from app.agents.performance import PerformanceAnalysisAgent
from app.agents.scoring import OpportunityScoringAgent
from app.core.config import Settings
from app.core.logging import get_logger
from app.domain.models import ApiQuotaUsage, Channel, ChannelSnapshot, LeadScore, PipelineRun, Video
from app.integrations.youtube import build_youtube_provider
from app.integrations.youtube.errors import QuotaExceededError
from app.integrations.youtube.quota import get_quota_tracker

log = get_logger("agent.manager")


class ManagerAgent:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.provider = build_youtube_provider(settings)
        self.discovery = DiscoveryAgent(
            self.provider,
            settings.min_subscribers,
            settings.english_only,
            settings.max_subscribers,
        )
        self.enrichment = PublicContactEnrichmentAgent()
        self.channel_analysis = ChannelAnalysisAgent()
        self.performance = PerformanceAnalysisAgent(settings.underperformance_ratio)
        self.country = CountryValidationAgent(settings.excluded_country_set)
        self.scoring = OpportunityScoringAgent()

    async def run(self, run: PipelineRun) -> PipelineRun:
        run.status = "running"
        await self.session.flush()

        max_results = (run.stats or {}).get("max_results", 25)
        quota_stopped = False

        try:
            contexts = await self.discovery.run((run.query, max_results))
            contexts = await self.enrichment.run(contexts)
            contexts = await self.channel_analysis.run(contexts)
            contexts = await self.performance.run(contexts)
            contexts = await self.country.run(contexts)
            contexts = await self.scoring.run(contexts)

            qualified = 0
            videos_stored = 0
            inactive = 0
            cutoff = (
                datetime.now(timezone.utc)
                - timedelta(days=self.settings.active_within_days)
                if self.settings.active_within_days > 0
                else None
            )
            for ctx in contexts:
                channel = await self._upsert_channel(ctx)
                self.session.add(
                    ChannelSnapshot(
                        channel_id=channel.id,
                        subscriber_count=channel.subscriber_count,
                        view_count=channel.view_count,
                        video_count=channel.video_count,
                    )
                )

                # Fetch recent videos only for non-excluded channels (saves
                # quota — we never spend units on already-disqualified creators).
                raw_videos: list = []
                activity_checked = False
                if not ctx.excluded and not quota_stopped and channel.uploads_playlist_id:
                    try:
                        raw_videos = await self.provider.get_recent_videos(
                            channel.uploads_playlist_id,
                            channel.youtube_id,
                            self.settings.youtube_recent_videos,
                        )
                        activity_checked = True
                    except QuotaExceededError as exc:
                        quota_stopped = True
                        log.warning("pipeline.quota_stop", run_id=run.id, error=str(exc))

                # Activity rule: disqualify creators with no upload inside the
                # window. Only applied when we actually fetched videos (so a
                # quota stop never falsely disqualifies unchecked channels).
                if activity_checked and cutoff is not None:
                    latest_upload = _latest_upload(raw_videos)
                    if latest_upload is None or latest_upload < cutoff:
                        ctx.excluded = True
                        ctx.exclusion_reason = (
                            f"inactive: no upload in the last "
                            f"{self.settings.active_within_days} days"
                        )
                        ctx.category = "disqualified"
                        ctx.is_underperforming = False
                        ctx.score = 0.0
                        ctx.confidence = 0.0
                        ctx.reasoning = ctx.exclusion_reason
                        inactive += 1

                self.session.add(
                    LeadScore(
                        channel_id=channel.id,
                        run_id=run.id,
                        score=ctx.score,
                        confidence=ctx.confidence,
                        category=ctx.category,
                        is_underperforming=ctx.is_underperforming,
                        feature_contributions=ctx.feature_contributions,
                        reasoning=ctx.reasoning,
                    )
                )

                if raw_videos:
                    videos_stored += await self._store_videos(channel, raw_videos)

                if not ctx.excluded and ctx.is_underperforming and ctx.category in ("hot", "warm"):
                    qualified += 1

            run.discovered = len(contexts)
            run.qualified = qualified
            run.status = "done"
            run.stats = {
                **(run.stats or {}),
                "excluded": sum(1 for c in contexts if c.excluded),
                "inactive": inactive,
                "underperforming": sum(1 for c in contexts if c.is_underperforming),
                "videos_stored": videos_stored,
                "quota_stopped": quota_stopped,
                "categories": _category_counts(contexts),
            }
            run.finished_at = datetime.now(timezone.utc)
            log.info(
                "pipeline.done",
                run_id=run.id,
                discovered=run.discovered,
                qualified=qualified,
                videos=videos_stored,
            )
        except Exception as exc:  # noqa: BLE001
            run.status = "failed"
            run.error = str(exc)
            run.finished_at = datetime.now(timezone.utc)
            log.error("pipeline.failed", run_id=run.id, error=str(exc))
            await self._persist_quota()
            raise
        finally:
            await self.provider.aclose()

        await self._persist_quota()
        await self.session.flush()
        return run

    async def _store_videos(self, channel: Channel, raw_videos: list) -> int:
        """Upsert already-fetched recent videos for a channel (idempotent).

        Existing videos are fetched in a single batched query (not one-per-video)
        to keep DB round-trips low — important when the DB is far from the app.
        """
        if not raw_videos:
            return 0
        ids = [rv.video_id for rv in raw_videos]
        existing_rows = (
            await self.session.execute(
                select(Video).where(Video.youtube_video_id.in_(ids))
            )
        ).scalars().all()
        existing = {v.youtube_video_id: v for v in existing_rows}
        now = datetime.now(timezone.utc)
        for rv in raw_videos:
            video = existing.get(rv.video_id)
            if video is None:
                video = Video(youtube_video_id=rv.video_id, channel_id=channel.id)
                self.session.add(video)
            video.channel_id = channel.id
            video.title = rv.title
            video.published_at = rv.published_at
            video.view_count = rv.view_count
            video.like_count = rv.like_count
            video.comment_count = rv.comment_count
            video.fetched_at = now
        await self.session.flush()
        return len(raw_videos)

    async def _upsert_channel(self, ctx) -> Channel:
        raw = ctx.raw
        existing = (
            await self.session.execute(
                select(Channel).where(Channel.youtube_id == raw.youtube_id)
            )
        ).scalar_one_or_none()

        if existing is None:
            channel = Channel(youtube_id=raw.youtube_id)
            self.session.add(channel)
        else:
            channel = existing

        channel.title = raw.title
        channel.description = raw.description or ""
        channel.country = raw.country
        channel.category = raw.category
        channel.subscriber_count = raw.subscriber_count
        channel.view_count = raw.view_count
        channel.video_count = raw.video_count
        channel.uploads_playlist_id = getattr(raw, "uploads_playlist_id", None)
        channel.website = raw.website
        channel.public_email = raw.public_email
        channel.social_links = raw.social_links or {}
        await self.session.flush()
        return channel

    async def _persist_quota(self) -> None:
        """Write the in-process quota snapshot to the DB (observability)."""
        snap = get_quota_tracker().snapshot()
        row = (
            await self.session.execute(
                select(ApiQuotaUsage).where(ApiQuotaUsage.day == snap["date"])
            )
        ).scalar_one_or_none()
        if row is None:
            row = ApiQuotaUsage(day=snap["date"])
            self.session.add(row)
        row.units_used = snap["units_used"]
        row.calls = snap["calls"]
        row.updated_at = datetime.now(timezone.utc)
        await self.session.flush()


def _category_counts(contexts) -> dict:
    counts: dict[str, int] = {}
    for c in contexts:
        counts[c.category] = counts.get(c.category, 0) + 1
    return counts


def _latest_upload(raw_videos: list) -> datetime | None:
    """Most recent upload timestamp across a channel's fetched videos."""
    dates = [
        v.published_at for v in raw_videos if getattr(v, "published_at", None) is not None
    ]
    return max(dates) if dates else None
