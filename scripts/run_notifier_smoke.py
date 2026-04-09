"""CLI entrypoint for notifier smoke send."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WorkAI notifier smoke runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    send_parser = subparsers.add_parser("send-test", help="Send one Telegram alert and log attempt")
    send_parser.add_argument("--level", choices=["infra_critical", "data_warning", "info"], required=True)
    send_parser.add_argument("--subject", required=True)
    send_parser.add_argument("--body", default=None)

    return parser


def main() -> int:
    from WorkAI.common import configure_logging, get_logger
    from WorkAI.config import get_settings
    from WorkAI.db import close_db
    from WorkAI.notifier import TelegramNotifier

    parser = _build_parser()
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings)
    logger = get_logger(__name__)

    if args.command != "send-test":
        parser.error("Unsupported command")
        return 2

    notifier = TelegramNotifier(settings=settings)
    result = notifier.send_alert(level=args.level, subject=args.subject, body=args.body)

    logger.info(
        "notifier_smoke_completed",
        level=result.level,
        channel=result.channel,
        delivered=result.delivered,
        error=result.error,
    )
    close_db()
    return 0 if result.delivered else 1


if __name__ == "__main__":
    raise SystemExit(main())
