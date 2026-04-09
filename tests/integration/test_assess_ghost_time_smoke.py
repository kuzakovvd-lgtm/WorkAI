from __future__ import annotations

import os
from datetime import date
from decimal import Decimal

import pytest
from alembic import command
from alembic.config import Config
from WorkAI.assess import run_assess_ghost_time
from WorkAI.db import close_db, connection, init_db


@pytest.mark.integration
def test_assess_ghost_time_smoke() -> None:
    dsn = os.getenv("WORKAI_DB__DSN", "").strip()
    if not dsn:
        pytest.skip("WORKAI_DB__DSN is not set")

    target_date = date(2026, 4, 7)
    spreadsheet_id = "assess-ghost-smoke"

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    init_db()
    try:
        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM employee_daily_ghost_time WHERE task_date = %s", (target_date,))
                cur.execute("DELETE FROM tasks_normalized WHERE spreadsheet_id = %s", (spreadsheet_id,))
                cur.executemany(
                    """
                    INSERT INTO tasks_normalized (
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
                        category_code,
                        normalized_at,
                        source_cell_ingested_at
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        null, null, %s, null, now(), now()
                    )
                    """,
                    [
                        (
                            spreadsheet_id,
                            "Sheet1",
                            2,
                            2,
                            1,
                            target_date,
                            "Alice",
                            "Alice",
                            "exact",
                            "Task A",
                            "Task A",
                            120,
                        ),
                        (
                            spreadsheet_id,
                            "Sheet1",
                            2,
                            2,
                            2,
                            target_date,
                            "Alice",
                            "Alice",
                            "exact",
                            "Task B (no duration)",
                            "Task B (no duration)",
                            None,
                        ),
                        (
                            spreadsheet_id,
                            "Sheet1",
                            3,
                            2,
                            1,
                            target_date,
                            "Bob",
                            "Bob",
                            "exact",
                            "Task C",
                            "Task C",
                            500,
                        ),
                    ],
                )
            conn.commit()

        result_first = run_assess_ghost_time(target_date)
        result_second = run_assess_ghost_time(target_date)

        assert result_first.employees_processed == 2
        assert result_first.rows_upserted == 2
        assert result_second.rows_upserted == 2

        init_db()
        with connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    e.employee_name_norm,
                    g.logged_minutes,
                    g.ghost_minutes,
                    g.index_of_trust_base
                FROM employee_daily_ghost_time AS g
                JOIN (
                    SELECT DISTINCT
                        employee_name_norm,
                        (mod(abs(hashtextextended(employee_name_norm, 0)), 2147483647) + 1)::int AS employee_id
                    FROM tasks_normalized
                    WHERE spreadsheet_id = %s
                      AND work_date = %s
                ) AS e
                  ON e.employee_id = g.employee_id
                WHERE g.task_date = %s
                ORDER BY e.employee_name_norm
                """,
                (spreadsheet_id, target_date, target_date),
            )
            rows = cur.fetchall()

            cur.execute(
                "SELECT count(*) FROM employee_daily_ghost_time WHERE task_date = %s",
                (target_date,),
            )
            total = cur.fetchone()

        assert total is not None
        assert int(total[0]) == 2

        assert rows[0][0] == "Alice"
        assert int(rows[0][1]) == 120
        assert int(rows[0][2]) == 360
        assert Decimal(str(rows[0][3])) == Decimal("0.500")

        assert rows[1][0] == "Bob"
        assert int(rows[1][1]) == 500
        assert int(rows[1][2]) == 0
        assert Decimal(str(rows[1][3])) == Decimal("1.000")
    finally:
        close_db()
