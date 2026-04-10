# WorkAI v2 Final Project Dossier

Date: 2026-04-10
Branch of record: `Itogmain`

## 1. What WorkAI v2 is

WorkAI v2 is a DB-driven modular employee work-audit platform that ingests Google Sheets, parses and normalizes task data, computes assess metrics, runs AI audit, exposes HTTP API, sends notifier alerts, and operates with health/sweeper/rollup tooling.

## 2. Final project status

- Phases 0-10: done.
- Phase 11: re-scoped from v1 migration to v2-first safe launch; done under re-scoped criteria.
- Phase 12: hardening pass complete.
- Completed means system is running end-to-end on real connected sheets with operational runbooks, hardening checks, and DR docs.

## 3. System architecture

Pipeline and supporting modules:

- ingest: Google Sheets -> `sheet_cells`
- parse: `sheet_cells` -> `raw_tasks`
- normalize: `raw_tasks` -> `tasks_normalized`
- assess: ghost time, task scoring, cycles, Bayesian norms
- knowledge_base: markdown indexing + PostgreSQL FTS
- audit: CrewAI sequential 3-agent run with cache/force semantics
- api: FastAPI HTTP layer over DB contracts
- notifier: Telegram routing + `notification_log`
- ops: healthcheck, stale sweeper, cost rollup, verify_units

Contract rule: cross-module contract is database schema (`DB_CONTRACT.md`), not Python interfaces.

## 4. Primary database tables

Core contract tables:

- `sheet_cells`
- `raw_tasks`
- `tasks_normalized`
- `employees`
- `employee_daily_ghost_time`
- `daily_task_assessments`
- `operational_cycles`
- `dynamic_task_norms`
- `pipeline_errors`
- `knowledge_base_articles`
- `audit_runs`
- `audit_feedback`
- `audit_cost_daily`
- `notification_log`

Alembic head: `0014_notification_log`.

## 5. System/runtime layout

Runtime paths and directories:

- code: `/opt/workai -> /opt/WorkAI`
- config root: `/etc/workai`
- secrets: `/etc/workai/secrets`
- logs: `/var/log/workai`
- systemd units/timers: `/etc/systemd/system/workai-*`

Release branch policy:

- active branch: `Itogmain`
- legacy v1 runtime removed from active server stack.

## 6. Actual data flow

Observed running flow:

Google Sheets -> ingest -> `sheet_cells` -> parse -> `raw_tasks` -> normalize -> `tasks_normalized` -> assess (`daily_task_assessments`, `employee_daily_ghost_time`, `operational_cycles`, `dynamic_task_norms`) -> audit (`audit_runs`) + api/notifier/ops.

## 7. Current production baseline

Baseline snapshot from live connected sheets (captured 2026-04-10):

- `sheet_cells = 31376`
- `raw_tasks = 1892`
- `tasks_normalized = 1892`
- `daily_task_assessments = 39`
- `operational_cycles = 39`
- `audit_runs = 4`

Baseline interpretation:

- end-to-end data path is non-empty and functional;
- parse includes weekly-board fallback for real sheet layout.

## 8. Services and timers used

Primary active units:

- `workai-api.service`
- `workai-cell-ingest.timer` (+ service)
- `workai-parse.timer` (+ service)
- `workai-normalize.timer` (+ service)
- `workai-assess.timer` (+ service)
- `workai-stale-sweeper.timer` (+ service)
- `workai-cost-rollup.timer` (+ service)
- `workai-verify-units.timer` (+ service)
- `workai-healthcheck.timer` (+ service)

## 9. API overview

FastAPI app: `WorkAI.api.main:app`

Implemented endpoint groups:

- health: `/health`, `/health/deep`
- tasks: `/tasks/raw`, `/tasks/normalized`, `/tasks/aggregated`
- analysis: `/analysis/start`, `/analysis/status/{run_id}`, `/analysis/history`, `/analysis/{run_id}/feedback`
- team: `/team/overview`
- debug: `/debug/logs`, `/debug/cost`

Auth model:

- `/health` unauthenticated;
- other routes require `X-API-Key`.

## 10. Notifier / Telegram routing

`TelegramNotifier.send_alert(...)` supports:

- `infra_critical` -> admin channel
- `data_warning` -> management channel
- `info` -> info channel (or admin fallback)

Every attempt is logged to `notification_log` with `delivered` + `error` semantics.

## 11. Google Sheets integration

Google ingest uses service account credentials and bounded ranges.

Key behavior:

- batchGet with retries/backoff
- idempotent range refresh (`DELETE range -> INSERT non-empty cells`)
- real source config via `/etc/workai/google_sheets_sources.json`
- parse is adapted for real weekly-board layout currently used by connected sheets.

## 12. Audit / OpenAI integration

Audit module runs a sequential CrewAI flow (3 agents), persists runs to `audit_runs`, and stores usage telemetry under `report_json._usage`.

Runner semantics:

- `run_audit(..., force=False)` can return cached result and write `completed_cached` ledger row;
- `force=True` creates a new run.

Known fixed issue:

- `run_audit --force` pool-lifecycle error-path bug was fixed (failed-run persistence survives mid-run pool closure).

## 13. Healthcheck / Ops

Ops scripts:

- `scripts/run_healthcheck.py`
- `scripts/run_stale_sweeper.py`
- `scripts/run_cost_rollup.py`
- `scripts/run_verify_units.py`

Healthcheck severity contract:

- `info`, `data_warning`, `infra_critical`
- script exit codes: `0/1/2` accordingly.

## 14. Test strategy (prod DB vs integration DB)

Server DB split:

- runtime DB env: `/etc/workai/secrets/db.env` -> `workai_v2_test`
- integration DB env: `/etc/workai/secrets/db.test.env` -> `workai_v2_integration`

Policy:

- production runtime services must stay on `db.env`;
- integration smoke must run only with `db.test.env`.

## 15. Deployment / launch model

Phase 11 is re-scoped to v2-first launch.

Launch model:

- systemd-managed `workai-*` runtime
- v2-centric readiness gates (health/smoke)
- no dependency on v1 parity gates.

## 16. Disaster recovery / rollback model

Rollback target is previous known-good v2 deploy plus DB snapshot/restore.

Reference:

- `docs/DR_PLAN.md`

No rollback dependency on v1 runtime.

## 17. Known limitations / accepted risks

- Original v1 comparison gates are waived by explicit project decision (ADR-0017).
- Runtime quality relies on v2-centric checks, operational discipline, and backup/restore readiness.
- AI provider behavior can still produce run-level failures; these are persisted in ledger and observable.

## 18. What is required for operations

- valid env/secrets in `/etc/workai/secrets/*`
- reachable PostgreSQL
- Google service account access to configured sheets
- OpenAI key for audit
- Telegram credentials for notifier
- active `workai-*` services/timers

## 19. Security and rotation notes

- Do not keep temporary bring-up secrets long-term.
- Rotate API/OpenAI/Telegram/Google credentials after test bring-up.
- Keep secrets out of repository and logs.
- Keep backup retention and access controls enforced.

## 20. Final system state conclusion

WorkAI v2 is in a real operational state on branch `Itogmain`, with end-to-end live data flow, isolated integration testing DB, operational scripts, and synchronized phase documentation. Remaining work is operational discipline (monitoring, rotation, routine drills), not core feature completion.
