from __future__ import annotations

import pytest
from WorkAI.common import ConfigError
from WorkAI.config import Settings
from WorkAI.parse import runner


def _settings(*, parse_enabled: bool, spreadsheet_id: str | None) -> Settings:
    return Settings.model_validate(
        {
            "db": {"dsn": "postgresql://u:p@localhost:5432/workai"},
            "parse": {"enabled": parse_enabled, "max_cells_per_sheet": 10},
            "gsheets": {"spreadsheet_id": spreadsheet_id},
        }
    )


def test_chunked_splits_and_validates_size() -> None:
    assert list(runner._chunked([1, 2, 3, 4, 5], 2)) == [[1, 2], [3, 4], [5]]
    with pytest.raises(ValueError, match="positive"):
        list(runner._chunked([1], 0))


def test_delete_refresh_scope_calls_deletes_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def _delete_tasks(*args: object, **kwargs: object) -> None:
        calls.append("tasks")

    def _delete_raw(*args: object, **kwargs: object) -> None:
        calls.append("raw")

    def _delete_null(*args: object, **kwargs: object) -> None:
        calls.append("null")

    monkeypatch.setattr(runner, "delete_tasks_normalized_for_sheet_dates", _delete_tasks)
    monkeypatch.setattr(runner, "delete_raw_tasks_for_sheet_dates", _delete_raw)
    monkeypatch.setattr(runner, "delete_raw_tasks_for_sheet_null_date", _delete_null)

    runner._delete_refresh_scope(
        object(),  # type: ignore[arg-type]
        spreadsheet_id="sheet-1",
        sheet_title="Team",
        refresh_dates=[],
    )

    assert calls == ["tasks", "raw", "null"]


def test_run_parse_returns_early_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    init_called = False
    close_called = False

    def _init_db(_: object) -> None:
        nonlocal init_called
        init_called = True

    def _close_db() -> None:
        nonlocal close_called
        close_called = True

    monkeypatch.setattr(runner, "init_db", _init_db)
    monkeypatch.setattr(runner, "close_db", _close_db)
    monkeypatch.setattr(runner, "configure_logging", lambda *_: None)

    runner.run_parse(_settings(parse_enabled=False, spreadsheet_id=None))

    assert init_called is False
    assert close_called is False


def test_run_parse_requires_spreadsheet_id_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "configure_logging", lambda *_: None)

    with pytest.raises(ConfigError, match="WORKAI_GSHEETS__SPREADSHEET_ID"):
        runner.run_parse(_settings(parse_enabled=True, spreadsheet_id="  "))
