from __future__ import annotations

import os
from datetime import date
from decimal import Decimal

import pytest
from alembic import command
from alembic.config import Config
from WorkAI.assess.runner import run_assess_bayesian_norms
from WorkAI.db import close_db, connection, init_db


@pytest.mark.integration
def test_assess_bayesian_norms_smoke_idempotent() -> None:
    dsn = os.getenv("WORKAI_DB__DSN", "").strip()
    if not dsn:
        pytest.skip("WORKAI_DB__DSN is not set")

    target_date = date(2099, 1, 1)
    spreadsheet_id = "assess-bayes-smoke"

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    init_db()
    try:
        with connection() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM daily_task_assessments WHERE task_date = %s", (target_date,))
            cur.execute("DELETE FROM dynamic_task_norms")
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
                ("bayes-alice",),
            )
            alice_id = int(cur.fetchone()[0])

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
                    (40001, spreadsheet_id, "Sheet1", 2, 2, "B2", "Alice", target_date, 1, "Code A"),
                    (40002, spreadsheet_id, "Sheet1", 2, 3, "C2", "Alice", target_date, 1, "Code B"),
                    (40003, spreadsheet_id, "Sheet1", 2, 4, "D2", "Alice", target_date, 1, "Meeting"),
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
                        40001,
                        target_date,
                        alice_id,
                        spreadsheet_id,
                        "Sheet1",
                        2,
                        2,
                        1,
                        target_date,
                        "Alice",
                        "bayes-alice",
                        "exact",
                        "Code A",
                        "Code A",
                        60,
                        "logged",
                        True,
                        False,
                        True,
                        False,
                        "coding",
                        "Code A",
                    ),
                    (
                        40002,
                        target_date,
                        alice_id,
                        spreadsheet_id,
                        "Sheet1",
                        2,
                        3,
                        1,
                        target_date,
                        "Alice",
                        "bayes-alice",
                        "exact",
                        "Code B",
                        "Code B",
                        90,
                        "logged",
                        True,
                        False,
                        True,
                        False,
                        "coding",
                        "Code B",
                    ),
                    (
                        40003,
                        target_date,
                        alice_id,
                        spreadsheet_id,
                        "Sheet1",
                        2,
                        4,
                        1,
                        target_date,
                        "Alice",
                        "bayes-alice",
                        "exact",
                        "Meeting",
                        "Meeting",
                        30,
                        "logged",
                        False,
                        True,
                        True,
                        False,
                        "meetings",
                        "Meeting",
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
                    norm_minutes,
                    delta_minutes,
                    quality_score,
                    smart_score,
                    assessed_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (normalized_task_id) DO UPDATE
                SET quality_score = EXCLUDED.quality_score,
                    smart_score = EXCLUDED.smart_score,
                    assessed_at = now()
                """,
                [
                    (task_map[40001], alice_id, target_date, None, None, "0.900", "0.900"),
                    (task_map[40002], alice_id, target_date, None, None, "0.800", "0.800"),
                    (task_map[40003], alice_id, target_date, None, None, "0.700", "0.500"),
                ],
            )
            conn.commit()

        first = run_assess_bayesian_norms(target_date, window_days=7)
        second = run_assess_bayesian_norms(target_date, window_days=7)

        assert first.categories_updated >= 2
        assert first.rows_recomputed == 3
        assert second.rows_recomputed == 3

        init_db()
        with connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT task_category, norm_minutes, sample_size, baseline_prior
                FROM dynamic_task_norms
                WHERE task_category IN ('coding', 'meetings')
                ORDER BY task_category
                """
            )
            norms = cur.fetchall()

            cur.execute(
                """
                SELECT tn.raw_task_id, dta.norm_minutes, dta.delta_minutes, dta.quality_score, dta.smart_score
                FROM daily_task_assessments AS dta
                JOIN tasks_normalized AS tn ON tn.id = dta.normalized_task_id
                WHERE dta.task_date = %s
                ORDER BY tn.raw_task_id
                """,
                (target_date,),
            )
            assessments = cur.fetchall()

            cur.execute("SELECT count(*), count(distinct task_category) FROM dynamic_task_norms")
            dedup = cur.fetchone()

        assert norms[0][0] == "coding"
        assert Decimal(str(norms[0][1])) == Decimal("62.50")
        assert int(norms[0][2]) == 2
        assert Decimal(str(norms[0][3])) == Decimal("60.00")

        assert norms[1][0] == "meetings"
        assert Decimal(str(norms[1][1])) == Decimal("30.00")
        assert int(norms[1][2]) == 1

        # coding norm round(62.50)=63
        assert int(assessments[0][1]) == 63
        assert int(assessments[0][2]) == -3
        assert int(assessments[1][1]) == 63
        assert int(assessments[1][2]) == 27

        # meetings norm round(30)=30
        assert int(assessments[2][1]) == 30
        assert int(assessments[2][2]) == 0

        # scoring columns remain intact
        assert Decimal(str(assessments[0][3])) == Decimal("0.900")
        assert Decimal(str(assessments[0][4])) == Decimal("0.900")

        assert dedup is not None
        assert int(dedup[0]) == int(dedup[1])
    finally:
        close_db()
