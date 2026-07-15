"""Pipeline endpoints — trigger and inspect agent runs."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.manager import ManagerAgent
from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.domain.models import PipelineRun
from app.domain.schemas import PipelineRunOut, PipelineRunRequest

router = APIRouter()


@router.post("/run", response_model=PipelineRunOut, status_code=201)
async def run_pipeline(
    body: PipelineRunRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> PipelineRun:
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
