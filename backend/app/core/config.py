"""Application configuration, loaded from environment (12-factor / config-driven)."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
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
    # Audience floor: only consider creators with at least this many subscribers.
    # Smaller channels are dropped at discovery (never stored/scored). Set 0 off.
    min_subscribers: int = Field(default=10000, ge=0)
    # Activity rule: a creator must have uploaded within this many days to
    # qualify as a lead (default ~6 months). Set to 0 to disable the check.
    active_within_days: int = Field(default=180, ge=0)
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

    @property
    def excluded_country_set(self) -> set[str]:
        return {c.strip().upper() for c in self.excluded_countries.split(",") if c.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
