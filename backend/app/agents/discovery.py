"""Discovery Agent — finds candidate creators via a YouTube provider."""
from __future__ import annotations

from app.agents.base import Agent, ChannelContext
from app.common.language import is_probably_english
from app.domain.schemas import RawChannel
from app.integrations.youtube.base import YouTubeProvider


class DiscoveryAgent(Agent[tuple[str, int], list[ChannelContext]]):
    name = "discovery"

    def __init__(
        self,
        provider: YouTubeProvider,
        min_subscribers: int = 0,
        english_only: bool = False,
        max_subscribers: int = 0,
    ) -> None:
        super().__init__()
        self.provider = provider
        self.min_subscribers = min_subscribers
        self.max_subscribers = max_subscribers
        self.english_only = english_only

    async def handle(self, payload: tuple[str, int]) -> list[ChannelContext]:
        query, max_results = payload
        raw: list[RawChannel] = await self.provider.search_channels(query, max_results)
        # Deduplicate by youtube_id, then drop creators below the subscriber
        # floor and non-English creators so they never enter the pipeline (no
        # storage, scoring, or video-fetch quota spent on them).
        seen: set[str] = set()
        contexts: list[ChannelContext] = []
        below_subs = 0
        above_subs = 0
        non_english = 0
        for ch in raw:
            if ch.youtube_id in seen:
                continue
            if self.min_subscribers > 0 and ch.subscriber_count < self.min_subscribers:
                below_subs += 1
                continue
            if self.max_subscribers > 0 and ch.subscriber_count > self.max_subscribers:
                above_subs += 1
                continue
            if self.english_only and not is_probably_english(
                ch.title, ch.description, getattr(ch, "default_language", None)
            ):
                non_english += 1
                continue
            seen.add(ch.youtube_id)
            contexts.append(ChannelContext(raw=ch))
        self.log.info(
            "discovered",
            query=query,
            count=len(contexts),
            below_min_subs=below_subs,
            above_max_subs=above_subs,
            non_english=non_english,
        )
        return contexts
