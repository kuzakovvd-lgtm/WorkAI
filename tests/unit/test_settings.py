import pytest
from WorkAI.config import get_settings


def test_gsheets_disabled_requires_no_google_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKAI_GSHEETS__ENABLED", "false")
    monkeypatch.delenv("WORKAI_GSHEETS__SPREADSHEET_ID", raising=False)
    monkeypatch.delenv("WORKAI_GSHEETS__RANGES", raising=False)
    monkeypatch.delenv("WORKAI_GSHEETS__SERVICE_ACCOUNT_FILE", raising=False)
    monkeypatch.delenv("WORKAI_GSHEETS__SERVICE_ACCOUNT_JSON_B64", raising=False)

    get_settings.cache_clear()
    settings = get_settings()

    assert settings.gsheets.enabled is False
    assert settings.gsheets.ranges == []


def test_nested_env_loading(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKAI_ENV", "staging")
    monkeypatch.setenv("WORKAI_LOG__LEVEL", "DEBUG")
    monkeypatch.setenv("WORKAI_LOG__JSON", "true")
    monkeypatch.setenv("WORKAI_DB__DSN", "postgresql://user:pass@host:5432/workai")
    monkeypatch.setenv("WORKAI_DB__MIN_SIZE", "2")
    monkeypatch.setenv("WORKAI_DB__MAX_SIZE", "7")
    monkeypatch.setenv("WORKAI_DB__TIMEOUT_SEC", "11")
    monkeypatch.setenv("WORKAI_DB__LOCK_TIMEOUT_MS", "3210")

    get_settings.cache_clear()
    settings = get_settings()

    assert settings.app.env == "staging"
    assert settings.log.level == "DEBUG"
    assert settings.log.json_output is True
    assert settings.db.dsn == "postgresql://user:pass@host:5432/workai"
    assert settings.db.min_size == 2
    assert settings.db.max_size == 7
    assert settings.db.timeout_sec == 11
    assert settings.db.lock_timeout_ms == 3210


def test_gsheets_enabled_without_required_fields_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKAI_GSHEETS__ENABLED", "true")
    monkeypatch.delenv("WORKAI_GSHEETS__SPREADSHEET_ID", raising=False)
    monkeypatch.delenv("WORKAI_GSHEETS__RANGES", raising=False)
    monkeypatch.delenv("WORKAI_GSHEETS__SERVICE_ACCOUNT_FILE", raising=False)
    monkeypatch.delenv("WORKAI_GSHEETS__SERVICE_ACCOUNT_JSON_B64", raising=False)

    get_settings.cache_clear()
    with pytest.raises(ValueError, match="WORKAI_GSHEETS__SPREADSHEET_ID"):
        get_settings()


def test_require_dsn_raises_without_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WORKAI_DB__DSN", raising=False)

    get_settings.cache_clear()
    settings = get_settings()

    with pytest.raises(ValueError, match="WORKAI_DB__DSN"):
        settings.db.require_dsn()


def test_parse_disabled_requires_no_parse_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKAI_PARSE__ENABLED", "false")
    monkeypatch.delenv("WORKAI_PARSE__HEADER_ROW_IDX", raising=False)
    monkeypatch.delenv("WORKAI_PARSE__EMPLOYEE_COL_IDX", raising=False)
    monkeypatch.delenv("WORKAI_PARSE__MAX_CELLS_PER_SHEET", raising=False)

    get_settings.cache_clear()
    settings = get_settings()
    assert settings.parse.enabled is False


def test_parse_enabled_invalid_values_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKAI_PARSE__ENABLED", "true")
    monkeypatch.setenv("WORKAI_PARSE__HEADER_ROW_IDX", "0")
    monkeypatch.setenv("WORKAI_PARSE__EMPLOYEE_COL_IDX", "1")
    monkeypatch.setenv("WORKAI_PARSE__MAX_CELLS_PER_SHEET", "100")

    get_settings.cache_clear()
    with pytest.raises(ValueError, match="WORKAI_PARSE__HEADER_ROW_IDX"):
        get_settings()
