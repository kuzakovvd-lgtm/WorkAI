from __future__ import annotations

from contextlib import contextmanager

import pytest
from WorkAI.common import ConfigError, DatabaseError
from WorkAI.config import Settings
from WorkAI.db import pool


class _FakePool:
    def __init__(self, *, name: str = "workai", fail_open: bool = False, **kwargs: object) -> None:
        self.name = name
        self.fail_open = fail_open
        self.kwargs = kwargs
        self.closed = False
        self.open_calls: list[tuple[bool, float]] = []

    def open(self, *, wait: bool, timeout: float) -> None:
        self.open_calls.append((wait, timeout))
        if self.fail_open:
            raise RuntimeError("open failed")

    def close(self) -> None:
        self.closed = True

    @contextmanager
    def connection(self) -> object:
        yield object()


class _CursorStub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def __enter__(self) -> _CursorStub:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False

    def execute(self, sql: str, params: tuple[object, ...]) -> None:
        self.calls.append((sql, params))


class _ConnectionStub:
    def __init__(self) -> None:
        self._cur = _CursorStub()

    def cursor(self) -> _CursorStub:
        return self._cur


def _settings(*, dsn: str | None, env: str = "dev", exit_on_pool_failure: bool = False) -> Settings:
    return Settings.model_validate(
        {
            "env": env,
            "db": {
                "dsn": dsn,
                "min_size": 1,
                "max_size": 2,
                "timeout_sec": 3.0,
                "connect_timeout_sec": 1.0,
                "exit_on_pool_failure": exit_on_pool_failure,
            },
        }
    )


@pytest.fixture(autouse=True)
def _reset_pool() -> None:
    pool._POOL = None
    yield
    pool._POOL = None


def test_normalize_conninfo_rewrites_psycopg_scheme() -> None:
    assert pool._normalize_conninfo("postgresql+psycopg://u:p@h:5432/db") == "postgresql://u:p@h:5432/db"
    assert pool._normalize_conninfo("postgresql://u:p@h:5432/db") == "postgresql://u:p@h:5432/db"


def test_reconnect_failed_callback_exits_in_prod() -> None:
    settings = _settings(dsn="postgresql://u:p@h:5432/db", env="prod", exit_on_pool_failure=True)
    callback = pool._build_reconnect_failed_callback(settings)

    with pytest.raises(SystemExit, match="2"):
        callback(_FakePool(name="workai"))  # type: ignore[arg-type]


def test_init_db_success(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[_FakePool] = []

    def _pool_factory(*args: object, **kwargs: object) -> _FakePool:
        fake = _FakePool(**kwargs)
        created.append(fake)
        return fake

    monkeypatch.setattr(pool, "ConnectionPool", _pool_factory)

    settings = _settings(dsn="postgresql+psycopg://u:p@h:5432/db")
    pool.init_db(settings)

    assert len(created) == 1
    assert created[0].open_calls == [(True, 3.0)]
    assert created[0].kwargs["conninfo"] == "postgresql://u:p@h:5432/db"
    assert pool.get_pool() is created[0]  # type: ignore[comparison-overlap]


def test_init_db_raises_config_error_for_missing_dsn() -> None:
    settings = _settings(dsn="   ")
    with pytest.raises(ConfigError):
        pool.init_db(settings)


def test_init_db_raises_database_error_and_closes_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[_FakePool] = []

    def _pool_factory(*args: object, **kwargs: object) -> _FakePool:
        fake = _FakePool(fail_open=True, **kwargs)
        created.append(fake)
        return fake

    monkeypatch.setattr(pool, "ConnectionPool", _pool_factory)
    settings = _settings(dsn="postgresql://u:p@h:5432/db")

    with pytest.raises(DatabaseError):
        pool.init_db(settings)

    assert len(created) == 1
    assert created[0].closed is True


def test_get_pool_raises_when_uninitialized() -> None:
    with pytest.raises(DatabaseError):
        pool.get_pool()


def test_apply_lock_timeout_validation_and_sql() -> None:
    conn = _ConnectionStub()

    pool.apply_lock_timeout(conn, 2500)  # type: ignore[arg-type]
    assert conn._cur.calls == [("SET lock_timeout = %s", ("2500ms",))]

    with pytest.raises(ValueError, match="positive"):
        pool.apply_lock_timeout(conn, 0)  # type: ignore[arg-type]
