# Creator Intelligence Platform (CIP)

An autonomous multi-agent system that discovers YouTube creators worldwide
(excluding creators primarily based in India), analyzes channel performance,
detects underperformance relative to subscriber count, enriches **publicly
available** business information, scores qualified leads, and generates AI
insights and outreach drafts.

> This repository is a **runnable foundation** (Phase 1) of the full enterprise
> platform described in `docs/ARCHITECTURE.md`. It boots end-to-end with a mock
> YouTube provider so no API key is required to try it.

## What works today

- FastAPI backend (async SQLAlchemy 2.0 + Postgres, Alembic migrations)
- A real, end-to-end **agent pipeline**:
  `Discovery → Channel Analysis → Performance Analysis → Country Validation → Opportunity Scoring → persist`
- Explainable **0–100 lead scoring** with per-feature contributions
- **Real YouTube Data API v3 integration** (default): channel search, channel details,
  recent videos, and video statistics — with quota monitoring, response caching,
  retry/backoff, pagination, and client-side rate limiting. A mock provider remains
  as a **test double** (`YOUTUBE_PROVIDER=mock`) for offline dev/tests
- Celery + Redis worker to run pipelines asynchronously
- Next.js dashboard shell (Overview + Leads) that reads the API
- Unit + API tests

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

Then:

- API docs:      http://localhost:8000/docs
- Health:        http://localhost:8000/health
- Dashboard:     http://localhost:3000

Kick off a discovery+scoring run (uses the mock provider):

```bash
curl -X POST http://localhost:8000/api/v1/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"query": "tech reviews", "max_results": 25}'
```

List scored leads:

```bash
curl http://localhost:8000/api/v1/leads
```

## Local dev without Docker

See `backend/README.md` and `frontend/README.md`.

## YouTube Data API v3 (default)

The real API is the default provider. Provide a key via environment (never
hardcoded):

```
YOUTUBE_PROVIDER=api          # default
YOUTUBE_API_KEY=your_google_cloud_api_key
```

Implemented operations (with quota cost per call):

| Operation | Endpoint | Units |
|-----------|----------|-------|
| Channel search (paginated) | `search.list` | 100 |
| Channel details (batched ≤50) | `channels.list` | 1 |
| Recent videos (paginated) | `playlistItems.list` | 1 |
| Video statistics (batched ≤50) | `videos.list` | 1 |

Operational features: daily **quota budget + monitoring** (`GET /api/v1/quota`,
persisted to `api_quota_usage`), **response caching** (Redis if available, else
in-memory TTL), **retry with backoff** on transient errors, and **rate limiting**.
All results (channels, snapshots, videos, scores) are stored in Postgres.

For offline dev/tests without a key, set `YOUTUBE_PROVIDER=mock` (a labelled test
double — not production data).

## Repository layout

```
backend/    FastAPI app, agents, integrations, workers, migrations, tests
frontend/   Next.js (App Router) dashboard
docs/       Architecture overview, roadmap
docker-compose.yml
```

## Compliance note

CIP collects **only publicly available information** and is intended for
legitimate B2B sales intelligence. Respect the YouTube Terms of Service and
API quota, robots directives, and applicable privacy law (GDPR/CCPA) when
enabling live data sources. See `docs/ARCHITECTURE.md` → "Compliance".

## Roadmap

Phase 1 (this repo): runnable discovery→scoring slice.
Phase 2+: enrichment agent, AI insight/email agents, CRM sync, notifications,
full dashboard pages, K8s/Terraform, observability stack. See `docs/ROADMAP.md`.
