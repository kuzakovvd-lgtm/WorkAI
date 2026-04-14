"""SQL access helpers for FastAPI routes."""

from __future__ import annotations

from datetime import date
from typing import Any, cast
from uuid import UUID

from psycopg import Cursor


def fetch_health_deep(cur: Cursor[object]) -> tuple[bool, str | None]:
    """Return DB reachability and current alembic revision."""

    cur.execute("SELECT 1")
    cur.fetchone()
    cur.execute("SELECT to_regclass('public.alembic_version')")
    row = cast(tuple[Any, ...] | None, cur.fetchone())
    if row is None or row[0] is None:
        return True, None
    cur.execute("SELECT version_num FROM alembic_version LIMIT 1")
    version_row = cast(tuple[Any, ...] | None, cur.fetchone())
    return True, None if version_row is None else str(version_row[0])


def fetch_raw_tasks(cur: Cursor[object], employee_id: int, task_date: date) -> list[tuple[Any, ...]]:
    """Read raw tasks by employee/date via tasks_normalized linkage."""

    cur.execute(
        """
        SELECT
            rt.raw_task_id,
            rt.spreadsheet_id,
            rt.sheet_title,
            rt.row_idx,
            rt.col_idx,
            rt.cell_a1,
            rt.cell_ingested_at,
            rt.employee_name_raw,
            rt.work_date,
            rt.line_no,
            rt.line_text,
            rt.parsed_at
        FROM raw_tasks AS rt
        JOIN tasks_normalized AS tn
          ON tn.raw_task_id = rt.raw_task_id
        WHERE tn.employee_id = %s
          AND tn.task_date = %s
        ORDER BY rt.sheet_title, rt.row_idx, rt.col_idx, rt.line_no
        """,
        (employee_id, task_date),
    )
    rows = cast(list[tuple[Any, ...]], cur.fetchall())
    return rows


def fetch_normalized_tasks(cur: Cursor[object], employee_id: int, task_date: date) -> list[tuple[Any, ...]]:
    """Read normalized tasks by employee/day."""

    cur.execute(
        """
        SELECT
            id,
            raw_task_id,
            employee_id,
            task_date,
            canonical_text,
            duration_minutes,
            task_category,
            time_source,
            is_smart,
            is_micro,
            result_confirmed,
            is_zhdun,
            normalized_at,
            spreadsheet_id,
            sheet_title,
            row_idx,
            col_idx,
            line_no
        FROM tasks_normalized
        WHERE employee_id = %s
          AND task_date = %s
        ORDER BY sheet_title, row_idx, col_idx, line_no, id
        """,
        (employee_id, task_date),
    )
    rows = cast(list[tuple[Any, ...]], cur.fetchall())
    return rows


def fetch_aggregated_cycles(cur: Cursor[object], employee_id: int, task_date: date) -> list[tuple[Any, ...]]:
    """Read operational cycles by employee/day."""

    cur.execute(
        """
        SELECT
            id,
            employee_id,
            task_date,
            cycle_key,
            canonical_text,
            task_category,
            total_duration_minutes,
            tasks_count,
            is_zhdun,
            avg_quality_score,
            avg_smart_score,
            created_at
        FROM operational_cycles
        WHERE employee_id = %s
          AND task_date = %s
        ORDER BY cycle_key
        """,
        (employee_id, task_date),
    )
    rows = cast(list[tuple[Any, ...]], cur.fetchall())
    return rows


def fetch_audit_run(cur: Cursor[object], run_id: UUID) -> tuple[Any, ...] | None:
    """Read one audit run by id."""

    cur.execute(
        """
        SELECT
            id,
            employee_id,
            task_date,
            status,
            started_at,
            finished_at,
            report_json,
            error,
            forced
        FROM audit_runs
        WHERE id = %s
        """,
        (run_id,),
    )
    row = cast(tuple[Any, ...] | None, cur.fetchone())
    return row


def fetch_audit_history(
    cur: Cursor[object],
    employee_id: int,
    from_date: date | None,
    to_date: date | None,
) -> list[tuple[Any, ...]]:
    """Read audit run history with optional date bounds."""

    cur.execute(
        """
        SELECT
            id,
            employee_id,
            task_date,
            status,
            started_at,
            finished_at,
            forced
        FROM audit_runs
        WHERE employee_id = %s
          AND (%s::date IS NULL OR task_date >= %s::date)
          AND (%s::date IS NULL OR task_date <= %s::date)
        ORDER BY task_date DESC, started_at DESC
        """,
        (employee_id, from_date, from_date, to_date, to_date),
    )
    rows = cast(list[tuple[Any, ...]], cur.fetchall())
    return rows


def insert_audit_feedback(
    cur: Cursor[object],
    run_id: UUID,
    rating: int | None,
    comment: str | None,
    submitted_by: str | None,
) -> None:
    """Insert audit feedback row."""

    cur.execute(
        """
        INSERT INTO audit_feedback (run_id, rating, comment, submitted_by)
        VALUES (%s, %s, %s, %s)
        """,
        (run_id, rating, comment, submitted_by),
    )


