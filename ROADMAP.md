# WorkAI Roadmap

Status date: 2026-04-09

## Phases

| Phase | Scope | Status | Definition of Done |
|---|---|---|---|
| 0 | Bootstrap (repo/tooling/CI skeleton) | Done | Repo skeleton exists, CI runs lint/type/test, baseline docs present |
| 1 | Core infrastructure (`config`, `common`, `db`, Alembic baseline) | Done | Typed settings/logging/db helpers + Alembic baseline + tests |
| 2 | Ingest layer | Done | Source pull into `sheet_cells`, retries, observability, CLI entrypoint |
| 3 | Parse layer | Done | Deterministic parsing into `raw_tasks`, CLI and unit/integration tests |
| 4 | Normalize layer | Done | Canonical `tasks_normalized` contract + migrations |
| 5 | Assess layer | Done | Ghost time, scoring, aggregation, and Bayesian norms in DB-driven pipeline |
| 6 | Knowledge base | Done | Markdown indexing + PostgreSQL FTS lookup + cache + CLI |
| 7 | Audit layer | Done | CrewAI 3-agent sequential audit with cache/force and usage telemetry |
| 8 | API layer | Done | FastAPI endpoints with auth, health, tasks, analysis, team, and debug routes |
| 9 | Notifier | Done | Telegram alerts by severity, resilient send path, and `notification_log` contract |
| 10 | Ops layer | In progress | Healthcheck/sweepers/rollups and operational validation tooling |
| 11 | Migration & cutover from v1 | Planned | Controlled parallel run and safe production switchover |
| 12 | Hardening | Planned | Coverage, performance checks, operational hardening |

## Current focus

Phase 10 operations implementation and validation.
