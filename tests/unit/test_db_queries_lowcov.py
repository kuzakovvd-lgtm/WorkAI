from __future__ import annotations

import hashlib
from contextlib import contextmanager
from datetime import date

import pytest
from WorkAI.db import queries


class _CursorStub:
    def __init__(self) -> None:
        self.executed: list[tuple[str, object]] = []
        self.fetchone_result: object = None
        self.fetchall_result: list[object] = []

    def __enter__(self) -> _CursorStub:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False

    def execute(self, sql: str, params: object = None) -> None:
        self.executed.append((sql, params))

    def fetchone(self) -> object:
        return self.fetchone_result

    def fetchall(self) -> list[object]:
        return self.fetchall_result


class _ConnectionStub:
    def __init__(self, cursor: _CursorStub) -> None:
        self._cursor = cursor
        self.commits = 0

    def __enter__(self) -> _ConnectionStub:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False

    def cursor(self) -> _CursorStub:
        return self._cursor

    def commit(self) -> None:
        self.commits += 1


def _patch_connection(monkeypatch: pytest.MonkeyPatch, conn: _ConnectionStub) -> None:
    @contextmanager
    def _connection() -> _ConnectionStub:
        yield conn

    monkeypatch.setattr(queries, "connection", _connection)


def test_execute_commits_and_runs_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    cur = _CursorStub()
    conn = _ConnectionStub(cur)
    _patch_connection(monkeypatch, conn)

    queries.execute("DELETE FROM t WHERE id = %s", (7,))

    assert conn.commits == 1
    assert cur.executed == [("DELETE FROM t WHERE id = %s", (7,))]


def test_fetch_one_none_and_fetch_all_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    cur = _CursorStub()
    conn = _ConnectionStub(cur)
    _patch_connection(monkeypatch, conn)

    cur.fetchone_result = None
    assert queries.fetch_one("SELECT 1") is None

    cur.fetchall_result = [[1, "a"], [2, "b"]]
    assert queries.fetch_all("SELECT * FROM t") == [(1, "a"), (2, "b")]


def test_insert_pipeline_error_trims_and_hashes(monkeypatch: pytest.MonkeyPatch) -> None:
    cur = _CursorStub()
    conn = _ConnectionStub(cur)
    _patch_connection(monkeypatch, conn)

    long_message = "E" * 5000
    long_payload = "P" * 5000
    record = queries.PipelineErrorRecord(
        phase="parse",
        run_id="run-1",
        sheet_id="sheet-1",
        work_date=date(2026, 4, 13),
        source_ref="sheet:Team",
        error_type="ValueError",
        error_message=long_message,
        payload_excerpt=long_payload,
    )

    queries.insert_pipeline_error(record)

    assert conn.commits == 1
    assert len(cur.executed) == 1

    _, params = cur.executed[0]
    assert isinstance(params, tuple)
    trimmed_message = long_message[:4096]
    trimmed_payload = long_payload[:4096]
    expected_hash = hashlib.sha256(
        f"parse|sheet:Team|ValueError|{trimmed_message}".encode()
    ).hexdigest()

    assert params[6] == trimmed_message
    assert params[7] == trimmed_payload
    assert params[8] == expected_hash


def test_make_payload_excerpt_type_error_fallback() -> None:
    payload = {"unsafe": object()}
    excerpt = queries.make_payload_excerpt(payload)

    assert excerpt is not None
    assert '"repr"' in excerpt
