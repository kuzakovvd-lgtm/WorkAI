# WorkAI Task Board

Status date: 2026-04-09

Policy: every non-trivial iteration must update this board together with
`docs/iteration-logs/` entry.

## Done

- [x] Phase 0 bootstrap.
- [x] Phase 1 core infrastructure.
- [x] Phase 2 ingest layer (`Google Sheets -> sheet_cells`).
- [x] Phase 3 parse layer (`sheet_cells -> raw_tasks`).
- [x] Phase 4 normalize layer (`raw_tasks -> tasks_normalized`).
- [x] Phase 4.5 pre-flight hardening (CI postgres, DLQ, normalize single-flight lock).
- [x] Phase 5 assess layer (ghost time, scoring, aggregation, Bayesian norms).
- [x] Phase 6 knowledge base (markdown index + PostgreSQL FTS lookup + cache).
- [x] Phase 7 AI audit layer (CrewAI sequential flow + audit_runs).
- [x] Phase 8 API layer (FastAPI routes + auth + integration smoke).
- [x] Phase 9 notifier layer (Telegram alerts + notification_log).

## In progress

- [ ] Phase 10 ops layer (healthcheck + stale sweeper + cost rollup + verify_units).

## Next

- [ ] Finalize Phase 10 validation in CI and merge.
- [ ] Start Phase 11 migration/cutover planning.
- [ ] Prepare ops runbook checks for scheduled execution.

## Backlog

- [ ] Ops + migration/cutover hardening (Phases 10-11).
