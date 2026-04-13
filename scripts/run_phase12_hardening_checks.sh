#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-/opt/workai/.venv/bin/python}"
RUFF_BIN="${RUFF_BIN:-/opt/workai/.venv/bin/ruff}"
MYPY_BIN="${MYPY_BIN:-/opt/workai/.venv/bin/mypy}"
PYTEST_BIN="${PYTEST_BIN:-/opt/workai/.venv/bin/pytest}"
DB_ENV_FILE="${DB_ENV_FILE:-/etc/workai/secrets/db.test.env}"
PYTEST_MARK_EXPR="${PYTEST_MARK_EXPR:-not integration_online}"

# Prefer integration DB env when available to avoid skipped integration tests
# and get realistic coverage in phase12 checks.
if [[ -z "${WORKAI_DB__DSN:-}" && -f "${DB_ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${DB_ENV_FILE}"
  set +a
  echo "[phase12] loaded DB env from ${DB_ENV_FILE}"
fi

echo "[phase12] verify python version (3.12.x)"
"${PYTHON_BIN}" - <<PY
import sys

if sys.version_info[:2] != (3, 12):
    raise SystemExit(
        f"Python 3.12.x is required for hardening checks, got {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
print(f"python={sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
PY

echo "[phase12] ruff standard"
"${RUFF_BIN}" check .

echo "[phase12] ruff hardened profile"
"${RUFF_BIN}" check . \
  --select TRY,BLE,S,DTZ,PERF \
  --ignore BLE001,S101,S105,S108,S310,S311,S324,S603,S608,TRY003,TRY300,TRY301,TRY004,DTZ007,DTZ011,PERF401

echo "[phase12] mypy strict"
"${MYPY_BIN}" WorkAI

echo "[phase12] pytest + coverage (mark: ${PYTEST_MARK_EXPR})"
"${PYTEST_BIN}" -q -m "${PYTEST_MARK_EXPR}" --cov=WorkAI --cov-report=term --cov-report=xml

echo "[phase12] done"
