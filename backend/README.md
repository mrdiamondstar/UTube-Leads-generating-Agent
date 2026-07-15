# CIP Backend

FastAPI + async SQLAlchemy + Celery. Clean/hexagonal layering:

```
app/
  core/          config, logging, database session
  domain/        SQLAlchemy models + Pydantic schemas (the "entities")
  repositories/  persistence behind interfaces
  integrations/  external providers (YouTube: mock + real adapter)
  agents/        the multi-agent pipeline (each agent = one bounded step)
  api/           FastAPI routers (v1)
  workers/       Celery app + tasks
alembic/         migrations
tests/
```

## Run locally (no Docker)

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt -e ".[dev]"

# Point at a local Postgres, or use sqlite for a quick spin:
export DATABASE_URL="postgresql+asyncpg://cip:cip@localhost:5432/cip"

alembic upgrade head
uvicorn app.main:app --reload
```

## Tests

```bash
pip install -e ".[dev]"
pytest
```

Tests run against an in-memory SQLite database (via `aiosqlite`) and the mock
YouTube provider, so no external services are required.
