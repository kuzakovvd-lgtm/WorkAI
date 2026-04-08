# WorkAI Task Board

Status date: 2026-04-08

Policy: every non-trivial iteration must update this board together with
`docs/iteration-logs/` entry.

## Done

- [x] Phase 0 bootstrap.
- [x] Phase 1 core infrastructure.
- [x] Phase 2 ingest layer (`Google Sheets -> sheet_cells`).
- [x] Phase 3 parse layer (`sheet_cells -> raw_tasks`).

## In progress

- [ ] Phase 4 normalize layer design and `tasks_normalized` contract.

## Next

- [ ] Define `tasks_normalized` schema and migration(s) for normalize layer.
- [ ] Implement normalize module entrypoint(s) in `scripts/`.
- [ ] Add normalize unit/integration tests.
- [ ] Extend runbook with normalize operational checks.

## Backlog

- [ ] Normalize layer (Phase 4).
- [ ] Assess layer (Phase 5).
- [ ] Knowledge base (Phase 6).
- [ ] Audit orchestration (Phase 7).
- [ ] API + notifier + ops (Phases 8-10).
