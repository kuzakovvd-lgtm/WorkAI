from __future__ import annotations

from WorkAI.api import queries


class _CursorStub:
    def __init__(
        self,
        *,
        fetchone_results: list[tuple[object, ...] | None] | None = None,
    ) -> None:
        self.fetchone_results = list(fetchone_results or [])
        self.executed: list[tuple[str, tuple[object, ...] | None]] = []

    def execute(self, sql: str, params: tuple[object, ...] | None = None) -> None:
        self.executed.append((sql, params))

    def fetchone(self) -> tuple[object, ...] | None:
        if not self.fetchone_results:
            return None
        return self.fetchone_results.pop(0)


def test_fetch_health_deep_returns_none_when_alembic_table_missing() -> None:
    cur = _CursorStub(fetchone_results=[(1,), (None,)])

    ok, revision = queries.fetch_health_deep(cur)  # type: ignore[arg-type]

    assert ok is True
    assert revision is None
    assert len(cur.executed) == 2


def test_fetch_health_deep_handles_empty_version_row() -> None:
    cur = _CursorStub(fetchone_results=[(1,), ("alembic_version",), None])

    ok, revision = queries.fetch_health_deep(cur)  # type: ignore[arg-type]

    assert ok is True
    assert revision is None
    assert len(cur.executed) == 3
    assert "SELECT version_num FROM alembic_version LIMIT 1" in cur.executed[2][0]


def test_fetch_health_deep_returns_revision_as_string() -> None:
    cur = _CursorStub(fetchone_results=[(1,), ("alembic_version",), (2026041301,)])

    ok, revision = queries.fetch_health_deep(cur)  # type: ignore[arg-type]

    assert ok is True
    assert revision == "2026041301"
