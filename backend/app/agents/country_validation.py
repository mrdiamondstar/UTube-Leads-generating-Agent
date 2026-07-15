"""Country Validation Agent — excludes creators primarily based in excluded countries."""
from __future__ import annotations

from app.agents.base import Agent, ChannelContext


class CountryValidationAgent(Agent[list[ChannelContext], list[ChannelContext]]):
    name = "country_validation"

    def __init__(self, excluded_countries: set[str]) -> None:
        super().__init__()
        self.excluded = {c.upper() for c in excluded_countries}

    async def handle(self, payload: list[ChannelContext]) -> list[ChannelContext]:
        for ctx in payload:
            country = (ctx.raw.country or "").upper()
            if country and country in self.excluded:
                ctx.excluded = True
                ctx.exclusion_reason = f"country '{country}' is excluded"
        excluded = sum(1 for c in payload if c.excluded)
        self.log.info("country.validated", excluded=excluded, rule=sorted(self.excluded))
        return payload
