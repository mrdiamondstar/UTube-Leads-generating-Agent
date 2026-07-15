"""YouTube provider factory (config-driven, pluggable).

Default is the real YouTube Data API v3. The mock provider is a test double,
selected only when YOUTUBE_PROVIDER=mock.
"""
from __future__ import annotations

from app.core.config import Settings
from app.integrations.youtube.base import YouTubeProvider


def build_youtube_provider(settings: Settings) -> YouTubeProvider:
    if settings.youtube_provider.lower() == "mock":
        from app.integrations.youtube.mock import MockYouTubeProvider

        return MockYouTubeProvider()

    # Default: real API.
    from app.integrations.youtube.api import YouTubeApiProvider

    return YouTubeApiProvider(api_key=settings.youtube_api_key, settings=settings)
