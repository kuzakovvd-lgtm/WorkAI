"""CLI entrypoint for knowledge base indexing."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WorkAI knowledge base indexer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Index markdown methodology sources")
    run_parser.add_argument(
        "--source-dir",
        dest="source_dir",
        default="/etc/workai/knowledge/sources",
        help="Directory containing markdown sources (*.md)",
    )

    return parser


def main() -> int:
    from WorkAI.common import get_logger
    from WorkAI.knowledge_base import index_knowledge_sources

    parser = _build_parser()
    args = parser.parse_args()
    logger = get_logger(__name__)

    if args.command != "run":
        parser.error("Unsupported command")
        return 2

    try:
        result = index_knowledge_sources(source_dir=args.source_dir)
        logger.info(
            "knowledge_index_cli_completed",
            source_dir=args.source_dir,
            files_seen=result.files_seen,
            rows_upserted=result.rows_upserted,
            errors_count=result.errors_count,
        )
        return 0
    except Exception:
        logger.exception("knowledge_index_cli_failed", source_dir=args.source_dir)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
