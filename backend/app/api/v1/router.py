"""Aggregate v1 API router."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, billing, leads, maintenance, niches, pipeline, quota

api_router = APIRouter()
api_router.include_router(auth.router, prefix="", tags=["auth"])
api_router.include_router(pipeline.router, prefix="/pipeline", tags=["pipeline"])
api_router.include_router(leads.router, prefix="", tags=["leads"])
api_router.include_router(quota.router, prefix="", tags=["quota"])
api_router.include_router(billing.router, prefix="", tags=["billing"])
api_router.include_router(niches.router, prefix="", tags=["niches"])
api_router.include_router(maintenance.router, prefix="", tags=["maintenance"])
