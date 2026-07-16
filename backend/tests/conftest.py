"""Test configuration.

Point the app at an in-process SQLite database and the mock YouTube provider
*before* importing any app module (the engine is built at import time from
settings). This keeps the whole suite hermetic — no Postgres, Redis, or network.
"""
from __future__ import annotations

import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["YOUTUBE_PROVIDER"] = "mock"
os.environ["EXCLUDED_COUNTRIES"] = "IN"
os.environ["UNDERPERFORMANCE_RATIO"] = "0.5"
os.environ["MIN_SUBSCRIBERS"] = "0"  # keep count-based pipeline tests deterministic
os.environ["ENGLISH_ONLY"] = "false"  # count-based tests shouldn't depend on lang filter

import pytest_asyncio  # noqa: E402

from app.core.db import Base, SessionLocal, engine  # noqa: E402
from app.domain import models  # noqa: E402,F401  (register tables)


@pytest_asyncio.fixture(autouse=True)
async def _schema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def session():
    async with SessionLocal() as s:
        yield s
