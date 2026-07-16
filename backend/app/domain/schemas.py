"""Pydantic schemas — API contracts and inter-agent DTOs."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.common.countries import country_name


# ---------- Provider / discovery DTOs (agent-internal) ----------
class RawChannel(BaseModel):
    """Normalized channel as returned by a YouTube provider."""

    youtube_id: str
    title: str
    description: str = ""
    country: str | None = None
    category: str | None = None
    subscriber_count: int = 0
    view_count: int = 0
    video_count: int = 0
    default_language: str | None = None  # snippet.defaultLanguage (e.g. "en")
    uploads_playlist_id: str | None = None  # contentDetails.relatedPlaylists.uploads
    website: str | None = None
    public_email: str | None = None
    social_links: dict[str, str] = Field(default_factory=dict)


class RawVideo(BaseModel):
    """Normalized video (recent uploads + statistics) from a provider."""

    video_id: str
    channel_youtube_id: str
    title: str = ""
    published_at: datetime | None = None
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0


# ---------- API response models ----------
class ChannelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    youtube_id: str
    title: str
    country: str | None
    category: str | None
    subscriber_count: int
    view_count: int
    video_count: int
    website: str | None
    public_email: str | None
    social_links: dict[str, str]

    @computed_field
    @property
    def country_name(self) -> str | None:
        return country_name(self.country)

    @computed_field
    @property
    def youtube_url(self) -> str:
        return f"https://www.youtube.com/channel/{self.youtube_id}"


class VideoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    channel_id: str
    youtube_video_id: str
    title: str
    published_at: datetime | None
    view_count: int
    like_count: int
    comment_count: int

    @computed_field
    @property
    def youtube_url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.youtube_video_id}"


_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    email: str = Field(..., pattern=_EMAIL_PATTERN)
    password: str = Field(..., min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(..., pattern=_EMAIL_PATTERN)
    password: str = Field(..., min_length=1, max_length=128)


class UpdateProfileRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=2_000_000)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str
    avatar_url: str | None
    created_at: datetime


class AuthTokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class PlanOut(BaseModel):
    id: str
    name: str
    interval: str
    period_days: int
    amount_cents: int
    amount: float
    per_day_cents: int
    currency: str
    tagline: str
    features: list[str]
    highlight: bool
    badge: str | None


class SubscribeRequest(BaseModel):
    plan_id: str = Field(..., min_length=1)
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class BillingConfigOut(BaseModel):
    enabled: bool
    provider: str = "razorpay"
    key_id: str | None = None
    currency: str = "INR"


class CheckoutRequest(BaseModel):
    plan_id: str = Field(..., min_length=1)
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class CheckoutOut(BaseModel):
    order_id: str
    amount: int
    currency: str
    key_id: str
    plan_id: str
    plan_name: str
    email: str


class VerifyPaymentRequest(BaseModel):
    plan_id: str = Field(..., min_length=1)
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_email: str
    plan_id: str
    interval: str
    amount_cents: int
    currency: str
    status: str
    started_at: datetime
    current_period_end: datetime


class NicheOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    category: str
    popularity: int
    recommended: bool
    language: str
    created_at: datetime


class QuotaOut(BaseModel):
    date: str
    units_used: int
    daily_quota: int
    remaining: int
    calls: dict[str, int]


class LeadScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    channel_id: str
    score: float
    confidence: float
    category: str
    is_underperforming: bool
    feature_contributions: dict
    reasoning: str
    created_at: datetime


class LeadStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(active|interested|closed|rejected)$")


class LeadStatusOut(BaseModel):
    channel_id: str
    status: str


class LeadOut(BaseModel):
    """A joined view: channel + its latest score + latest video, for the dashboard."""

    channel: ChannelOut
    score: LeadScoreOut
    latest_video: VideoOut | None = None
    niche: str | None = None  # the discovery query (niche) the latest score came from
    status: str = "active"  # per-user outreach status (default when unset)


class LeadDetailOut(BaseModel):
    """Full channel profile: channel + latest score + recent videos."""

    channel: ChannelOut
    score: LeadScoreOut | None = None
    videos: list[VideoOut] = Field(default_factory=list)


# ---------- Pipeline API ----------
class PipelineRunRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=255)
    max_results: int = Field(default=25, ge=1, le=200)
    run_async: bool = Field(default=False, description="Dispatch to Celery instead of running inline")
    force: bool = Field(
        default=False,
        description="Bypass the recent-discovery reuse guard and always call the API",
    )


class PipelineRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    query: str
    status: str
    discovered: int
    qualified: int
    error: str | None
    stats: dict
    created_at: datetime
    finished_at: datetime | None
    reused: bool = False  # true when returned from the recent-discovery reuse guard