def fetch_team_overview(cur: Cursor[object], task_date: date) -> list[tuple[Any, ...]]:
    """Return daily team summary view from assess outputs."""

    cur.execute(
        """
        SELECT
            edgt.employee_id,
            edgt.task_date,
            edgt.ghost_minutes,
            (edgt.ghost_minutes::float / 60.0) AS ghost_hours,
            edgt.index_of_trust_base::float,
            COALESCE(dta.tasks_count, 0)::int,
            COALESCE(oc.cycles_count, 0)::int
        FROM employee_daily_ghost_time AS edgt
        LEFT JOIN (
            SELECT employee_id, task_date, COUNT(*) AS tasks_count
            FROM daily_task_assessments
            WHERE task_date = %s
            GROUP BY employee_id, task_date
        ) AS dta
          ON dta.employee_id = edgt.employee_id
         AND dta.task_date = edgt.task_date
        LEFT JOIN (
            SELECT employee_id, task_date, COUNT(*) AS cycles_count
            FROM operational_cycles
            WHERE task_date = %s
            GROUP BY employee_id, task_date
        ) AS oc
          ON oc.employee_id = edgt.employee_id
         AND oc.task_date = edgt.task_date
        WHERE edgt.task_date = %s
        ORDER BY edgt.employee_id
        """,
        (task_date, task_date, task_date),
    )
    rows = cast(list[tuple[Any, ...]], cur.fetchall())
    return rows


def fetch_debug_logs(cur: Cursor[object], limit: int) -> list[tuple[Any, ...]]:
    """Return recent pipeline and audit failure logs."""

    cur.execute(
        """
        SELECT
            source,
            created_at,
            phase,
            run_id,
            source_ref,
            error_type,
            error_message
        FROM (
            SELECT
                'pipeline_errors'::text AS source,
                pe.created_at,
                pe.phase,
                pe.run_id,
                pe.source_ref,
                pe.error_type,
                pe.error_message
            FROM pipeline_errors AS pe
            UNION ALL
            SELECT
                'audit_runs'::text AS source,
                ar.started_at AS created_at,
                'audit'::text AS phase,
                ar.id::text AS run_id,
                (ar.employee_id::text || ':' || ar.task_date::text) AS source_ref,
                'run_failed'::text AS error_type,
                COALESCE(ar.error, 'unknown error') AS error_message
            FROM audit_runs AS ar
            WHERE ar.status = 'failed'
        ) AS logs
        ORDER BY created_at DESC
        LIMIT %s
        """,
        (limit,),
    )
    rows = cast(list[tuple[Any, ...]], cur.fetchall())
    return rows


def fetch_debug_cost(cur: Cursor[object], from_date: date | None, to_date: date | None) -> list[tuple[Any, ...]]:
    """Return audit daily cost rollups."""

    cur.execute(
        """
        SELECT
            rollup_date,
            runs_count,
            input_tokens,
            output_tokens,
            cost_usd::float,
            rollup_at
        FROM audit_cost_daily
        WHERE (%s::date IS NULL OR rollup_date >= %s::date)
          AND (%s::date IS NULL OR rollup_date <= %s::date)
        ORDER BY rollup_date DESC
        """,
        (from_date, from_date, to_date, to_date),
    )
    rows = cast(list[tuple[Any, ...]], cur.fetchall())
    return rows


def update_task_result_confirmed(
    cur: Cursor[object],
    normalized_task_id: int,
    result_confirmed: bool,
) -> tuple[Any, ...] | None:
    """Update one tasks_normalized.result_confirmed row and return id/state."""

    cur.execute(
        """
        UPDATE tasks_normalized
        SET result_confirmed = %s,
            normalized_at = now()
        WHERE id = %s
        RETURNING id, result_confirmed, normalized_at
        """,
        (result_confirmed, normalized_task_id),
    )
    row = cast(tuple[Any, ...] | None, cur.fetchone())
    return row


def fetch_result_confirmed_daily_report(cur: Cursor[object], to_date: date | None) -> list[tuple[Any, ...]]:
    """Return daily result_confirmed report up to selected date."""

    cur.execute(
        """
        SELECT
            task_date,
            COUNT(*)::int AS total,
            COUNT(*) FILTER (WHERE result_confirmed)::int AS done,
            ROUND(
                100.0 * COUNT(*) FILTER (WHERE result_confirmed) / NULLIF(COUNT(*), 0),
                1
            )::float AS pct
        FROM tasks_normalized
        WHERE task_date <= COALESCE(%s::date, current_date)
        GROUP BY task_date
        ORDER BY task_date DESC
        """,
        (to_date,),
    )
    rows = cast(list[tuple[Any, ...]], cur.fetchall())
    return rows
