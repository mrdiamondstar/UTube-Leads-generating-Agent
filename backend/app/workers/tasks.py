"""Celery tasks — async agent runs bridged into the worker via asyncio."""
from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.agents.manager import ManagerAgent
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.logging import get_logger
from app.domain.models import PipelineRun
from app.workers.celery_app import celery_app

log = get_logger("worker")


async def _run(run_id: str) -> dict:
    settings = get_settings()
    async with SessionLocal() as session:
        run = (
            await session.execute(select(PipelineRun).where(PipelineRun.id == run_id))
        ).scalar_one_or_none()
        if run is None:
            log.error("worker.run_missing", run_id=run_id)
            return {"run_id": run_id, "status": "missing"}
        try:
            manager = ManagerAgent(session, settings)
            await manager.run(run)
            await session.commit()
            return {"run_id": run_id, "status": run.status, "qualified": run.qualified}
        except Exception:
            await session.commit()  # persist the "failed" status recorded by the manager
            raise


@celery_app.task(name="pipeline.run", bind=True, max_retries=3, default_retry_delay=10)
def run_pipeline_task(self, run_id: str) -> dict:
    try:
        return asyncio.run(_run(run_id))
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc)
