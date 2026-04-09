# WorkAI Task Board

Status date: 2026-04-08

Policy: every non-trivial iteration must update this board together with
`docs/iteration-logs/` entry.

## Done

- [x] Phase 0 bootstrap.
- [x] Phase 1 core infrastructure.
- [x] Phase 2 ingest layer (`Google Sheets -> sheet_cells`).
- [x] Phase 3 parse layer (`sheet_cells -> raw_tasks`).
- [x] Phase 4 normalize layer (`raw_tasks -> tasks_normalized`).
- [x] Phase 4.5 pre-flight hardening (CI postgres, DLQ, normalize single-flight lock).

## In progress

- [ ] Phase 5 assess layer design and `daily_task_assessments` contract.

## Next

- [ ] Define `daily_task_assessments` schema and migration(s) for assess layer.
- [ ] Implement assess module entrypoint(s) in `scripts/`.
- [ ] Add assess unit/integration tests.
- [ ] Extend runbook with assess operational checks.

## Backlog

- [ ] Assess layer (Phase 5).
- [ ] Knowledge base (Phase 6).
- [ ] Audit orchestration (Phase 7).
- [ ] API + notifier + ops (Phases 8-10).
