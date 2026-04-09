# Database Contract

## Principle

Database schema is the formal contract between modules.

## Dependency contract

- `api`, `ops` may depend on pipeline modules.
- All modules may depend on `db`, `config`, `common`.
- Reverse/circular imports across domain modules are forbidden.

## Current contract state (Phase 2/3/4.5/5.4/6/7/9/10)

- Alembic chain: `0001_baseline` -> `0002_sheet_cells` -> `0003_raw_tasks` -> `0004_tasks_normalized` -> `0005_pipeline_errors` -> `0006_employee_daily_ghost_time` -> `0007_tasks_norm_contract` -> `0008_daily_task_assess` -> `0009_tasks_norm_time_source` -> `0010_operational_cycles` -> `0011_dynamic_task_norms` -> `0012_knowledge_base_articles` -> `0013_audit_tables` -> `0014_notification_log`.
- Runtime DB access goes through `WorkAI.db` helpers and explicit `init_db()`.

Ops phase (10) adds no new DB tables; it operates on existing contracts:
- `audit_runs` (stale sweeper, error-rate checks),
- `audit_cost_daily` (daily rollup upsert),
- `raw_tasks` / `tasks_normalized` (health volume/freshness checks),
- `pipeline_errors` (health signal surface),
- `notification_log` (downstream notifier observability).

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
- Contract columns required by assess:
  - `raw_task_id`, `task_date`, `employee_id`, `canonical_text`, `duration_minutes`,
    `task_category`, `time_source`, `is_smart`, `is_micro`, `result_confirmed`,
    `is_zhdun`, `normalized_at`.
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
  - `(employee_id, task_date)` for assess ghost-time aggregation.
- Idempotency expectation:
  - normalize MVP uses full-refresh per sheet/date (`DELETE sheet+date -> INSERT normalized rows`) and must not duplicate rows on repeated runs.
  - single-flight safety is enforced by advisory lock key `normalize|<spreadsheet_id>:<sheet_title>|<work_date>`.

### `employees` (normalize-assigned identity contract)

- Purpose: stable non-hash employee identity for downstream assess.
- Primary key: `employee_id`.
- Uniqueness: `employee_name_norm`.
- Ownership:
  - populated/upserted only by normalize,
  - consumed by normalize + assess.

### `employee_daily_ghost_time` (assess Step 1 output)

- Purpose: per-employee/day ghost minutes and base trust index.
- Primary key: `(employee_id, task_date)`.
- Core metrics:
  - `workday_minutes`, `logged_minutes`, `ghost_minutes`, `index_of_trust_base`.
- Idempotency expectation:
  - assess Step 1 uses UPSERT by `(employee_id, task_date)`; reruns update in-place without duplicates.

### `daily_task_assessments` (assess Step 2 output)

- Purpose: per-task deterministic scoring values (`quality_score`, `smart_score`) linked to normalized tasks.
- Primary key: `id` (bigserial).
- Uniqueness: `normalized_task_id`.
- Indexes:
  - `(employee_id, task_date)` for day-level rollups and Step 3 joins.
- Idempotency expectation:
  - assess Step 2 uses UPSERT on `normalized_task_id`; reruns update row scores in place.
  - assess Step 4 recomputes `norm_minutes` and `delta_minutes` in place without duplicating rows.

### `operational_cycles` (assess Step 3 output, assess -> audit contract)

- Purpose: deterministic aggregation of normalized tasks into operational cycles.
- Primary key: `id` (bigserial).
- Uniqueness: `(employee_id, task_date, cycle_key)`.
- Core payload:
  - `canonical_text`, `task_category`, `total_duration_minutes`, `tasks_count`,
    `is_zhdun`, `avg_quality_score`, `avg_smart_score`.
- Indexes:
  - `(employee_id, task_date)` for employee/day fetch,
  - `(task_date)` for day-wide operational/audit prefetch.
- Idempotency expectation:
  - assess Step 3 rebuilds cycles per `(employee_id, task_date)` partition and writes deterministic keys; reruns on the same snapshot produce the same cycle keys and metrics.

### `dynamic_task_norms` (assess Step 4 output)

- Purpose: persistent Bayesian-updated duration norms by task category.
- Primary key: `task_category`.
- Core payload:
  - `norm_minutes`, `stddev_minutes`, `sample_size`, `baseline_prior`, `last_updated_at`.
- Idempotency expectation:
  - assess Step 4 uses UPSERT by `task_category`; reruns update norm statistics in place.

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

### `knowledge_base_articles` (knowledge_base -> audit contract)

- Purpose: persistent methodology corpus indexed from markdown sources for FTS lookup.
- Primary key: `id` (bigserial).
- Uniqueness: `source_path`.
- Core payload:
  - `title`, `body`, `tags`, `indexed_at`.
  - generated stored `fts` vector:
    - `to_tsvector('russian', coalesce(title,'') || ' ' || coalesce(body,''))`.
- Indexes:
  - `GIN (fts)` for full-text queries.
- Idempotency expectation:
  - knowledge indexer uses UPSERT by `source_path`; reruns update existing rows and do not duplicate.
  - MVP sync strategy is soft-sync: rows are not deleted when source files disappear from disk.

### `audit_runs` (audit run ledger contract)

- Purpose: persistent run ledger for employee/day CrewAI audits.
- Primary key: `id` (UUID, `gen_random_uuid()`).
- Core payload:
  - execution scope: `employee_id`, `task_date`, `forced`;
  - lifecycle: `status`, `started_at`, `finished_at`, `error`;
  - report output: `report_json` (includes `_usage` telemetry).
- Status contract:
  - `processing`, `completed`, `completed_cached`, `failed`, `stale`.
- Indexes:
  - `(employee_id, task_date, started_at)` for run history lookups,
  - partial processing index for in-flight runs.
- Idempotency expectation:
  - default run (`force=false`) returns cached completed result and writes `completed_cached` ledger row;
  - `force=true` always creates a new run.

### `audit_feedback` (feedback contract)

- Purpose: operator/manager feedback on one audit run.
- Primary key: `id` (bigserial).
- Foreign key: `run_id -> audit_runs(id)` (`ON DELETE CASCADE`).
- Data quality:
  - optional `rating` constrained to `1..5`,
  - free-text `comment`, `submitted_by`, and `submitted_at`.

### `audit_cost_daily` (cost rollup contract)

- Purpose: daily aggregated AI usage/cost accounting.
- Primary key: `rollup_date`.
- Core payload:
  - `runs_count`, `input_tokens`, `output_tokens`, `cost_usd`, `rollup_at`.
- Note:
  - rollup automation is deferred to ops phase; table contract is created in Phase 7.

### `notification_log` (notifier delivery ledger contract)

- Purpose: persistent log of every notifier delivery attempt across channels.
- Primary key: `id` (bigserial).
- Required fields:
  - `sent_at`, `channel`, `level`, `subject`, `delivered`.
- Optional payload:
  - `body`, `error`.
- Idempotency expectation:
  - notifier logs every send attempt as an immutable row;
  - failure path must still insert row with `delivered=false` and non-empty `error`.

## Invariants

- No module may assume live DB on import.
- Schema changes must be represented by Alembic revisions.
- Backward compatibility of running pipelines must be considered in every migration.
- Any new table used as cross-module contract must be documented here.

## Migration policy

- Every schema change: migration + rationale in `DECISIONS.md` and iteration log.
- Avoid destructive migrations without explicit rollout/rollback plan.
- For lock-sensitive changes, use configured lock timeout and maintenance windows.
