"""Pipeline endpoints — trigger and inspect agent runs."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.manager import ManagerAgent
from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.domain.models import PipelineRun
from app.domain.schemas import PipelineRunOut, PipelineRunRequest

router = APIRouter()


async def _recent_run(session: AsyncSession, query: str, hours: int) -> PipelineRun | None:
    """Most recent successful discovery for this niche within the window, if any."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    return (
        await session.execute(
            select(PipelineRun)
            .where(
                PipelineRun.query == query,
                PipelineRun.status == "done",
                PipelineRun.created_at >= cutoff,
            )
            .order_by(PipelineRun.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


@router.post("/run", response_model=PipelineRunOut, status_code=201)
async def run_pipeline(
    body: PipelineRunRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> PipelineRun:
    # Reuse guard: if this niche was discovered recently, return that run instead
    # of spending YouTube quota again (unless the caller forces a fresh run).
    if not body.force and settings.discovery_reuse_hours > 0:
        existing = await _recent_run(session, body.query, settings.discovery_reuse_hours)
        if existing is not None:
            existing.reused = True  # transient flag for the response (not persisted)
            return existing

    run = PipelineRun(query=body.query, stats={"max_results": body.max_results})
    session.add(run)
    await session.flush()

    if body.run_async:
        # Dispatch to Celery; the worker owns its own DB session.
        from app.workers.tasks import run_pipeline_task

        run.status = "queued"
        await session.flush()
        run_pipeline_task.delay(run.id)
        return run

    # Run inline. Capture failures on the run record and return it (rather than
    # a 500) so the client always gets a structured status + error message —
    # e.g. a missing YOUTUBE_API_KEY surfaces here cleanly.
    try:
        manager = ManagerAgent(session, settings)
        await manager.run(run)
    except Exception as exc:  # noqa: BLE001
        from datetime import datetime, timezone

        run.status = "failed"
        run.error = run.error or str(exc)
        run.finished_at = run.finished_at or datetime.now(timezone.utc)
    return run


@router.get("/recent-niches", response_model=list[str])
async def recent_niches(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> list[str]:
    """Niches discovered within the reuse window.

    These are the queries the reuse guard would serve from cache (re-running
    them spends no fresh YouTube quota), so the UI can skip them in "Select
    all". Returns distinct niche names, newest first.
    """
    if settings.discovery_reuse_hours <= 0:
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.discovery_reuse_hours)
    rows = await session.execute(
        select(PipelineRun.query, func.max(PipelineRun.created_at).label("last"))
        .where(PipelineRun.status == "done", PipelineRun.created_at >= cutoff)
        .group_by(PipelineRun.query)
        .order_by(func.max(PipelineRun.created_at).desc())
    )
    return [q for q, _ in rows.all()]


@router.get("/runs", response_model=list[PipelineRunOut])
async def list_runs(
    limit: int = 20, session: AsyncSession = Depends(get_session)
) -> list[PipelineRun]:
    rows = await session.execute(
        select(PipelineRun).order_by(PipelineRun.created_at.desc()).limit(limit)
    )
    return list(rows.scalars().all())


@router.get("/runs/{run_id}", response_model=PipelineRunOut)
async def get_run(run_id: str, session: AsyncSession = Depends(get_session)) -> PipelineRun:
    run = (
        await session.execute(select(PipelineRun).where(PipelineRun.id == run_id))
    ).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run
