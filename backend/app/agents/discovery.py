"""Discovery Agent — finds candidate creators via a YouTube provider."""
from __future__ import annotations

from app.agents.base import Agent, ChannelContext
from app.domain.schemas import RawChannel
from app.integrations.youtube.base import YouTubeProvider


class DiscoveryAgent(Agent[tuple[str, int], list[ChannelContext]]):
    name = "discovery"

    def __init__(self, provider: YouTubeProvider, min_subscribers: int = 0) -> None:
        super().__init__()
        self.provider = provider
        self.min_subscribers = min_subscribers

    async def handle(self, payload: tuple[str, int]) -> list[ChannelContext]:
        query, max_results = payload
        raw: list[RawChannel] = await self.provider.search_channels(query, max_results)
        # Deduplicate by youtube_id (incremental/repeat discovery safety) and
        # drop creators below the minimum-subscriber floor so they never enter
        # the pipeline (no storage, scoring, or video-fetch quota spent).
        seen: set[str] = set()
        contexts: list[ChannelContext] = []
        skipped = 0
        for ch in raw:
            if ch.youtube_id in seen:
                continue
            if self.min_subscribers > 0 and ch.subscriber_count < self.min_subscribers:
                skipped += 1
                continue
            seen.add(ch.youtube_id)
            contexts.append(ChannelContext(raw=ch))
        self.log.info(
            "discovered", query=query, count=len(contexts), below_min_subs=skipped
        )
        return contexts
