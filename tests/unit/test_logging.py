import pytest
from WorkAI.common import configure_logging, get_logger
from WorkAI.config import get_settings


def test_configure_logging_and_emit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKAI_ENV", "dev")
    monkeypatch.setenv("WORKAI_LOG__LEVEL", "INFO")
    monkeypatch.setenv("WORKAI_LOG__JSON", "false")

    get_settings.cache_clear()
    settings = get_settings()

    assert configure_logging(settings) is None

    logger = get_logger("tests.logging")
    logger.info("phase1 logging smoke", extra_key="ok")
