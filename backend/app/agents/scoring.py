"""Opportunity Scoring Agent — produces an explainable 0-100 lead score."""
from __future__ import annotations

from app.agents.base import Agent, ChannelContext
from app.agents.metrics import score_lead


class OpportunityScoringAgent(Agent[list[ChannelContext], list[ChannelContext]]):
    name = "scoring"

    async def handle(self, payload: list[ChannelContext]) -> list[ChannelContext]:
        for ctx in payload:
            if ctx.excluded:
                ctx.category = "disqualified"
                ctx.reasoning = ctx.exclusion_reason or "excluded"
                continue

            raw = ctx.raw
            result = score_lead(
                subscriber_count=raw.subscriber_count,
                view_count=raw.view_count,
                video_count=raw.video_count,
                has_email=bool(raw.public_email),
                has_website=bool(raw.website),
                social_count=len(raw.social_links or {}),
                performance_ratio_value=ctx.metrics.get("performance_ratio", 1.0),
            )
            ctx.score = result["score"]
            ctx.confidence = result["confidence"]
            ctx.category = result["category"]
            ctx.feature_contributions = result["feature_contributions"]
            ctx.reasoning = result["reasoning"]
        return payload
