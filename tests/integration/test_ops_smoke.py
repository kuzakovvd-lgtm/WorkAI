from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from WorkAI.config import get_settings
from WorkAI.db import close_db, connection, init_db
from WorkAI.ops.cost_rollup import run_cost_rollup
from WorkAI.ops.healthcheck import run_healthcheck
from WorkAI.ops.stale_sweeper import run_stale_sweeper
from WorkAI.ops.verify_units import run_verify_units


@pytest.mark.integration
def test_ops_smoke(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    dsn = os.getenv("WORKAI_DB__DSN", "").strip()
    if not dsn:
        pytest.skip("WORKAI_DB__DSN is not set")

    target_day = date(2099, 3, 1)
    processing_run_id = UUID("11111111-1111-1111-1111-111111111111")

    get_settings.cache_clear()
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    init_db()
    try:
        with connection() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM audit_feedback")
            cur.execute("DELETE FROM audit_runs WHERE task_date = %s", (target_day,))
            cur.execute("DELETE FROM audit_cost_daily WHERE rollup_date = %s", (target_day,))

            cur.execute(
                """
                INSERT INTO audit_runs (id, employee_id, task_date, status, started_at, report_json, forced)
                VALUES (%s, 7, %s, 'processing', now() - interval '20 minutes', NULL, false)
                """,
                (processing_run_id, target_day),
            )

            cur.execute(
                """
                INSERT INTO audit_runs (employee_id, task_date, status, started_at, report_json, forced)
                VALUES
                  (7, %s, 'completed', now(), '{"_usage": {"input_tokens": 10, "output_tokens": 5, "cost_usd": 0.10}}'::jsonb, false),
                  (8, %s, 'completed_cached', now(), '{"_usage": {"input_tokens": 20, "output_tokens": 8, "cost_usd": 0.20}}'::jsonb, false),
                  (9, %s, 'completed', now(), '{"note": "missing usage"}'::jsonb, false)
                """,
                (target_day, target_day, target_day),
            )
            conn.commit()
    finally:
        close_db()

    stale_result = run_stale_sweeper(threshold_minutes=15)
    assert stale_result.rows_updated >= 1

    init_db()
    try:
        with connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT status, error FROM audit_runs WHERE id = %s", (processing_run_id,))
            stale_row = cur.fetchone()
        assert stale_row is not None
        assert stale_row[0] == "stale"
        assert stale_row[1] == "sweeper_timeout"
    finally:
        close_db()

    rollup_result = run_cost_rollup(target_day)
    assert rollup_result.runs_seen >= 3
    assert rollup_result.usage_rows_used == 2
    assert rollup_result.usage_rows_skipped >= 1
    assert rollup_result.input_tokens == 30
    assert rollup_result.output_tokens == 13
    assert abs(rollup_result.cost_usd - 0.3) < 1e-9

    init_db()
    try:
        with connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT runs_count, input_tokens, output_tokens, cost_usd FROM audit_cost_daily WHERE rollup_date = %s",
                (target_day,),
            )
            rollup_row = cur.fetchone()
        assert rollup_row is not None
        assert int(rollup_row[0]) == 2
        assert int(rollup_row[1]) == 30
        assert int(rollup_row[2]) == 13
    finally:
        close_db()

    unit_dir = tmp_path / "units"
    unit_dir.mkdir(parents=True, exist_ok=True)
    (unit_dir / "workai-ok.service").write_text(
        "[Service]\nExecStart=/bin/echo /tmp/script.py\n",
        encoding="utf-8",
    )
    (unit_dir / "workai-bad.service").write_text(
        "[Service]\nExecStart=/missing/python /missing/script.py\n",
        encoding="utf-8",
    )

    verify_result = run_verify_units(unit_dir=str(unit_dir))
    assert verify_result.units_checked == 2
    assert any(item.status == "critical" for item in verify_result.units)

    health_result = run_healthcheck(target_date=target_day, unit_dir=str(unit_dir))
    assert health_result.severity in {"info", "data_warning", "infra_critical"}
    assert any(check.name == "db_reachable" for check in health_result.checks)
