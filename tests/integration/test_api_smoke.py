from __future__ import annotations

import hashlib
import os
from datetime import date
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from WorkAI.audit.models import AuditRunResult
from WorkAI.config import get_settings
from WorkAI.db import close_db, connection, init_db


@pytest.mark.integration
def test_api_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    dsn = os.getenv("WORKAI_DB__DSN", "").strip()
    if not dsn:
        pytest.skip("WORKAI_DB__DSN is not set")

    employee_id = 93001
    spreadsheet_id = "api-smoke-sheet"
    task_day = date(2099, 2, 1)
    raw_task_id = 93001001
    normalized_task_id = 93001001
    existing_run_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    start_run_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")

    monkeypatch.setenv("WORKAI_API_KEY", "integration-api-key")
    monkeypatch.setenv("WORKAI_AUDIT__ENABLED", "true")
    get_settings.cache_clear()

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    init_db()
    try:
        with connection() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM audit_feedback")
            cur.execute("DELETE FROM audit_runs WHERE employee_id = %s AND task_date = %s", (employee_id, task_day))
            cur.execute("DELETE FROM daily_task_assessments WHERE employee_id = %s AND task_date = %s", (employee_id, task_day))
            cur.execute("DELETE FROM operational_cycles WHERE employee_id = %s AND task_date = %s", (employee_id, task_day))
            cur.execute("DELETE FROM daily_task_assessments WHERE normalized_task_id = %s", (normalized_task_id,))
            cur.execute("DELETE FROM tasks_normalized WHERE id = %s", (normalized_task_id,))
            cur.execute("DELETE FROM raw_tasks WHERE raw_task_id = %s", (raw_task_id,))
            cur.execute("DELETE FROM tasks_normalized WHERE employee_id = %s AND task_date = %s", (employee_id, task_day))
            cur.execute("DELETE FROM raw_tasks WHERE spreadsheet_id = %s", (spreadsheet_id,))
            cur.execute("DELETE FROM employee_daily_ghost_time WHERE employee_id = %s AND task_date = %s", (employee_id, task_day))
            cur.execute("DELETE FROM employees WHERE employee_id = %s", (employee_id,))
            cur.execute(
                """
                INSERT INTO employees (employee_id, employee_name_norm)
                VALUES (%s, %s)
                ON CONFLICT (employee_id) DO UPDATE SET employee_name_norm = EXCLUDED.employee_name_norm
                """,
                (employee_id, "api-smoke-employee"),
            )
            cur.execute(
                """
                INSERT INTO raw_tasks (
                    raw_task_id,
                    spreadsheet_id,
                    sheet_title,
                    row_idx,
                    col_idx,
                    cell_a1,
                    cell_ingested_at,
                    employee_name_raw,
                    work_date,
                    line_no,
                    line_text,
                    parsed_at
                )
                VALUES (%s, %s, 'Sheet1', 2, 2, 'B2', now(), 'Api Employee', %s, 1, 'Task api', now())
                """,
                (raw_task_id, spreadsheet_id, task_day),
            )
            cur.execute(
                """
                INSERT INTO tasks_normalized (
                    id,
                    raw_task_id,
                    task_date,
                    employee_id,
                    spreadsheet_id,
                    sheet_title,
                    row_idx,
                    col_idx,
                    line_no,
                    work_date,
                    employee_name_raw,
                    employee_name_norm,
                    employee_match_method,
                    task_text_raw,
                    task_text_norm,
                    duration_minutes,
                    time_source,
                    is_smart,
                    is_micro,
                    result_confirmed,
                    is_zhdun,
                    category_code,
                    task_category,
                    canonical_text,
                    normalized_at,
                    source_cell_ingested_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, 'Sheet1', 2, 2, 1, %s,
                    'Api Employee', 'api-smoke-employee', 'exact', 'Task api', 'Task api',
                    120, 'logged', true, false, true, false,
                    'analysis', 'analysis', 'Task api', now(), now()
                )
                ON CONFLICT (id) DO NOTHING
                """,
                (normalized_task_id, raw_task_id, task_day, employee_id, spreadsheet_id, task_day),
            )
            cur.execute(
                """
                INSERT INTO employee_daily_ghost_time (
                    employee_id,
                    task_date,
                    workday_minutes,
                    logged_minutes,
                    ghost_minutes,
                    index_of_trust_base
                )
                VALUES (%s, %s, 480, 120, 360, 0.750)
                ON CONFLICT (employee_id, task_date)
                DO UPDATE SET ghost_minutes = EXCLUDED.ghost_minutes
                """,
                (employee_id, task_day),
            )
            cur.execute(
                """
                INSERT INTO daily_task_assessments (
                    normalized_task_id,
                    employee_id,
                    task_date,
                    norm_minutes,
                    delta_minutes,
                    quality_score,
                    smart_score
                )
                VALUES (%s, %s, %s, 60, 60, 0.900, 0.800)
                ON CONFLICT (normalized_task_id)
                DO UPDATE SET quality_score = EXCLUDED.quality_score
                """,
                (normalized_task_id, employee_id, task_day),
            )
            cur.execute(
                """
                INSERT INTO operational_cycles (
                    employee_id,
                    task_date,
                    cycle_key,
                    canonical_text,
                    task_category,
                    total_duration_minutes,
                    tasks_count,
                    is_zhdun,
                    avg_quality_score,
                    avg_smart_score
                )
                VALUES (%s, %s, 'api-cycle-1', 'Task api', 'analysis', 120, 1, false, 0.9, 0.8)
                ON CONFLICT (employee_id, task_date, cycle_key)
                DO UPDATE SET total_duration_minutes = EXCLUDED.total_duration_minutes
                """,
                (employee_id, task_day),
            )
            cur.execute(
                """
                INSERT INTO audit_runs (
                    id,
                    employee_id,
                    task_date,
                    status,
                    report_json,
                    forced
                )
                VALUES (%s, %s, %s, 'completed', '{"executive_summary":"seed"}'::jsonb, false)
                ON CONFLICT (id) DO NOTHING
                """,
                (existing_run_id, employee_id, task_day),
            )
            cur.execute(
                """
                INSERT INTO audit_cost_daily (rollup_date, runs_count, input_tokens, output_tokens, cost_usd)
                VALUES (%s, 1, 100, 50, 0.1234)
                ON CONFLICT (rollup_date) DO UPDATE SET runs_count = EXCLUDED.runs_count
                """,
                (task_day,),
            )

            error_message = "api smoke pipeline error"
            source_ref = f"{spreadsheet_id}:Sheet1:B2"
            hash_source = f"normalize|{source_ref}|ValueError|{error_message}"
            error_hash = hashlib.sha256(hash_source.encode("utf-8")).hexdigest()
            cur.execute(
                """
                INSERT INTO pipeline_errors (
                    phase,
                    run_id,
                    sheet_id,
                    work_date,
                    source_ref,
                    error_type,
                    error_message,
                    payload_excerpt,
                    error_hash
                )
                VALUES ('normalize', 'api-smoke-run', 'Sheet1', %s, %s, 'ValueError', %s, '{"test":true}', %s)
                ON CONFLICT (phase, source_ref, error_hash)
                DO UPDATE SET created_at = now()
                """,
                (task_day, source_ref, error_message, error_hash),
            )
            conn.commit()
    finally:
        close_db()

    from WorkAI.api import main as api_main
    from WorkAI.api.routes import analysis as analysis_routes

    def fake_run_audit(
        emp_id: int,
        run_day: date,
        *,
        force: bool = False,
        manage_db_lifecycle: bool = True,
    ) -> AuditRunResult:
        assert emp_id == employee_id
        assert run_day == task_day
        assert manage_db_lifecycle is False
        return AuditRunResult(
            run_id=start_run_id,
            employee_id=emp_id,
            task_date=run_day,
            status="completed" if force else "completed_cached",
            report_json={"executive_summary": "api-run"},
            cached=not force,
        )

    monkeypatch.setattr(analysis_routes, "_resolve_run_audit", lambda: fake_run_audit)

    headers = {"X-API-Key": "integration-api-key"}
    with TestClient(api_main.app) as client:
        health = client.get("/health")
        assert health.status_code == 200

        deep = client.get("/health/deep", headers=headers)
        assert deep.status_code == 200
        assert deep.json()["db_ok"] is True

        raw_resp = client.get("/tasks/raw", headers=headers, params={"employee_id": employee_id, "task_date": str(task_day)})
        assert raw_resp.status_code == 200
        assert len(raw_resp.json()) == 1

        norm_resp = client.get(
            "/tasks/normalized",
            headers=headers,
            params={"employee_id": employee_id, "task_date": str(task_day)},
        )
        assert norm_resp.status_code == 200
        assert norm_resp.json()[0]["id"] == normalized_task_id

        agg_resp = client.get(
            "/tasks/aggregated",
            headers=headers,
            params={"employee_id": employee_id, "task_date": str(task_day)},
        )
        assert agg_resp.status_code == 200
        assert agg_resp.json()[0]["cycle_key"] == "api-cycle-1"

        start_resp = client.post(
            "/analysis/start",
            headers=headers,
            json={"employee_id": employee_id, "task_date": str(task_day), "force": False},
        )
        assert start_resp.status_code == 200
        assert start_resp.json()["run_id"] == str(start_run_id)

        status_resp = client.get(f"/analysis/status/{existing_run_id}", headers=headers)
        assert status_resp.status_code == 200
        assert status_resp.json()["id"] == str(existing_run_id)

        history_resp = client.get(
            "/analysis/history",
            headers=headers,
            params={"employee_id": employee_id, "from": str(task_day), "to": str(task_day)},
        )
        assert history_resp.status_code == 200
        assert len(history_resp.json()) >= 1

        feedback_resp = client.post(
            f"/analysis/{existing_run_id}/feedback",
            headers=headers,
            json={"rating": 5, "comment": "ok"},
        )
        assert feedback_resp.status_code == 200

        team_resp = client.get("/team/overview", headers=headers, params={"task_date": str(task_day)})
        assert team_resp.status_code == 200
        assert team_resp.json()[0]["employee_id"] == employee_id

        debug_logs_resp = client.get("/debug/logs", headers=headers)
        assert debug_logs_resp.status_code == 200
        assert len(debug_logs_resp.json()) >= 1

        debug_cost_resp = client.get(
            "/debug/cost",
            headers=headers,
            params={"from": str(task_day), "to": str(task_day)},
        )
        assert debug_cost_resp.status_code == 200
        assert len(debug_cost_resp.json()) == 1

    init_db()
    try:
        with connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM audit_feedback WHERE run_id = %s", (existing_run_id,))
            count_row = cur.fetchone()
            assert count_row is not None
            assert int(count_row[0]) >= 1
    finally:
        close_db()
