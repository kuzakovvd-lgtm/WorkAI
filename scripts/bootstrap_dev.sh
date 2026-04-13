#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3.12}"
VENV_DIR="${VENV_DIR:-.venv}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Required interpreter '${PYTHON_BIN}' not found. Install Python 3.12 first."
  exit 1
fi

"${PYTHON_BIN}" - <<'PY'
import sys

if sys.version_info[:2] != (3, 12):
    raise SystemExit(
        f"Python 3.12.x is required, got {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
PY

"${PYTHON_BIN}" -m venv "${VENV_DIR}"

"${VENV_DIR}/bin/python" - <<'PY'
import sys

if sys.version_info[:2] != (3, 12):
    raise SystemExit(
        f"Virtualenv must use Python 3.12.x, got {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
print(f"Using Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
PY

"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/pip" install -e ".[dev]"

echo "Bootstrap complete. Activate with: source ${VENV_DIR}/bin/activate"
