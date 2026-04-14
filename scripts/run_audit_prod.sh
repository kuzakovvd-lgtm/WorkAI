#!/usr/bin/env bash
set -euo pipefail

EMPLOYEE_ID="${WORKAI_AUDIT_EMPLOYEE_ID:-}"
TARGET_DATE="${WORKAI_AUDIT_TARGET_DATE:-}"
FORCE="${WORKAI_AUDIT_FORCE:-false}"
PROJECT_DIR="${WORKAI_PROJECT_DIR:-/opt/workai}"
PYTHON_BIN="${WORKAI_PYTHON_BIN:-/opt/workai/.venv/bin/python}"
HOME_DIR="${HOME:-/opt/workai}"

if [[ -z "$EMPLOYEE_ID" || -z "$TARGET_DATE" ]]; then
  echo "WORKAI_AUDIT_EMPLOYEE_ID and WORKAI_AUDIT_TARGET_DATE are required." >&2
  exit 2
fi

if [[ ! -d "$PROJECT_DIR" ]]; then
  echo "Missing project directory: $PROJECT_DIR" >&2
  exit 2
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing python binary: $PYTHON_BIN" >&2
  exit 2
fi

if [[ ! -f /etc/workai/secrets/db.env || ! -f /etc/workai/secrets/workai.env || ! -f /etc/workai/secrets/api.env ]]; then
  echo "Missing required env files in /etc/workai/secrets/" >&2
  exit 2
fi

CMD=( "$PYTHON_BIN" "$PROJECT_DIR/scripts/run_audit.py" run --employee-id "$EMPLOYEE_ID" --date "$TARGET_DATE" )
if [[ "$FORCE" == "true" || "$FORCE" == "1" ]]; then
  CMD+=( --force )
fi

# Load prod env contract exactly like systemd services.
set -a
source /etc/workai/secrets/db.env
source /etc/workai/secrets/api.env
source /etc/workai/secrets/workai.env
if [[ -f /etc/workai/secrets/openai.env ]]; then
  source /etc/workai/secrets/openai.env
fi
export HOME="$HOME_DIR"
export WORKAI_AUDIT__ENABLED="${WORKAI_AUDIT__ENABLED:-true}"
set +a

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY is not set in /etc/workai/secrets/workai.env or openai.env" >&2
  exit 2
fi

cd "$PROJECT_DIR"

ENV_ARGS=()
while IFS= read -r var_name; do
  ENV_ARGS+=( "${var_name}=${!var_name}" )
done < <(compgen -v | grep -E '^(WORKAI_|OPENAI_)')

ENV_ARGS+=( "HOME=$HOME" )
exec env "${ENV_ARGS[@]}" "${CMD[@]}"
