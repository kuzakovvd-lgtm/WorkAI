# Domain Glossary

## Core entities

- `sheet_cells`: raw cell-level data ingested from source sheets.
- `raw_tasks`: parsed task rows extracted from raw sheet representations.
- `tasks_normalized`: canonical task representation used by downstream modules.
- `daily_task_assessments`: per-day/per-task scoring results.
- `employee_daily_ghost_time`: per-employee/day ghost-time aggregates.
- `dynamic_task_norms`: evolving baseline norms used by assessment logic.
- `audit_runs`: persisted records of AI audit executions.

## Module terms

- Ingest: fetches raw external data into staging structures.
- Parse: transforms staged raw data into task rows.
- Normalize: canonicalizes heterogeneous task rows.
- Assess: computes quantitative quality metrics.
- Audit: AI reasoning/reporting on assessed and normalized data.
- Ops: operational jobs and system diagnostics.

## Operational terms

- Ghost time: time entries classified as suspicious/non-productive by defined rules.
- Baseline migration: initial Alembic revision that anchors schema history.
