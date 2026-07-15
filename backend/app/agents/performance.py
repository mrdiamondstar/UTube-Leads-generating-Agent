"""Performance Analysis Agent — flags underperformance vs subscriber baseline."""
from __future__ import annotations

from app.agents.base import Agent, ChannelContext
from app.agents.metrics import is_underperforming


class PerformanceAnalysisAgent(Agent[list[ChannelContext], list[ChannelContext]]):
    name = "performance"

    def __init__(self, underperformance_ratio: float) -> None:
        super().__init__()
        self.ratio = underperformance_ratio

    async def handle(self, payload: list[ChannelContext]) -> list[ChannelContext]:
        for ctx in payload:
            raw = ctx.raw
            ctx.is_underperforming = is_underperforming(
                view_count=raw.view_count,
                subscriber_count=raw.subscriber_count,
                threshold_ratio=self.ratio,
            )
        flagged = sum(1 for c in payload if c.is_underperforming)
        self.log.info("performance.analyzed", total=len(payload), underperforming=flagged)
        return payload
