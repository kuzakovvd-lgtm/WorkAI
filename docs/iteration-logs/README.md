# Iteration Logs

Purpose: detailed execution log per iteration/phase, with decisions, commands, validations, and outcomes.

Format rules:
- One file per iteration.
- File name: `YYYY-MM-DD_phase-<id>_<short-topic>.md`.
- Dates in ISO format (`YYYY-MM-DD`).
- Keep latest iteration at top in the index table.
- For each non-trivial iteration, updating this index is required.
- The same iteration must update `TASK_BOARD.md` status.

## Index

| Date | Iteration | Scope | Commit | Status | Log |
|---|---|---|---|---|---|
| 2026-04-09 | Phase 10 | Operations layer (healthcheck + sweeper + rollup + verify_units) | `pending` | In progress | [2026-04-09_phase-10_operations.md](./2026-04-09_phase-10_operations.md) |
| 2026-04-09 | Phase 9 | Notifier layer (Telegram routing + `notification_log` + smoke tests) | `9246314` | Completed | [2026-04-09_phase-9_notifier.md](./2026-04-09_phase-9_notifier.md) |
| 2026-04-09 | Phase 8 | API layer (FastAPI routes, auth, async orchestration, HTTP smoke) | `716fde9` | Completed | [2026-04-09_phase-8_api-fastapi.md](./2026-04-09_phase-8_api-fastapi.md) |
| 2026-04-09 | Phase 7 | AI Audit (CrewAI) sequential flow + cache/force + usage telemetry | `pending` | In progress | [2026-04-09_phase-7_audit-crewai.md](./2026-04-09_phase-7_audit-crewai.md) |
| 2026-04-09 | Phase 6 | Knowledge Base (markdown indexing + PostgreSQL FTS lookup + cache) | `pending` | In progress | [2026-04-09_phase-6_knowledge-base.md](./2026-04-09_phase-6_knowledge-base.md) |
| 2026-04-09 | Phase 4.5 | Pre-flight hardening (CI postgres + DLQ + normalize lock) | `pending` | Completed | [2026-04-09_phase-4.5_hardening.md](./2026-04-09_phase-4.5_hardening.md) |
| 2026-04-08 | Phase 4 | Normalize layer (raw_tasks -> tasks_normalized) | `pending` | Completed | [2026-04-08_phase-4_normalize.md](./2026-04-08_phase-4_normalize.md) |
| 2026-04-08 | Phase 3 | Parse layer (sheet_cells -> raw_tasks) | `e0a33bf` | Completed | [2026-04-08_phase-3_parse.md](./2026-04-08_phase-3_parse.md) |
| 2026-04-08 | Phase 2 | Ingest layer (Google Sheets -> sheet_cells) | `ea4c926` | Completed | [2026-04-08_phase-2_ingest-sheet-cells.md](./2026-04-08_phase-2_ingest-sheet-cells.md) |
| 2026-04-08 | Phase 1 | Core infrastructure (config/common/db/alembic baseline) | `566fe8d` | Completed | [2026-04-08_phase-1_core-infrastructure.md](./2026-04-08_phase-1_core-infrastructure.md) |
| 2026-04-08 | Phase 0 | Repository bootstrap | `ed5d726` | Completed | [2026-04-08_phase-0_bootstrap.md](./2026-04-08_phase-0_bootstrap.md) |

## Sections template

Use [TEMPLATE.md](./TEMPLATE.md) for all next iterations.
