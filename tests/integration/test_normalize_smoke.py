from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from WorkAI.config import get_settings
from WorkAI.db import close_db, connection, init_db
from WorkAI.normalize import run_normalize


@pytest.mark.integration
def test_normalize_smoke() -> None:
    dsn = os.getenv("WORKAI_DB__DSN", "").strip()
    if not dsn:
        pytest.skip("WORKAI_DB__DSN is not set")

    spreadsheet_id = "normalize-smoke-sheet"

    os.environ["WORKAI_GSHEETS__SPREADSHEET_ID"] = spreadsheet_id
    os.environ["WORKAI_NORMALIZE__ENABLED"] = "true"
    os.environ["WORKAI_NORMALIZE__FUZZY_ENABLED"] = "false"
    os.environ["WORKAI_NORMALIZE__TIME_PARSE_ENABLED"] = "true"
    get_settings.cache_clear()

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    init_db()
    try:
        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM tasks_normalized WHERE spreadsheet_id = %s", (spreadsheet_id,))
                cur.execute("DELETE FROM raw_tasks WHERE spreadsheet_id = %s", (spreadsheet_id,))
                cur.executemany(
                    """
                    INSERT INTO raw_tasks (
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
                    VALUES (%s, %s, %s, %s, %s, now(), %s, %s, %s, %s, now())
                    """,
                    [
                        (
                            spreadsheet_id,
                            "Sheet1",
                            2,
                            2,
                            "B2",
                            " Alice ",
                            "2026-04-08",
                            1,
                            "10:00-11:30 Sync meeting",
                        ),
                        (
                            spreadsheet_id,
                            "Sheet1",
                            2,
                            2,
                            "B2",
                            "Alice",
                            "2026-04-08",
                            2,
                            "1h30m Implement feature",
                        ),
                    ],
                )
            conn.commit()

        run_normalize()
        run_normalize()
        init_db()

        with connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    count(*),
                    min(employee_name_norm),
                    max(duration_minutes),
                    min(employee_id),
                    max(raw_task_id),
                    bool_and(time_source IN ('none', 'logged')),
                    bool_and(result_confirmed = true)
                FROM tasks_normalized
                WHERE spreadsheet_id = %s
                """,
                (spreadsheet_id,),
            )
            summary = cur.fetchone()

        assert summary is not None
        assert int(summary[0]) == 2
        assert summary[1] == "Alice"
        assert int(summary[2]) == 90
        assert int(summary[3]) > 0
        assert int(summary[4]) > 0
        assert bool(summary[5]) is True
        assert bool(summary[6]) is True
    finally:
        close_db()
