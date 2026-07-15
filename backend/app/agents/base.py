"""Agent base abstractions.

Every agent is a single, testable, idempotent step with typed input/output,
its own logger, and a uniform retry wrapper. This keeps the pipeline
composable and observable (each step emits structured logs + timing).
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from app.core.logging import get_logger

TIn = TypeVar("TIn")
TOut = TypeVar("TOut")


@dataclass
class ChannelContext:
    """The working object passed between agents for a single creator."""

    raw: object  # RawChannel (kept loose to avoid a hard import cycle)
    metrics: dict = field(default_factory=dict)
    is_underperforming: bool = False
    excluded: bool = False
    exclusion_reason: str | None = None
    score: float = 0.0
    confidence: float = 0.0
    category: str = "cold"
    feature_contributions: dict = field(default_factory=dict)
    reasoning: str = ""


class Agent(ABC, Generic[TIn, TOut]):
    name: str = "agent"
    max_retries: int = 2

    def __init__(self) -> None:
        self.log = get_logger(f"agent.{self.name}")

    @abstractmethod
    async def handle(self, payload: TIn) -> TOut:
        """Core logic. Implementations must be idempotent."""
        raise NotImplementedError

    async def run(self, payload: TIn) -> TOut:
        """Execute with timing + bounded retries."""
        attempt = 0
        while True:
            attempt += 1
            started = time.perf_counter()
            try:
                result = await self.handle(payload)
                self.log.info(
                    "agent.ok", attempt=attempt, ms=round((time.perf_counter() - started) * 1000, 1)
                )
                return result
            except Exception as exc:  # noqa: BLE001
                self.log.error("agent.error", attempt=attempt, error=str(exc))
                if attempt > self.max_retries:
                    raise
