"""Application configuration, loaded from environment (12-factor / config-driven)."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: str = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    secret_key: str = "dev-only-change-me-in-production-0123456789abcdef"

    # Database (async driver)
    database_url: str = "postgresql+asyncpg://cip:cip@localhost:5432/cip"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # YouTube provider. Default is the REAL YouTube Data API v3.
    # "mock" is a test double only (used by the test suite / offline dev).
    youtube_provider: str = "api"  # "api" | "mock"
    youtube_api_key: str = ""  # read from env YOUTUBE_API_KEY; never hardcode

    # YouTube API operational controls
    youtube_daily_quota: int = 10000          # default project quota (units/day)
    youtube_quota_safety_margin: int = 100    # stop before hitting the hard cap
    youtube_cache_ttl_seconds: int = 3600     # cache successful responses for 1h
    youtube_min_request_interval_ms: int = 25 # client-side rate limiting
    youtube_max_concurrency: int = 10         # max concurrent API calls
    youtube_max_retries: int = 4              # transient-error retries
    youtube_recent_videos: int = 5            # recent videos fetched per channel
    youtube_page_size: int = 50               # API hard cap per page

    # Razorpay (payments) — read from env; never hardcode.
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    razorpay_currency: str = "INR"

    # Business rules
    excluded_countries: str = "IN"
    underperformance_ratio: float = Field(default=0.5, ge=0.0, le=1.0)
    # Audience range: only consider creators within [min, max] subscribers.
    # Channels outside the range are dropped at discovery (never stored/scored).
    # Set either bound to 0 to disable it.
    min_subscribers: int = Field(default=1000, ge=0)
    max_subscribers: int = Field(default=900000, ge=0)  # 9 lakhs
    # Max leads that may be generated per (IST) day. Once reached, discovery
    # stops creating new leads until the next day. 0 (the default) means no cap
    # — the YouTube daily quota is then the only ceiling on a day's output.
    daily_lead_limit: int = Field(default=0, ge=0)
    # Language: when true, only consider English-language creators (detected from
    # the channel's declared language + title/description). Dropped at discovery.
    english_only: bool = True
    # Activity rule: a creator must have uploaded within this many days to
    # qualify as a lead (default ~6 months). Set to 0 to disable the check.
    active_within_days: int = Field(default=180, ge=0)

    # Recent-performance rule. Lifetime view totals hide decline — a channel that
    # was big years ago still reads as healthy while its new uploads get a few
    # hundred views. A creator qualifies only when the MEDIAN view count of their
    # recent videos falls below base + (subscribers x per_subscriber), capped.
    #   5,000 subs   -> under ~1,025 views
    #   300,000 subs -> under ~2,500 views
    #   900,000 subs -> under 5,000 views (cap)
    require_low_recent_views: bool = True
    recent_views_base: int = Field(default=1000, ge=0)
    recent_views_per_subscriber: float = Field(default=0.005, ge=0.0)
    recent_views_cap: int = Field(default=5000, ge=0)
    # Discovery reuse: if the same niche was discovered within this many hours,
    # reuse those results instead of spending YouTube quota again (unless the
    # caller forces a fresh run). Set to 0 to disable and always re-run.
    discovery_reuse_hours: int = Field(default=24, ge=0)

    # YouTube API Terms compliance: stored channel/video data must be deleted or
    # refreshed within 30 days. The /maintenance/cleanup endpoint purges records
    # not refreshed within this many days. Set 0 to disable (not recommended).
    data_retention_days: int = Field(default=30, ge=0)
    # Optional shared secret required to call the maintenance endpoint (so a
    # public cron can trigger cleanup safely). Blank = endpoint open.
    maintenance_token: str = ""

    @field_validator("database_url")
    @classmethod
    def _force_async_driver(cls, url: str) -> str:
        """Normalise managed-host DSNs to the async driver the app requires.

        Render/Railway/Heroku hand out `postgres://` or `postgresql://` URLs,
        but SQLAlchemy's async engine (and Alembic, which reads this same
        setting) needs `postgresql+asyncpg://`. Rewriting here means every
        consumer gets a usable URL regardless of what the platform injected.
        """
        for prefix in ("postgresql+asyncpg://", "sqlite"):
            if url.startswith(prefix):
                return url
        for prefix in ("postgresql://", "postgres://"):
            if url.startswith(prefix):
                return "postgresql+asyncpg://" + url[len(prefix):]
        return url

    @property
    def excluded_country_set(self) -> set[str]:
        return {c.strip().upper() for c in self.excluded_countries.split(",") if c.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
