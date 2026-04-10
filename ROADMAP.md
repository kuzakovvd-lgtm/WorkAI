# WorkAI Roadmap

Status date: 2026-04-10

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
| 10 | Ops layer | Done | Healthcheck/sweepers/rollups and operational validation tooling |
| 11 | Safe production launch of v2 | In progress | v2 launch safety gate without dependency on v1 baseline |
| 12 | Hardening | In progress | Coverage >=70%, strict static checks, docs/perf/DR hardening |

## Current focus

Phase 12 hardening pass (coverage + static analysis + docs/perf/DR).

## Confirmed v2 baseline

As of 2026-04-10, v2 has a real production-like baseline on connected Google Sheets:

- `sheet_cells = 31376`
- `raw_tasks = 1892`
- `tasks_normalized = 1892`
- `daily_task_assessments = 39`
- `operational_cycles = 39`
- `audit_runs = 4`

Known-at-capture caveat (resolved in hotfix): `run_audit --force` error-path pool lifecycle bug.

## Phase 11 Re-scope

### Decision

Original Phase 11 is redefined from "migration from working v1 to v2" to
"safe production launch of v2".

### Reason

- v1 is not a stable production baseline;
- v1/v2 numerical alignment is not a reliable quality signal in this project state;
- rollback to v1 does not provide dependable operational safety.

### Accepted risks

- no 7-day v1/v2 parallel comparison as hard gate;
- no acceptance gate based on `>=95%` alignment to v1;
- no rollback promise to v1 runtime.

### New acceptance criteria

- production deploy path + `workai-*` units/timers are ready;
- secrets/env contract is ready and documented;
- cutover runbook is complete;
- v2 healthcheck is green for defined observation window;
- post-launch smoke pipeline checks pass;
- rollback/restore targets previous deploy or DB snapshot (not v1) and are documented/drill-ready.
