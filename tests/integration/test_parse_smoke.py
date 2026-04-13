from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from WorkAI.config import get_settings
from WorkAI.db import close_db, connection, init_db
from WorkAI.normalize import run_normalize
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


@pytest.mark.integration
def test_parse_refresh_with_existing_normalized_fk_links() -> None:
    dsn = os.getenv("WORKAI_DB__DSN", "").strip()
    if not dsn:
        pytest.skip("WORKAI_DB__DSN is not set")

    spreadsheet_id = "parse-fk-refresh-sheet"

    os.environ["WORKAI_GSHEETS__SPREADSHEET_ID"] = spreadsheet_id
    os.environ["WORKAI_PARSE__ENABLED"] = "true"
    os.environ["WORKAI_PARSE__HEADER_ROW_IDX"] = "1"
    os.environ["WORKAI_PARSE__EMPLOYEE_COL_IDX"] = "1"
    os.environ["WORKAI_PARSE__DATE_FORMATS"] = "%Y-%m-%d,%d.%m.%Y"
    os.environ["WORKAI_NORMALIZE__ENABLED"] = "true"
    os.environ["WORKAI_NORMALIZE__FUZZY_ENABLED"] = "false"
    os.environ["WORKAI_NORMALIZE__TIME_PARSE_ENABLED"] = "false"
    get_settings.cache_clear()

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    init_db()
    try:
        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM tasks_normalized WHERE spreadsheet_id = %s", (spreadsheet_id,))
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
                        (spreadsheet_id, "Sheet1", 2, 2, "B2", "Task A"),
                    ],
                )
            conn.commit()

        run_parse()
        run_normalize()
        init_db()

        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE sheet_cells
                    SET value_text = %s, ingested_at = now()
                    WHERE spreadsheet_id = %s AND sheet_title = %s AND a1 = %s
                    """,
                    ("Task B", spreadsheet_id, "Sheet1", "B2"),
                )
            conn.commit()

        run_parse()
        run_parse()
        init_db()

        with connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*), min(line_text), max(line_text)
                FROM raw_tasks
                WHERE spreadsheet_id = %s
                """,
                (spreadsheet_id,),
            )
            raw_summary = cur.fetchone()

            cur.execute(
                """
                SELECT count(*)
                FROM tasks_normalized
                WHERE spreadsheet_id = %s
                """,
                (spreadsheet_id,),
            )
            normalized_count = cur.fetchone()

        assert raw_summary is not None
        assert int(raw_summary[0]) == 1
        assert raw_summary[1] == "Task B"
        assert raw_summary[2] == "Task B"
        assert normalized_count is not None
        assert int(normalized_count[0]) == 0
    finally:
        close_db()
