"""Discovery Agent — finds candidate creators via a YouTube provider."""
from __future__ import annotations

from app.agents.base import Agent, ChannelContext
from app.domain.schemas import RawChannel
from app.integrations.youtube.base import YouTubeProvider


class DiscoveryAgent(Agent[tuple[str, int], list[ChannelContext]]):
    name = "discovery"

    def __init__(self, provider: YouTubeProvider) -> None:
        super().__init__()
        self.provider = provider

    async def handle(self, payload: tuple[str, int]) -> list[ChannelContext]:
        query, max_results = payload
        raw: list[RawChannel] = await self.provider.search_channels(query, max_results)
        # Deduplicate by youtube_id (incremental/repeat discovery safety).
        seen: set[str] = set()
        contexts: list[ChannelContext] = []
        for ch in raw:
            if ch.youtube_id in seen:
                continue
            seen.add(ch.youtube_id)
            contexts.append(ChannelContext(raw=ch))
        self.log.info("discovered", query=query, count=len(contexts))
        return contexts
