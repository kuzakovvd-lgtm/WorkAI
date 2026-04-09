from __future__ import annotations

import os
from datetime import date

import pytest
from alembic import command
from alembic.config import Config
from WorkAI.assess.runner import run_assess_aggregation
from WorkAI.db import close_db, connection, init_db


@pytest.mark.integration
def test_assess_aggregation_smoke_idempotent() -> None:
    dsn = os.getenv("WORKAI_DB__DSN", "").strip()
    if not dsn:
        pytest.skip("WORKAI_DB__DSN is not set")

    target_date = date(2026, 4, 12)
    spreadsheet_id = "assess-aggregation-smoke"

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    init_db()
    try:
        with connection() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM operational_cycles WHERE task_date = %s", (target_date,))
            cur.execute("DELETE FROM daily_task_assessments WHERE task_date = %s", (target_date,))
            cur.execute("DELETE FROM tasks_normalized WHERE spreadsheet_id = %s", (spreadsheet_id,))
            cur.execute("DELETE FROM raw_tasks WHERE spreadsheet_id = %s", (spreadsheet_id,))

            cur.execute(
                """
                INSERT INTO employees (employee_name_norm)
                VALUES (%s)
                ON CONFLICT (employee_name_norm) DO UPDATE
                SET employee_name_norm = EXCLUDED.employee_name_norm
                RETURNING employee_id
                """,
                ("agg-alice",),
            )
            alice_id = int(cur.fetchone()[0])

            cur.execute(
                """
                INSERT INTO employees (employee_name_norm)
                VALUES (%s)
                ON CONFLICT (employee_name_norm) DO UPDATE
                SET employee_name_norm = EXCLUDED.employee_name_norm
                RETURNING employee_id
                """,
                ("agg-bob",),
            )
            bob_id = int(cur.fetchone()[0])

            cur.executemany(
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
                VALUES (%s, %s, %s, %s, %s, %s, now(), %s, %s, %s, %s, now())
                """,
                [
                    (30001, spreadsheet_id, "Sheet1", 2, 2, "B2", "Alice", target_date, 1, "standup sync"),
                    (30002, spreadsheet_id, "Sheet1", 2, 3, "C2", "Alice", target_date, 1, "stand-up sync"),
                    (30003, spreadsheet_id, "Sheet1", 3, 2, "B3", "Alice", target_date, 1, "build api endpoint"),
                    (30004, spreadsheet_id, "Sheet1", 4, 2, "B4", "Alice", target_date, 1, "wait review"),
                    (30005, spreadsheet_id, "Sheet2", 2, 2, "B2", "Bob", target_date, 1, "incident triage"),
                ],
            )

            cur.executemany(
                """
                INSERT INTO tasks_normalized (
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
                    task_category,
                    canonical_text,
                    normalized_at,
                    source_cell_ingested_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, now(), now()
                )
                """,
                [
                    (
                        30001,
                        target_date,
                        alice_id,
                        spreadsheet_id,
                        "Sheet1",
                        2,
                        2,
                        1,
                        target_date,
                        "Alice",
                        "agg-alice",
                        "exact",
                        "standup sync",
                        "standup sync",
                        10,
                        "logged",
                        False,
                        True,
                        True,
                        False,
                        "meeting",
                        "standup sync",
                    ),
                    (
                        30002,
                        target_date,
                        alice_id,
                        spreadsheet_id,
                        "Sheet1",
                        2,
                        3,
                        1,
                        target_date,
                        "Alice",
                        "agg-alice",
                        "exact",
                        "stand-up sync",
                        "stand-up sync",
                        15,
                        "logged",
                        False,
                        True,
                        True,
                        False,
                        "meeting",
                        "stand-up sync",
                    ),
                    (
                        30003,
                        target_date,
                        alice_id,
                        spreadsheet_id,
                        "Sheet1",
                        3,
                        2,
                        1,
                        target_date,
                        "Alice",
                        "agg-alice",
                        "exact",
                        "build api endpoint",
                        "build api endpoint",
                        60,
                        "logged",
                        True,
                        False,
                        True,
                        False,
                        "coding",
                        "build api endpoint",
                    ),
                    (
                        30004,
                        target_date,
                        alice_id,
                        spreadsheet_id,
                        "Sheet1",
                        4,
                        2,
                        1,
                        target_date,
                        "Alice",
                        "agg-alice",
                        "exact",
                        "wait review",
                        "wait review",
                        10,
                        "logged",
                        False,
                        True,
                        False,
                        True,
                        "ops",
                        "wait review",
                    ),
                    (
                        30005,
                        target_date,
                        bob_id,
                        spreadsheet_id,
                        "Sheet2",
                        2,
                        2,
                        1,
                        target_date,
                        "Bob",
                        "agg-bob",
                        "exact",
                        "incident triage",
                        "incident triage",
                        30,
                        "estimated",
                        True,
                        False,
                        True,
                        False,
                        "support",
                        "incident triage",
                    ),
                ],
            )
            cur.execute(
                """
                SELECT raw_task_id, id
                FROM tasks_normalized
                WHERE spreadsheet_id = %s
                  AND task_date = %s
                ORDER BY raw_task_id
                """,
                (spreadsheet_id, target_date),
            )
            task_map = {int(raw_task_id): int(task_id) for raw_task_id, task_id in cur.fetchall()}

            cur.executemany(
                """
                INSERT INTO daily_task_assessments (
                    normalized_task_id,
                    employee_id,
                    task_date,
                    quality_score,
                    smart_score,
                    assessed_at
                )
                VALUES (%s, %s, %s, %s, %s, now())
                ON CONFLICT (normalized_task_id) DO UPDATE
                SET quality_score = EXCLUDED.quality_score,
                    smart_score = EXCLUDED.smart_score,
                    assessed_at = now()
                """,
                [
                    (task_map[30001], alice_id, target_date, "0.800", "0.500"),
                    (task_map[30002], alice_id, target_date, "0.700", "0.400"),
                    (task_map[30003], alice_id, target_date, "1.000", "1.000"),
                    (task_map[30004], alice_id, target_date, "0.200", "0.100"),
                    (task_map[30005], bob_id, target_date, "0.900", "0.900"),
                ],
            )

            conn.commit()

        first = run_assess_aggregation(target_date)
        second = run_assess_aggregation(target_date)

        assert first.employees_processed == 2
        assert first.tasks_aggregated == 5
        assert first.cycles_written == 4
        assert second.cycles_written == 4

        init_db()
        with connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT employee_id, task_category, total_duration_minutes, tasks_count, is_zhdun
                FROM operational_cycles
                WHERE task_date = %s
                ORDER BY employee_id, task_category, total_duration_minutes
                """,
                (target_date,),
            )
            rows = cur.fetchall()

            cur.execute(
                "SELECT count(*), count(distinct cycle_key) FROM operational_cycles WHERE task_date = %s",
                (target_date,),
            )
            counts = cur.fetchone()

            cur.execute(
                "SELECT cycle_key FROM operational_cycles WHERE task_date = %s ORDER BY cycle_key",
                (target_date,),
            )
            keys_before = [str(row[0]) for row in cur.fetchall()]

        run_assess_aggregation(target_date)
        init_db()
        with connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT cycle_key FROM operational_cycles WHERE task_date = %s ORDER BY cycle_key",
                (target_date,),
            )
            keys_after = [str(row[0]) for row in cur.fetchall()]

        assert counts is not None
        assert int(counts[0]) == 4
        assert int(counts[1]) == 4
        assert keys_before == keys_after

        # Alice meeting micro tasks merged into one cycle with total 25 minutes.
        assert (alice_id, "meeting", 25, 2, False) in rows
        # Alice non-micro coding task is singleton cycle.
        assert (alice_id, "coding", 60, 1, False) in rows
        # Alice zhdun cycle is propagated.
        assert (alice_id, "ops", 10, 1, True) in rows
    finally:
        close_db()
