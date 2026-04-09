# Database Contract

## Principle

Database schema is the formal contract between modules.

## Dependency contract

- `api`, `ops` may depend on pipeline modules.
- All modules may depend on `db`, `config`, `common`.
- Reverse/circular imports across domain modules are forbidden.

## Current contract state (Phase 2/3/4.5)

- Alembic chain: `0001_baseline` -> `0002_sheet_cells` -> `0003_raw_tasks` -> `0004_tasks_normalized` -> `0005_pipeline_errors`.
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

### `tasks_normalized` (normalize -> assess contract)

- Purpose: deterministic canonical form of parsed task lines for downstream assessment.
- Natural uniqueness: `(spreadsheet_id, sheet_title, row_idx, col_idx, line_no)`.
- Required lineage columns:
  - source coordinates (`spreadsheet_id`, `sheet_title`, `row_idx`, `col_idx`, `line_no`),
  - `source_cell_ingested_at` copied from parse source for traceability.
- Core normalized payload:
  - employee mapping (`employee_name_raw`, `employee_name_norm`, `employee_match_method`),
  - normalized text (`task_text_raw`, `task_text_norm`),
  - optional extracted time info (`time_start`, `time_end`, `duration_minutes`),
  - optional classification (`category_code`).
- Indexes:
  - `(spreadsheet_id, sheet_title)` for sheet-scoped refresh/read,
  - `(employee_name_norm, work_date)` for assess filtering.
- Idempotency expectation:
  - normalize MVP uses full-refresh per sheet/date (`DELETE sheet+date -> INSERT normalized rows`) and must not duplicate rows on repeated runs.
  - single-flight safety is enforced by advisory lock key `normalize|<spreadsheet_id>:<sheet_title>|<work_date>`.

### `pipeline_errors` (cross-phase DLQ-style error contract)

- Purpose: persist record-level processing failures without crashing whole runs.
- Primary key: `id` (bigserial).
- Required fields:
  - `phase`, `run_id`, `source_ref`, `error_type`, `error_message`, `created_at`.
- Optional context:
  - `sheet_id`, `work_date`, `payload_excerpt`.
- Deduplication:
  - `UNIQUE (phase, source_ref, error_hash)` to merge repeated identical failures.
- Indexes:
  - `(phase, created_at)` for recent incident review,
  - `(sheet_id, work_date)` for targeted reprocessing,
  - `(run_id)` for per-run troubleshooting.
- Retention:
  - MVP policy is 90 days with periodic cleanup batches (see `RUNBOOK.md`).

## Invariants

- No module may assume live DB on import.
- Schema changes must be represented by Alembic revisions.
- Backward compatibility of running pipelines must be considered in every migration.
- Any new table used as cross-module contract must be documented here.

## Migration policy

- Every schema change: migration + rationale in `DECISIONS.md` and iteration log.
- Avoid destructive migrations without explicit rollout/rollback plan.
- For lock-sensitive changes, use configured lock timeout and maintenance windows.
