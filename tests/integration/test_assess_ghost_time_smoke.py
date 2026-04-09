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
                cur.execute("DELETE FROM raw_tasks WHERE spreadsheet_id = %s", (spreadsheet_id,))
                cur.execute(
                    """
                    INSERT INTO employees (employee_name_norm)
                    VALUES (%s)
                    ON CONFLICT (employee_name_norm) DO UPDATE
                    SET employee_name_norm = EXCLUDED.employee_name_norm
                    RETURNING employee_id
                    """,
                    ("assess-smoke-alice",),
                )
                employee_id_alice = int(cur.fetchone()[0])
                cur.execute(
                    """
                    INSERT INTO employees (employee_name_norm)
                    VALUES (%s)
                    ON CONFLICT (employee_name_norm) DO UPDATE
                    SET employee_name_norm = EXCLUDED.employee_name_norm
                    RETURNING employee_id
                    """,
                    ("assess-smoke-bob",),
                )
                employee_id_bob = int(cur.fetchone()[0])
                cur.execute(
                    """
                    INSERT INTO employees (employee_name_norm)
                    VALUES (%s)
                    ON CONFLICT (employee_name_norm) DO UPDATE
                    SET employee_name_norm = EXCLUDED.employee_name_norm
                    RETURNING employee_id
                    """,
                    ("assess-smoke-carol",),
                )
                employee_id_carol = int(cur.fetchone()[0])
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
                        (10001, spreadsheet_id, "Sheet1", 2, 2, "B2", "Alice", target_date, 1, "Task A"),
                        (
                            10002,
                            spreadsheet_id,
                            "Sheet1",
                            2,
                            2,
                            "B2",
                            "Alice",
                            target_date,
                            2,
                            "Task B (no duration)",
                        ),
                        (10003, spreadsheet_id, "Sheet1", 3, 2, "B3", "Bob", target_date, 1, "Task C"),
                        (
                            10004,
                            spreadsheet_id,
                            "Sheet1",
                            4,
                            2,
                            "B4",
                            "Alice duplicate-name id",
                            target_date,
                            1,
                            "Task D",
                        ),
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
                        null, null, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now()
                    )
                    """,
                    [
                        (
                            10001,
                            target_date,
                            employee_id_alice,
                            spreadsheet_id,
                            "Sheet1",
                            2,
                            2,
                            1,
                            target_date,
                            "Alice",
                            "assess-smoke-alice",
                            "exact",
                            "Task A",
                            "Task A",
                            120,
                            "parsed",
                            False,
                            False,
                            True,
                            False,
                            "coding",
                            "coding",
                            "Task A",
                        ),
                        (
                            10002,
                            target_date,
                            employee_id_alice,
                            spreadsheet_id,
                            "Sheet1",
                            2,
                            2,
                            2,
                            target_date,
                            "Alice",
                            "assess-smoke-alice",
                            "exact",
                            "Task B (no duration)",
                            "Task B (no duration)",
                            None,
                            "none",
                            False,
                            False,
                            False,
                            False,
                            None,
                            None,
                            "Task B (no duration)",
                        ),
                        (
                            10003,
                            target_date,
                            employee_id_bob,
                            spreadsheet_id,
                            "Sheet1",
                            3,
                            2,
                            1,
                            target_date,
                            "Bob",
                            "assess-smoke-bob",
                            "exact",
                            "Task C",
                            "Task C",
                            500,
                            "parsed",
                            True,
                            False,
                            True,
                            False,
                            "meeting",
                            "meeting",
                            "Task C",
                        ),
                        (
                            10004,
                            target_date,
                            employee_id_carol,
                            spreadsheet_id,
                            "Sheet1",
                            4,
                            2,
                            1,
                            target_date,
                            "Carol",
                            "assess-smoke-carol",
                            "exact",
                            "Task D",
                            "Task D",
                            60,
                            "parsed",
                            True,
                            False,
                            True,
                            False,
                            "ops",
                            "ops",
                            "Task D",
                        ),
                    ],
                )
            conn.commit()

        result_first = run_assess_ghost_time(target_date)
        result_second = run_assess_ghost_time(target_date)

        assert result_first.employees_processed == 3
        assert result_first.rows_upserted == 3
        assert result_second.rows_upserted == 3

        init_db()
        with connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    g.employee_id,
                    g.logged_minutes,
                    g.ghost_minutes,
                    g.index_of_trust_base
                FROM employee_daily_ghost_time AS g
                WHERE g.task_date = %s
                ORDER BY g.employee_id
                """,
                (target_date,),
            )
            rows = cur.fetchall()

            cur.execute(
                "SELECT count(*) FROM employee_daily_ghost_time WHERE task_date = %s",
                (target_date,),
            )
            total = cur.fetchone()

        assert total is not None
        assert int(total[0]) == 3

        by_employee_id = {int(row[0]): row for row in rows}
        assert employee_id_alice in by_employee_id
        assert employee_id_bob in by_employee_id
        assert employee_id_carol in by_employee_id

        alice_row = by_employee_id[employee_id_alice]
        assert int(alice_row[1]) == 120
        assert int(alice_row[2]) == 360
        assert Decimal(str(alice_row[3])) == Decimal("0.500")

        bob_row = by_employee_id[employee_id_bob]
        assert int(bob_row[1]) == 500
        assert int(bob_row[2]) == 0
        assert Decimal(str(bob_row[3])) == Decimal("1.000")

        # Regression guard: assess must use contract employee_id values, not recomputed ids.
        carol_row = by_employee_id[employee_id_carol]
        assert int(carol_row[1]) == 60
        assert int(carol_row[2]) == 420
        assert Decimal(str(carol_row[3])) == Decimal("1.000")
    finally:
        close_db()
