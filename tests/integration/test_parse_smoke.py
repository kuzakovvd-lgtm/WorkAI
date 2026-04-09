from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from WorkAI.config import get_settings
from WorkAI.db import close_db, connection, init_db
from WorkAI.parse import run_parse


@pytest.mark.integration
def test_parse_smoke() -> None:
    dsn = os.getenv("WORKAI_DB__DSN", "").strip()
    if not dsn:
        pytest.skip("WORKAI_DB__DSN is not set")

    spreadsheet_id = "parse-smoke-sheet"

    os.environ["WORKAI_GSHEETS__SPREADSHEET_ID"] = spreadsheet_id
    os.environ["WORKAI_PARSE__ENABLED"] = "true"
    os.environ["WORKAI_PARSE__HEADER_ROW_IDX"] = "1"
    os.environ["WORKAI_PARSE__EMPLOYEE_COL_IDX"] = "1"
    os.environ["WORKAI_PARSE__DATE_FORMATS"] = "%Y-%m-%d,%d.%m.%Y"
    get_settings.cache_clear()

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    init_db()
    try:
        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM raw_tasks WHERE spreadsheet_id = %s", (spreadsheet_id,))
                cur.execute("DELETE FROM sheet_cells WHERE spreadsheet_id = %s", (spreadsheet_id,))
                cur.executemany(
                    """
                    INSERT INTO sheet_cells (
                        spreadsheet_id,
                        sheet_title,
                        row_idx,
                        col_idx,
                        a1,
                        value_text,
                        ingested_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, now())
                    """,
                    [
                        (spreadsheet_id, "Sheet1", 1, 1, "A1", "Employee"),
                        (spreadsheet_id, "Sheet1", 1, 2, "B1", "2026-04-08"),
                        (spreadsheet_id, "Sheet1", 2, 1, "A2", "Alice"),
                        (spreadsheet_id, "Sheet1", 2, 2, "B2", "Task A\nTask B"),
                    ],
                )
            conn.commit()

        run_parse()
        init_db()

        with connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                    SELECT count(*), min(employee_name_raw), min(work_date::text)
                    FROM raw_tasks
                    WHERE spreadsheet_id = %s
                    """,
                (spreadsheet_id,),
            )
            row = cur.fetchone()

        assert row is not None
        assert int(row[0]) == 2
        assert row[1] == "Alice"
        assert row[2] == "2026-04-08"
    finally:
        close_db()
