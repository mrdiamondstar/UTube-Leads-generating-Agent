"""YouTube provider port (hexagonal architecture — an interface, not an impl)."""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.schemas import RawChannel, RawVideo


class YouTubeProvider(ABC):
    """Port for discovering and fetching public YouTube channel/video data."""

    @abstractmethod
    async def search_channels(self, query: str, max_results: int = 25) -> list[RawChannel]:
        """Discover channels for a query (search.list + channels.list), paginated."""
        raise NotImplementedError

    @abstractmethod
    async def get_recent_videos(
        self, uploads_playlist_id: str, channel_youtube_id: str, max_results: int = 10
    ) -> list[RawVideo]:
        """Fetch a channel's most recent uploads with their statistics."""
        raise NotImplementedError

    async def aclose(self) -> None:
        """Release any underlying resources (HTTP client, etc.)."""
        return None
