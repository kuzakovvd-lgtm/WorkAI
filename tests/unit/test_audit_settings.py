from __future__ import annotations

import pytest
from WorkAI.config import get_settings


def test_audit_openai_env_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKAI_AUDIT__ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL_ANALYST", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_MODEL_FORENSIC", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_MODEL_REPORTER", "gpt-4o")

    get_settings.cache_clear()
    settings = get_settings()

    assert settings.audit.enabled is True
    assert settings.audit.openai_api_key == "sk-test"
    assert settings.audit.model_reporter == "gpt-4o"
    assert settings.audit.failed_retry_attempts == 1


def test_audit_invalid_limits_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKAI_AUDIT__ENABLED", "true")
    monkeypatch.setenv("WORKAI_AUDIT__MAX_ITER", "0")

    get_settings.cache_clear()
    with pytest.raises(ValueError, match="WORKAI_AUDIT__MAX_ITER"):
        get_settings()


def test_audit_invalid_failed_retry_attempts_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKAI_AUDIT__ENABLED", "true")
    monkeypatch.setenv("WORKAI_AUDIT__FAILED_RETRY_ATTEMPTS", "3")

    get_settings.cache_clear()
    with pytest.raises(ValueError, match="WORKAI_AUDIT__FAILED_RETRY_ATTEMPTS"):
        get_settings()
