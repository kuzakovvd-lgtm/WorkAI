# WorkAI Task Board

Status date: 2026-04-10

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
- [x] Phase 10 ops layer (healthcheck + stale sweeper + cost rollup + verify_units).

## In progress

- [ ] Phase 11 safe production launch of v2 (cutover gating + readiness checks).
- [ ] Phase 12 hardening (coverage/static/docs/perf/DR).
- [ ] Baseline documentation + force-path hotfix verification.

## Next

- [ ] Finalize Phase 11 launch observation evidence.
- [ ] Finalize Phase 12 CI evidence with hardened checks.
- [ ] Publish final production readiness summary.
- [ ] Keep weekly-board parse coverage/tests aligned with real connected sheets.

## Backlog

- [ ] Phase 11 decision tracking (waived v1-alignment criteria + accepted risks).
- [ ] Phase 12 hardening preparation.

## Phase 11 Decision Log

### Decision

Phase 11 is re-scoped to v2-first safe production launch.

### Reason

v1 is not a dependable production baseline; comparison and rollback gates against v1 are not actionable quality controls.

### Accepted risks

- no mandatory 7-day v1/v2 parallel run;
- no `>=95%` v1 alignment gate;
- no rollback dependency on v1 runtime.

### New acceptance criteria

- v2 launch safety artifacts ready;
- cutover and rollback-to-previous-deploy runbook ready;
- health/smoke validation window defined and tracked.
