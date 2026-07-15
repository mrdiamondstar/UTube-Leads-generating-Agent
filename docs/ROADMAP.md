# CIP Roadmap

Phase 1 (this repo) is a runnable vertical slice. Below is the path to the full
enterprise platform from the master brief, in dependency order.

## Phase 1 — Foundation ✅ (done)
- FastAPI + async SQLAlchemy + Alembic + Postgres
- Agent pipeline: Discovery → Channel Analysis → Performance → Country Validation → Scoring
- Explainable scoring, pipeline audit, Celery worker, mock YouTube provider
- Next.js dashboard shell (Overview, Leads)
- Unit + integration + API tests (all green)

## Phase 2 — Enrichment & AI
- **Public Contact Enrichment Agent**: resolve website/socials/business email from
  public sources only (respect robots, rate limits).
- **AI Insight Agent** + **Email Personalization Agent**: Claude/OpenAI/Gemini
  behind a provider port (mirror the YouTube pluggable pattern); store outputs in
  a new `ai_outputs` table. Add Qdrant for semantic dedup/similar-creator search.
- Guardrails: prompt templates, token/cost logging, output validation.

## Phase 3 — CRM, Notifications, Reporting
- **CRM Synchronization Agent** (HubSpot/Salesforce adapters, idempotent upsert).
- **Notification Agent** (email/Slack) + **Report Generator Agent** (PDF/CSV).
- Dashboard pages: Analytics, Countries, Categories, Reports, CRM, Notifications,
  Audit Logs, Settings.

## Phase 4 — Platform hardening
- **AuthN/Z**: users, roles, permissions (RBAC), API keys/OAuth.
- **Scheduler Agent**: periodic discovery via Celery beat.
- **Quality Assurance Agent**: data validation + scoring drift checks.
- Observability: OpenTelemetry traces, Prometheus metrics, Grafana, Loki logs.

## Phase 5 — Infra & delivery
- Kubernetes manifests / Helm chart; Terraform for AWS (RDS, ElastiCache, ECR, EKS).
- GitHub Actions CI/CD (lint, test, build, scan, deploy).
- Security: secrets management, network policy, image scanning, load & security tests.

## Suggested next step
Implement the **Public Contact Enrichment Agent** and an LLM provider port for
the **AI Insight Agent** — both slot directly into the existing Manager pipeline
and `ai_outputs`/enrichment columns already anticipated in the schema.
