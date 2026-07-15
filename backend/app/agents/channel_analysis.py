"""Channel Analysis Agent — normalizes raw channel data into base metrics."""
from __future__ import annotations

from app.agents.base import Agent, ChannelContext
from app.agents.metrics import compute_metrics


class ChannelAnalysisAgent(Agent[list[ChannelContext], list[ChannelContext]]):
    name = "channel_analysis"

    async def handle(self, payload: list[ChannelContext]) -> list[ChannelContext]:
        for ctx in payload:
            raw = ctx.raw
            ctx.metrics.update(
                compute_metrics(
                    view_count=raw.view_count,
                    subscriber_count=raw.subscriber_count,
                    video_count=raw.video_count,
                )
            )
        return payload
