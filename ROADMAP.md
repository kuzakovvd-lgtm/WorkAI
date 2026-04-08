# WorkAI Roadmap

Status date: 2026-04-08

## Phases

| Phase | Scope | Status | Definition of Done |
|---|---|---|---|
| 0 | Bootstrap (repo/tooling/CI skeleton) | Done | Repo skeleton exists, CI runs lint/type/test, baseline docs present |
| 1 | Core infrastructure (`config`, `common`, `db`, Alembic baseline) | Done | Typed settings/logging/db helpers + Alembic baseline + tests |
| 2 | Ingest layer | Planned | Source pull into raw staging tables, retries, observability |
| 3 | Parse layer | Planned | Deterministic parsing into `raw_tasks` with tests |
| 4 | Normalize layer | Planned | Canonical `tasks_normalized` contract + migrations |
| 5 | Assess layer | Planned | Scoring and ghost-time calculations with reproducible rules |
| 6 | Knowledge base | Planned | Searchable methodology storage and retrieval |
| 7 | Audit layer | Planned | Multi-agent AI audit orchestration |
| 8 | API layer | Planned | FastAPI endpoints with auth and health endpoints |
| 9 | Notifier | Planned | Telegram alerts by severity and routing rules |
| 10 | Ops layer | Planned | Healthcheck/sweepers/rollups and operational automation |
| 11 | Migration & cutover from v1 | Planned | Controlled parallel run and safe production switchover |
| 12 | Hardening | Planned | Coverage, performance checks, operational hardening |

## Current focus

Phase 2 planning and DB contract refinement for ingest/parser handoff.
