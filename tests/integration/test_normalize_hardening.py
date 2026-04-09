from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from WorkAI.config import get_settings
from WorkAI.db import close_db, connection, get_pool, init_db
from WorkAI.normalize import run_normalize


def _setup_normalize_env(spreadsheet_id: str) -> None:
    os.environ["WORKAI_GSHEETS__SPREADSHEET_ID"] = spreadsheet_id
    os.environ["WORKAI_NORMALIZE__ENABLED"] = "true"
    os.environ["WORKAI_NORMALIZE__FUZZY_ENABLED"] = "false"
    os.environ["WORKAI_NORMALIZE__TIME_PARSE_ENABLED"] = "true"
    os.environ["WORKAI_NORMALIZE__MAX_ERRORS_PER_SHEET"] = "50"
    get_settings.cache_clear()


def _seed_raw_task(spreadsheet_id: str, line_text: str) -> None:
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tasks_normalized WHERE spreadsheet_id = %s", (spreadsheet_id,))
            cur.execute("DELETE FROM raw_tasks WHERE spreadsheet_id = %s", (spreadsheet_id,))
            cur.execute("DELETE FROM pipeline_errors WHERE source_ref LIKE %s", (f"{spreadsheet_id}:%",))
            cur.execute(
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
                (spreadsheet_id, "Sheet1", 2, 2, "B2", "Alice", "2026-04-08", 1, line_text),
            )
        conn.commit()


@pytest.mark.integration
def test_normalize_writes_pipeline_error_on_record_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    dsn = os.getenv("WORKAI_DB__DSN", "").strip()
    if not dsn:
        pytest.skip("WORKAI_DB__DSN is not set")

    spreadsheet_id = "normalize-hardening-dlq"
    _setup_normalize_env(spreadsheet_id)

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    init_db()
    try:
        _seed_raw_task(spreadsheet_id, "10:00-11:00 task")

        def _broken_extract_time_info(_: str) -> tuple[None, str]:
            raise ValueError("forced-normalize-error")

        monkeypatch.setattr("WorkAI.normalize.runner.extract_time_info", _broken_extract_time_info)
        run_normalize()
        init_db()

        with connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*), min(error_type), min(error_message)
                FROM pipeline_errors
                WHERE phase = 'normalize'
                  AND source_ref LIKE %s
                """,
                (f"{spreadsheet_id}:%",),
            )
            row = cur.fetchone()

        assert row is not None
        assert int(row[0]) >= 1
        assert row[1] == "ValueError"
        assert "forced-normalize-error" in str(row[2])
    finally:
        close_db()


@pytest.mark.integration
def test_normalize_skips_sheet_date_when_lock_is_held() -> None:
    dsn = os.getenv("WORKAI_DB__DSN", "").strip()
    if not dsn:
        pytest.skip("WORKAI_DB__DSN is not set")

    spreadsheet_id = "normalize-hardening-lock"
    _setup_normalize_env(spreadsheet_id)

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    init_db()
    lock_key = f"normalize|{spreadsheet_id}:Sheet1|2026-04-08"
    try:
        _seed_raw_task(spreadsheet_id, "10:00-11:30 Task under lock")

        with get_pool().connection() as lock_conn:
            with lock_conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_lock(hashtextextended(%s, 0))", (lock_key,))

            run_normalize()
            init_db()

            with connection() as conn, conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM tasks_normalized WHERE spreadsheet_id = %s",
                    (spreadsheet_id,),
                )
                row = cur.fetchone()
            assert row is not None
            assert int(row[0]) == 0

            with lock_conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_unlock(hashtextextended(%s, 0))", (lock_key,))
            lock_conn.commit()
    finally:
        close_db()
