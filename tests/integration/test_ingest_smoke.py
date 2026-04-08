import os

import pytest
from alembic import command
from alembic.config import Config
from WorkAI.db import close_db, connection
from WorkAI.ingest.runner import run_ingest


def test_ingest_smoke() -> None:
    has_dsn = bool(os.getenv("WORKAI_DB__DSN", "").strip())
    has_spreadsheet = bool(os.getenv("WORKAI_GSHEETS__SPREADSHEET_ID", "").strip())
    has_sa_file = bool(os.getenv("WORKAI_GSHEETS__SERVICE_ACCOUNT_FILE", "").strip())
    has_sa_b64 = bool(os.getenv("WORKAI_GSHEETS__SERVICE_ACCOUNT_JSON_B64", "").strip())

    if not has_dsn or not has_spreadsheet or not (has_sa_file or has_sa_b64):
        pytest.skip("Google Sheets ingest integration env is not configured")

    os.environ["WORKAI_GSHEETS__ENABLED"] = "true"

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    try:
        run_ingest()
        with connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM sheet_cells WHERE spreadsheet_id = %s",
                (os.environ["WORKAI_GSHEETS__SPREADSHEET_ID"],),
            )
            row = cur.fetchone()
        assert row is not None
        assert int(row[0]) >= 0
    finally:
        close_db()
