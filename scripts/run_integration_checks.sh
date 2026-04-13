#!/usr/bin/env bash
set -euo pipefail

VENV_BIN="${VENV_BIN:-/opt/workai/.venv/bin}"
PYTEST_BIN="${PYTEST_BIN:-${VENV_BIN}/pytest}"
ALEMBIC_BIN="${ALEMBIC_BIN:-${VENV_BIN}/alembic}"
PYTHON_BIN="${PYTHON_BIN:-${VENV_BIN}/python3.12}"
DB_ENV_FILE="${DB_ENV_FILE:-/etc/workai/secrets/db.test.env}"
GOOGLE_ENV_FILE="${GOOGLE_ENV_FILE:-/etc/workai/secrets/google_sheets.test.env}"
MARK_EXPR="${WORKAI_PYTEST_MARK_EXPR:-integration}"

require_flags=(--require-integration-env)

resolve_executable() {
  local kind="$1"
  local candidate="$2"
  local override_var="$3"

  if [[ "${candidate}" == */* ]]; then
    if [[ -x "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
    echo "ERROR: ${kind} binary '${candidate}' was not found or is not executable." >&2
    echo "Hint: ensure ${VENV_BIN}/${kind} exists, or override ${override_var}." >&2
    return 1
  fi

  if command -v "${candidate}" >/dev/null 2>&1; then
    command -v "${candidate}"
    return 0
  fi

  echo "ERROR: ${kind} binary '${candidate}' was not found in PATH." >&2
  echo "Hint: install ${kind} in ${VENV_BIN} or pass explicit ${override_var} path." >&2
  return 1
}

if [[ ! -x "${PYTHON_BIN}" && -x "${VENV_BIN}/python" ]]; then
  PYTHON_BIN="${VENV_BIN}/python"
fi

PYTHON_BIN="$(resolve_executable "python" "${PYTHON_BIN}" "PYTHON_BIN")"
ALEMBIC_BIN="$(resolve_executable "alembic" "${ALEMBIC_BIN}" "ALEMBIC_BIN")"
PYTEST_BIN="$(resolve_executable "pytest" "${PYTEST_BIN}" "PYTEST_BIN")"

echo "Using interpreter: ${PYTHON_BIN}"
echo "Using alembic: ${ALEMBIC_BIN}"
echo "Using pytest: ${PYTEST_BIN}"

"${PYTHON_BIN}" - <<'PY'
import sys

if sys.version_info[:2] != (3, 12):
    raise SystemExit(
        f"Python 3.12.x is required for integration checks, got {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
print(f"integration python={sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
PY

if [[ ! -f "${DB_ENV_FILE}" ]]; then
  echo "Missing DB integration env file: ${DB_ENV_FILE}"
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${DB_ENV_FILE}"

if [[ "${MARK_EXPR}" == *"integration_online"* ]]; then
  if [[ ! -f "${GOOGLE_ENV_FILE}" ]]; then
    echo "Missing Google integration env file: ${GOOGLE_ENV_FILE}"
    exit 1
  fi
  # shellcheck disable=SC1090
  source "${GOOGLE_ENV_FILE}"
  require_flags+=(--require-integration-online-env)
fi
set +a

echo "Running migrations: ${ALEMBIC_BIN} upgrade head"
"${ALEMBIC_BIN}" upgrade head

echo "Running tests: ${PYTEST_BIN} -q -m \"${MARK_EXPR}\" ..."
"${PYTEST_BIN}" -q -m "${MARK_EXPR}" "${require_flags[@]}" -rA
