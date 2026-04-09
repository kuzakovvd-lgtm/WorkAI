from __future__ import annotations

import os
from datetime import date
from typing import Any, ClassVar

import pytest
from alembic import command
from alembic.config import Config
from WorkAI.audit import crew as audit_crew_module
from WorkAI.audit import run_audit
from WorkAI.config import get_settings
from WorkAI.db import close_db, connection, init_db


@pytest.mark.integration
def test_audit_run_cache_and_force_semantics(monkeypatch: pytest.MonkeyPatch) -> None:
    dsn = os.getenv("WORKAI_DB__DSN", "").strip()
    if not dsn:
        pytest.skip("WORKAI_DB__DSN is not set")

    employee_id = 91001
    target_date = date(2099, 1, 8)

    os.environ["WORKAI_AUDIT__ENABLED"] = "true"
    get_settings.cache_clear()

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    init_db()
    try:
        with connection() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM audit_feedback")
            cur.execute("DELETE FROM audit_runs WHERE employee_id = %s AND task_date = %s", (employee_id, target_date))
            cur.execute(
                "DELETE FROM operational_cycles WHERE employee_id = %s AND task_date = %s",
                (employee_id, target_date),
            )
            cur.execute(
                "DELETE FROM employee_daily_ghost_time WHERE employee_id = %s AND task_date = %s",
                (employee_id, target_date),
            )
            cur.execute(
                """
                INSERT INTO employee_daily_ghost_time (
                    employee_id, task_date, workday_minutes, logged_minutes, ghost_minutes, index_of_trust_base
                )
                VALUES (%s, %s, 480, 180, 300, 0.600)
                ON CONFLICT (employee_id, task_date)
                DO UPDATE SET ghost_minutes = EXCLUDED.ghost_minutes, index_of_trust_base = EXCLUDED.index_of_trust_base
                """,
                (employee_id, target_date),
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
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (employee_id, task_date, cycle_key)
                DO UPDATE SET canonical_text = EXCLUDED.canonical_text
                """,
                (
                    employee_id,
                    target_date,
                    "cycle-1",
                    "Investigate ghost blocks",
                    "analysis",
                    180,
                    3,
                    False,
                    "0.800",
                    "0.700",
                ),
            )
            conn.commit()
    finally:
        close_db()

    calls: dict[str, Any] = {"kickoff": 0, "use_tool": []}

    class FakeCrew:
        usage_metrics: ClassVar[dict[str, float]] = {
            "input_tokens": 120,
            "output_tokens": 80,
            "cost_usd": 0.11,
        }

        def kickoff(self, *, inputs: dict[str, Any]) -> dict[str, Any]:
            calls["kickoff"] += 1
            assert "aggregated_tasks_json" in inputs
            return {
                "executive_summary": "Audit summary",
                "top_3_priorities": [{"title": "Reduce ghost time", "rationale": "High ghost hours"}],
                "high_priority_employees": [],
                "key_findings": ["Ghost concentration in analysis cycles"],
                "smart_actions": ["Break long cycles into measurable outputs"],
                "blockers_zhdun": [],
                "methodology_recommendation": "Use methodology KB section on ghost time",
            }

    def fake_crew_builder(*, settings, use_methodology_tool):  # type: ignore[no-untyped-def]
        del settings
        calls["use_tool"].append(use_methodology_tool)
        return FakeCrew()

    prefetch_calls = {"count": 0}
    original_prefetch = audit_crew_module.fetch_prefetch_payload

    def counting_prefetch(cur, run_employee_id, run_task_date):  # type: ignore[no-untyped-def]
        prefetch_calls["count"] += 1
        return original_prefetch(cur, run_employee_id, run_task_date)

    monkeypatch.setattr(audit_crew_module, "fetch_prefetch_payload", counting_prefetch)

    first = run_audit(employee_id, target_date, crew_builder=fake_crew_builder)
    second = run_audit(employee_id, target_date, crew_builder=fake_crew_builder)
    third = run_audit(employee_id, target_date, force=True, crew_builder=fake_crew_builder)

    assert first.status == "completed"
    assert first.cached is False
    assert second.status == "completed_cached"
    assert second.cached is True
    assert third.status == "completed"
    assert calls["kickoff"] == 2
    assert calls["use_tool"] == [True, True]
    assert prefetch_calls["count"] == 2
    assert "_usage" in first.report_json

    init_db()
    try:
        with connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT status, count(*)
                FROM audit_runs
                WHERE employee_id = %s
                  AND task_date = %s
                GROUP BY status
                ORDER BY status
                """,
                (employee_id, target_date),
            )
            rows = cur.fetchall()
    finally:
        close_db()

    summary = {status: int(count) for status, count in rows}
    assert summary["completed"] == 2
    assert summary["completed_cached"] == 1


@pytest.mark.integration
def test_audit_failed_status_on_crew_error() -> None:
    dsn = os.getenv("WORKAI_DB__DSN", "").strip()
    if not dsn:
        pytest.skip("WORKAI_DB__DSN is not set")

    employee_id = 91002
    target_date = date(2099, 1, 9)

    os.environ["WORKAI_AUDIT__ENABLED"] = "true"
    get_settings.cache_clear()

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    init_db()
    try:
        with connection() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM audit_runs WHERE employee_id = %s AND task_date = %s", (employee_id, target_date))
            cur.execute(
                "DELETE FROM operational_cycles WHERE employee_id = %s AND task_date = %s",
                (employee_id, target_date),
            )
            cur.execute(
                "DELETE FROM employee_daily_ghost_time WHERE employee_id = %s AND task_date = %s",
                (employee_id, target_date),
            )
            cur.execute(
                """
                INSERT INTO employee_daily_ghost_time (
                    employee_id, task_date, workday_minutes, logged_minutes, ghost_minutes, index_of_trust_base
                )
                VALUES (%s, %s, 480, 120, 360, 0.500)
                ON CONFLICT (employee_id, task_date)
                DO UPDATE SET ghost_minutes = EXCLUDED.ghost_minutes, index_of_trust_base = EXCLUDED.index_of_trust_base
                """,
                (employee_id, target_date),
            )
            conn.commit()
    finally:
        close_db()

    class FailingCrew:
        def kickoff(self, *, inputs: dict[str, Any]) -> dict[str, Any]:
            del inputs
            raise RuntimeError("LLM unavailable")

    def failing_crew_builder(*, settings, use_methodology_tool):  # type: ignore[no-untyped-def]
        del settings
        del use_methodology_tool
        return FailingCrew()

    with pytest.raises(RuntimeError):
        run_audit(employee_id, target_date, force=True, crew_builder=failing_crew_builder)

    init_db()
    try:
        with connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT status
                FROM audit_runs
                WHERE employee_id = %s
                  AND task_date = %s
                ORDER BY started_at DESC
                LIMIT 1
                """,
                (employee_id, target_date),
            )
            row = cur.fetchone()
    finally:
        close_db()

    assert row is not None
    assert row[0] == "failed"
