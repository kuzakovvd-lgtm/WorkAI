"""Convenience wrapper for Alembic commands."""

from __future__ import annotations

import argparse
from pathlib import Path

from alembic import command
from alembic.config import Config

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run WorkAI Alembic migrations")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_upgrade = subparsers.add_parser("upgrade", help="Upgrade to target revision")
    parser_upgrade.add_argument("revision", nargs="?", default="head")

    parser_downgrade = subparsers.add_parser("downgrade", help="Downgrade to target revision")
    parser_downgrade.add_argument("revision", nargs="?", default="-1")

    subparsers.add_parser("current", help="Show current revision")

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    cfg = Config(str(ALEMBIC_INI))

    if args.command == "upgrade":
        command.upgrade(cfg, args.revision)
        return 0

    if args.command == "downgrade":
        command.downgrade(cfg, args.revision)
        return 0

    if args.command == "current":
        command.current(cfg)
        return 0

    parser.error("Unsupported command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
