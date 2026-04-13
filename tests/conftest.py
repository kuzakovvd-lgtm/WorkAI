from __future__ import annotations

import os
from collections.abc import Iterable

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--require-integration-env",
        action="store_true",
        default=False,
        help="Fail test run if integration tests are selected but required DB env is missing.",
    )
    parser.addoption(
        "--require-integration-online-env",
        action="store_true",
        default=False,
        help="Fail test run if integration_online tests are selected but Google env is missing.",
    )


def _has_marker(items: Iterable[pytest.Item], marker_name: str) -> bool:
    return any(item.get_closest_marker(marker_name) is not None for item in items)


def _validate_required_env(var_names: list[str], context: str) -> None:
    missing = [name for name in var_names if not os.getenv(name, "").strip()]
    if missing:
        missing_values = ", ".join(missing)
        raise pytest.UsageError(f"{context}: missing required env vars: {missing_values}")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    require_integration_env = bool(config.getoption("--require-integration-env"))
    require_integration_online_env = bool(config.getoption("--require-integration-online-env"))

    has_integration = _has_marker(items, "integration")
    has_integration_online = _has_marker(items, "integration_online")

    if require_integration_env and (has_integration or has_integration_online):
        _validate_required_env(["WORKAI_DB__DSN"], "integration preflight failed")

    if require_integration_online_env and has_integration_online:
        _validate_required_env(
            [
                "WORKAI_DB__DSN",
                "WORKAI_GSHEETS__SPREADSHEET_ID",
                "WORKAI_GSHEETS__RANGES",
            ],
            "integration_online preflight failed",
        )
        if not (
            os.getenv("WORKAI_GSHEETS__SERVICE_ACCOUNT_FILE", "").strip()
            or os.getenv("WORKAI_GSHEETS__SERVICE_ACCOUNT_JSON_B64", "").strip()
        ):
            raise pytest.UsageError(
                "integration_online preflight failed: set one of "
                "WORKAI_GSHEETS__SERVICE_ACCOUNT_FILE or "
                "WORKAI_GSHEETS__SERVICE_ACCOUNT_JSON_B64"
            )
