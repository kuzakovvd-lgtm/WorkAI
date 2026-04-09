"""EXPLAIN helper for assess-like queries against tasks_normalized."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WorkAI assess-like EXPLAIN analyzer")
    parser.add_argument("--date", required=True, help="Work date in YYYY-MM-DD format")
    parser.add_argument("--sheet-id", required=False, help="Optional sheet_title filter")
    return parser


def _build_queries(date_value: str, sheet_id: str | None) -> list[tuple[str, str, tuple[object, ...]]]:
    sheet_filter = ""
    params: tuple[object, ...]
    if sheet_id is None:
        params = (date_value,)
    else:
        sheet_filter = " AND sheet_title = %s"
        params = (date_value, sheet_id)

    queries: list[tuple[str, str, tuple[object, ...]]] = [
        (
            "employee_daily_duration",
            f"""
EXPLAIN (ANALYZE, BUFFERS)
SELECT employee_name_norm, SUM(COALESCE(duration_minutes, 0)) AS total_minutes
FROM tasks_normalized
WHERE work_date = %s{sheet_filter}
GROUP BY employee_name_norm
ORDER BY total_minutes DESC
            """.strip(),
            params,
        ),
        (
            "category_daily_distribution",
            f"""
EXPLAIN (ANALYZE, BUFFERS)
SELECT COALESCE(category_code, 'uncategorized') AS category_code, COUNT(*)
FROM tasks_normalized
WHERE work_date = %s{sheet_filter}
GROUP BY COALESCE(category_code, 'uncategorized')
ORDER BY COUNT(*) DESC
            """.strip(),
            params,
        ),
        (
            "top_longest_tasks",
            f"""
EXPLAIN (ANALYZE, BUFFERS)
SELECT employee_name_norm, task_text_norm, COALESCE(duration_minutes, 0) AS duration_minutes
FROM tasks_normalized
WHERE work_date = %s{sheet_filter}
ORDER BY COALESCE(duration_minutes, 0) DESC
LIMIT 20
            """.strip(),
            params,
        ),
    ]
    return queries


def main() -> int:
    from WorkAI.common import configure_logging
    from WorkAI.config import get_settings
    from WorkAI.db import close_db, connection, init_db

    parser = _build_parser()
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings)
    init_db(settings)

    output_dir = PROJECT_ROOT / "docs" / "perf"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"assess_explain_{args.date}.md"

    lines: list[str] = [
        f"# Assess EXPLAIN baseline for {args.date}",
        "",
        f"- date: `{args.date}`",
        f"- sheet_id: `{args.sheet_id if args.sheet_id else 'ALL'}`",
        "",
    ]

    try:
        queries = _build_queries(args.date, args.sheet_id)
        with connection() as conn, conn.cursor() as cur:
            for name, sql, params in queries:
                cur.execute(sql, params)
                explain_rows = cur.fetchall()
                plan_lines = [str(row[0]) for row in explain_rows]

                lines.append(f"## {name}")
                lines.append("")
                lines.append("```text")
                lines.extend(plan_lines)
                lines.append("```")
                lines.append("")
    finally:
        close_db()

    rendered = "\n".join(lines).rstrip() + "\n"
    output_file.write_text(rendered, encoding="utf-8")
    print(rendered)
    print(f"Saved explain report: {output_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
