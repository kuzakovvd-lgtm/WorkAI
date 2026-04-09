import os

import pytest
from WorkAI.db import close_db, connection, init_db


@pytest.mark.integration
def test_db_connectivity() -> None:
    dsn = os.getenv("WORKAI_DB__DSN", "").strip()
    if not dsn:
        pytest.skip("WORKAI_DB__DSN is not set")

    init_db()
    try:
        with connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
            row = cur.fetchone()
        assert row is not None
        assert row[0] == 1
    finally:
        close_db()
