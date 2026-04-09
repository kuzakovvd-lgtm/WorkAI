"""CLI entrypoint for verify_units."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WorkAI verify systemd units")
    parser.add_argument("--unit-dir", dest="unit_dir", default="/etc/systemd/system")
    return parser


def main() -> int:
    from WorkAI.ops.verify_units import run_verify_units, verify_units_to_dict

    args = _build_parser().parse_args()
    result = run_verify_units(unit_dir=args.unit_dir)
    print(json.dumps(verify_units_to_dict(result), ensure_ascii=False, indent=2))
    if result.severity == "infra_critical":
        return 2
    if result.severity == "data_warning":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
