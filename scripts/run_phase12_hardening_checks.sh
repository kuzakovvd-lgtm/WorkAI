#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-/tmp/workai-py312/bin/python}"
RUFF_BIN="${RUFF_BIN:-/tmp/workai-py312/bin/ruff}"
MYPY_BIN="${MYPY_BIN:-/tmp/workai-py312/bin/mypy}"
PYTEST_BIN="${PYTEST_BIN:-/tmp/workai-py312/bin/pytest}"

echo "[phase12] verify python version (3.12.x)"
"${PYTHON_BIN}" - <<'PY'
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

echo "[phase12] pytest + coverage (requires WORKAI_DB__DSN for full integration coverage)"
"${PYTEST_BIN}" -q --cov=WorkAI --cov-report=term --cov-report=xml

echo "[phase12] done"
