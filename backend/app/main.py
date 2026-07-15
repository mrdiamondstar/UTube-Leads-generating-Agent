"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

settings = get_settings()
configure_logging()
log = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup", env=settings.app_env, youtube_provider=settings.youtube_provider)
    yield
    log.info("shutdown")


app = FastAPI(
    title="Creator Intelligence Platform API",
    version="0.1.0",
    description="Discovers, analyzes, and scores YouTube creator leads (public data only).",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten per-environment in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "service": "cip-backend", "version": "0.1.0"}


@app.get("/", tags=["system"])
async def root() -> dict:
    return {"service": "Creator Intelligence Platform", "docs": "/docs"}
