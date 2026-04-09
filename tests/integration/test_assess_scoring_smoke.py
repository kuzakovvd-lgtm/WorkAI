from __future__ import annotations

import os
from datetime import date
from decimal import Decimal

import pytest
from alembic import command
from alembic.config import Config
from WorkAI.assess.runner import run_assess_scoring
from WorkAI.db import close_db, connection, init_db


@pytest.mark.integration
def test_assess_scoring_smoke_idempotent() -> None:
    dsn = os.getenv("WORKAI_DB__DSN", "").strip()
    if not dsn:
        pytest.skip("WORKAI_DB__DSN is not set")

    target_date = date(2026, 4, 10)
    spreadsheet_id = "assess-scoring-smoke"

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    init_db()
    try:
        with connection() as conn, conn.cursor() as cur:
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
                ("assess-score-alice",),
            )
            employee_alice = int(cur.fetchone()[0])

            cur.execute(
                """
                INSERT INTO employees (employee_name_norm)
                VALUES (%s)
                ON CONFLICT (employee_name_norm) DO UPDATE
                SET employee_name_norm = EXCLUDED.employee_name_norm
                RETURNING employee_id
                """,
                ("assess-score-bob",),
            )
            employee_bob = int(cur.fetchone()[0])

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
                    (20001, spreadsheet_id, "Sheet1", 2, 2, "B2", "Alice", target_date, 1, "Task 1"),
                    (20002, spreadsheet_id, "Sheet1", 2, 3, "C2", "Alice", target_date, 1, "Task 2"),
                    (20003, spreadsheet_id, "Sheet1", 3, 2, "B3", "Bob", target_date, 1, "Task 3"),
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
                    time_start,
                    time_end,
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
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    null, null, %s, %s, %s, %s, %s, %s, null, null, %s, now(), now()
                )
                """,
                [
                    (
                        20001,
                        target_date,
                        employee_alice,
                        spreadsheet_id,
                        "Sheet1",
                        2,
                        2,
                        1,
                        target_date,
                        "Alice",
                        "assess-score-alice",
                        "exact",
                        "Task 1",
                        "Task 1",
                        60,
                        "logged",
                        True,
                        False,
                        True,
                        False,
                        "Task 1",
                    ),
                    (
                        20002,
                        target_date,
                        employee_alice,
                        spreadsheet_id,
                        "Sheet1",
                        2,
                        3,
                        1,
                        target_date,
                        "Alice",
                        "assess-score-alice",
                        "exact",
                        "Task 2",
                        "Task 2",
                        15,
                        "estimated",
                        False,
                        True,
                        True,
                        False,
                        "Task 2",
                    ),
                    (
                        20003,
                        target_date,
                        employee_bob,
                        spreadsheet_id,
                        "Sheet1",
                        3,
                        2,
                        1,
                        target_date,
                        "Bob",
                        "assess-score-bob",
                        "exact",
                        "Task 3",
                        "Task 3",
                        None,
                        "none",
                        False,
                        False,
                        False,
                        True,
                        "Task 3",
                    ),
                ],
            )
            conn.commit()

        first = run_assess_scoring(target_date)
        second = run_assess_scoring(target_date)

        assert first.tasks_scored == 3
        assert first.rows_upserted == 3
        assert first.employees_seen == 2
        assert second.rows_upserted == 3

        init_db()
        with connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT normalized_task_id, quality_score, smart_score
                FROM daily_task_assessments
                WHERE task_date = %s
                ORDER BY normalized_task_id
                """,
                (target_date,),
            )
            rows = cur.fetchall()

            cur.execute(
                "SELECT count(*), count(distinct normalized_task_id) FROM daily_task_assessments WHERE task_date = %s",
                (target_date,),
            )
            counts = cur.fetchone()

            cur.execute(
                """
                UPDATE tasks_normalized
                SET time_source = 'estimated', result_confirmed = true
                WHERE raw_task_id = 20003
                """
            )
            conn.commit()

        assert counts is not None
        assert int(counts[0]) == 3
        assert int(counts[1]) == 3

        assert Decimal(str(rows[0][1])) == Decimal("1.000")
        assert Decimal(str(rows[0][2])) == Decimal("1.000")

        assert Decimal(str(rows[1][1])) == Decimal("0.700")
        assert Decimal(str(rows[1][2])) == Decimal("0.300")

        assert Decimal(str(rows[2][1])) == Decimal("0.000")
        assert Decimal(str(rows[2][2])) == Decimal("0.300")

        run_assess_scoring(target_date)
        init_db()
        with connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT quality_score
                FROM daily_task_assessments
                WHERE task_date = %s AND normalized_task_id = %s
                """,
                (target_date, rows[2][0]),
            )
            updated = cur.fetchone()

        assert updated is not None
        assert Decimal(str(updated[0])) == Decimal("0.700")
    finally:
        close_db()
