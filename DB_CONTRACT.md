# Database Contract

## Principle

Database schema is the formal contract between modules.

## Dependency contract

- `api`, `ops` may depend on pipeline modules.
- All modules may depend on `db`, `config`, `common`.
- Reverse/circular imports across domain modules are forbidden.

## Current contract state (Phase 2/3)

- Alembic chain: `0001_baseline` -> `0002_sheet_cells` -> `0003_raw_tasks`.
- Runtime DB access goes through `WorkAI.db` helpers and explicit `init_db()`.

### `sheet_cells` (ingest -> parse contract)

- Purpose: raw cell-level snapshot loaded from Google Sheets bounded ranges.
- Primary key: `(spreadsheet_id, sheet_title, row_idx, col_idx)`.
- Parse expectations:
  - one physical cell is uniquely identified by coordinates in a sheet;
  - `ingested_at` is used for traceability of downstream parsed rows.
- Idempotency expectation:
  - ingest performs range-level refresh (`DELETE range -> INSERT non-empty`) so removed source values are reflected.

### `raw_tasks` (parse -> normalize contract)

- Purpose: deterministic split of task lines from `sheet_cells` with contextual metadata.
- Primary key: `raw_task_id` (surrogate key).
- Uniqueness: `(spreadsheet_id, sheet_title, row_idx, col_idx, line_no)`.
- Indexes:
  - `(spreadsheet_id, sheet_title)` for sheet-scoped refresh/read,
  - `(employee_name_raw, work_date)` for downstream normalization/assessment filters.
- Idempotency expectation:
  - parse runs full-refresh per sheet (`DELETE sheet -> INSERT parsed rows`) and must not duplicate rows on repeated runs.

## Invariants

- No module may assume live DB on import.
- Schema changes must be represented by Alembic revisions.
- Backward compatibility of running pipelines must be considered in every migration.
- Any new table used as cross-module contract must be documented here.

## Migration policy

- Every schema change: migration + rationale in `DECISIONS.md` and iteration log.
- Avoid destructive migrations without explicit rollout/rollback plan.
- For lock-sensitive changes, use configured lock timeout and maintenance windows.
