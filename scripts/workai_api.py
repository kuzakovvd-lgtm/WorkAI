#!/usr/bin/env python3
"""Run WorkAI FastAPI server."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for API runner."""

    parser = argparse.ArgumentParser(description="WorkAI API runner")
    parser.add_argument("command", choices=["run"], help="Command to execute")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8000, help="Bind port")
    return parser


def main() -> int:
    """Run selected command."""

    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        uvicorn.run("WorkAI.api.main:app", host=args.host, port=args.port)
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
