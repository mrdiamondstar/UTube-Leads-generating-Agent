"""SQLAlchemy ORM models (normalized schema for the Phase 1 slice).

Bounded contexts represented here:
- Channel (creator identity + latest stats)
- ChannelSnapshot (time-series of metrics for trend analysis)
- LeadScore (explainable scoring output)
- PipelineRun (audit trail of an orchestrated agent run)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    youtube_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    country: Mapped[str | None] = mapped_column(String(4), index=True, nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)

    subscriber_count: Mapped[int] = mapped_column(Integer, default=0)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    video_count: Mapped[int] = mapped_column(Integer, default=0)

    # Publicly discoverable business info (enrichment; Phase 2 fills more)
    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    public_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    social_links: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    uploads_playlist_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    snapshots: Mapped[list["ChannelSnapshot"]] = relationship(
        back_populates="channel", cascade="all, delete-orphan"
    )
    lead_scores: Mapped[list["LeadScore"]] = relationship(
        back_populates="channel", cascade="all, delete-orphan"
    )
    videos: Mapped[list["Video"]] = relationship(
        back_populates="channel", cascade="all, delete-orphan"
    )


class ChannelSnapshot(Base):
    """A point-in-time capture of a channel's metrics (for trend/momentum analysis)."""

    __tablename__ = "channel_snapshots"
    __table_args__ = (UniqueConstraint("channel_id", "captured_at", name="uq_snapshot"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    channel_id: Mapped[str] = mapped_column(ForeignKey("channels.id", ondelete="CASCADE"))
    subscriber_count: Mapped[int] = mapped_column(Integer, default=0)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    video_count: Mapped[int] = mapped_column(Integer, default=0)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    channel: Mapped["Channel"] = relationship(back_populates="snapshots")


class Video(Base):
    """A recent upload with its statistics (from the YouTube Data API)."""

    __tablename__ = "videos"
    __table_args__ = (UniqueConstraint("youtube_video_id", name="uq_video_yt_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    channel_id: Mapped[str] = mapped_column(ForeignKey("channels.id", ondelete="CASCADE"))
    youtube_video_id: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(512), default="")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    channel: Mapped["Channel"] = relationship(back_populates="videos")


class ApiQuotaUsage(Base):
    """Daily YouTube Data API quota accounting (observability / cost control)."""

    __tablename__ = "api_quota_usage"

    day: Mapped[str] = mapped_column(String(10), primary_key=True)  # YYYY-MM-DD (UTC)
    units_used: Mapped[int] = mapped_column(Integer, default=0)
    calls: Mapped[dict] = mapped_column(JSON, default=dict)  # {endpoint: count}
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class LeadScore(Base):
    """Explainable lead score with per-feature contributions and reasoning."""

    __tablename__ = "lead_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    channel_id: Mapped[str] = mapped_column(ForeignKey("channels.id", ondelete="CASCADE"))
    run_id: Mapped[str | None] = mapped_column(
        ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True
    )

    score: Mapped[float] = mapped_column(Float, default=0.0)  # 0..100
    confidence: Mapped[float] = mapped_column(Float, default=0.0)  # 0..1
    category: Mapped[str] = mapped_column(String(32), default="cold")  # hot/warm/cold/disqualified
    is_underperforming: Mapped[bool] = mapped_column(default=False)

    # Explainability: {feature: {value, weight, contribution}}
    feature_contributions: Mapped[dict] = mapped_column(JSON, default=dict)
    reasoning: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    channel: Mapped["Channel"] = relationship(back_populates="lead_scores")


class Niche(Base):
    """A curated, recommendable YouTube niche (backend/database-driven)."""

    __tablename__ = "niches"
    __table_args__ = (UniqueConstraint("name", name="uq_niche_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    popularity: Mapped[int] = mapped_column(Integer, default=0)
    recommended: Mapped[bool] = mapped_column(default=False)
    language: Mapped[str] = mapped_column(String(8), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class User(Base):
    """An authenticated dashboard user (email + password)."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)  # data URL or link
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Subscription(Base):
    """A customer's subscription to a plan (daily/weekly/monthly).

    Payment provider integration (e.g. Stripe) plugs in later; this records the
    subscription lifecycle and the billing period.
    """

    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    customer_email: Mapped[str] = mapped_column(String(255), index=True)
    plan_id: Mapped[str] = mapped_column(String(32))
    interval: Mapped[str] = mapped_column(String(16))  # day/week/month
    amount_cents: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    status: Mapped[str] = mapped_column(String(16), default="active")  # active/canceled/expired
    provider: Mapped[str] = mapped_column(String(32), default="manual")
    payment_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)  # razorpay_payment_id

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class PipelineRun(Base):
    """Audit record of a single orchestrated Manager-agent run."""

    __tablename__ = "pipeline_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    query: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending/running/done/failed
    discovered: Mapped[int] = mapped_column(Integer, default=0)
    qualified: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    stats: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
