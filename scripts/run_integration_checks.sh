#!/usr/bin/env bash
set -euo pipefail

PYTEST_BIN="${PYTEST_BIN:-pytest}"
ALEMBIC_BIN="${ALEMBIC_BIN:-alembic}"
DB_ENV_FILE="${DB_ENV_FILE:-/etc/workai/secrets/db.test.env}"
GOOGLE_ENV_FILE="${GOOGLE_ENV_FILE:-/etc/workai/secrets/google_sheets.test.env}"
MARK_EXPR="${WORKAI_PYTEST_MARK_EXPR:-integration}"

require_flags=(--require-integration-env)

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

echo "Running alembic upgrade head on integration DB..."
"${ALEMBIC_BIN}" upgrade head

echo "Running pytest -m \"${MARK_EXPR}\"..."
"${PYTEST_BIN}" -q -m "${MARK_EXPR}" "${require_flags[@]}" -rA
