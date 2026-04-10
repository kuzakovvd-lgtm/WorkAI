"""Generate reproducible Phase 12 performance baselines for ingest/parse/normalize."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import perf_counter

from WorkAI.config.settings import ParseSettings
from WorkAI.ingest.models import ValueRange
from WorkAI.ingest.runner import flatten_value_range
from WorkAI.normalize.models import RawTask
from WorkAI.normalize.runner import _normalize_sheet_rows
from WorkAI.parse.models import SheetCell
from WorkAI.parse.parser import parse_cells


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WorkAI Phase 12 benchmarks")
    parser.add_argument("--rows", type=int, default=200)
    parser.add_argument("--cols", type=int, default=40)
    parser.add_argument("--sheets", type=int, default=3)
    parser.add_argument("--output", type=str, default="")
    return parser


def main() -> int:
    args = _build_parser().parse_args()

    now = datetime.now(UTC)
    value_ranges = _make_value_ranges(args.sheets, args.rows, args.cols)

    ingest_started = perf_counter()
    flattened_total = 0
    for item in value_ranges:
        _, flattened = flatten_value_range("bench-spreadsheet", item)
        flattened_total += len(flattened)
    ingest_ms = (perf_counter() - ingest_started) * 1000

    cells = _make_parse_cells(args.rows, args.cols, now)
    parse_settings = ParseSettings(
        enabled=True,
        header_row_idx=1,
        employee_col_idx=1,
        max_cells_per_sheet=max(1, args.rows * args.cols),
        date_formats=["%Y-%m-%d", "%d.%m.%Y"],
    )
    parse_started = perf_counter()
    parsed_rows, parse_stats = parse_cells(cells, parse_settings)
    parse_ms = (perf_counter() - parse_started) * 1000

    normalize_rows = _make_raw_tasks_for_normalize(parsed_rows, now)
    normalize_started = perf_counter()
    normalize_result = _normalize_sheet_rows(
        run_id="phase12-bench",
        raw_rows=normalize_rows,
        settings=_bench_settings(),
        alias_map={},
        category_rules={},
    )
    normalize_ms = (perf_counter() - normalize_started) * 1000

    report = {
        "generated_at": now.isoformat(),
        "dataset": {
            "sheets": args.sheets,
            "rows": args.rows,
            "cols": args.cols,
            "parse_cells": len(cells),
            "raw_tasks": len(normalize_rows),
        },
        "ingest": {
            "duration_ms": round(ingest_ms, 2),
            "ranges": len(value_ranges),
            "flattened_cells": flattened_total,
        },
        "parse": {
            "duration_ms": round(parse_ms, 2),
            "tasks_emitted": len(parsed_rows),
            "stats": asdict(parse_stats),
        },
        "normalize": {
            "duration_ms": round(normalize_ms, 2),
            "rows_emitted": len(normalize_result.rows),
            "rows_failed": normalize_result.stats.rows_failed,
            "rows_skipped": normalize_result.stats.rows_skipped,
            "errors": len(normalize_result.errors),
        },
        "acceptance_guidance": {
            "ingest": "stable under configured sheet/range volume",
            "parse": "deterministic output; no failed cells in synthetic baseline",
            "normalize": "no limit_exceeded, no row-level failures in baseline",
        },
    }

    output_path = (
        Path(args.output)
        if args.output
        else Path("docs/perf") / f"phase12_baseline_{now.date().isoformat()}.md"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_to_markdown(report), encoding="utf-8")

    print(json.dumps({"output": str(output_path), "dataset": report["dataset"]}, ensure_ascii=False))
    return 0


def _make_value_ranges(sheets: int, rows: int, cols: int) -> list[ValueRange]:
    ranges: list[ValueRange] = []
    for sheet_index in range(1, sheets + 1):
        values: list[list[str]] = []
        for row in range(1, rows + 1):
            row_values = [f"S{sheet_index}-R{row}-C{col}" for col in range(1, cols + 1)]
            values.append(row_values)
        ranges.append(ValueRange(range=f"Sheet{sheet_index}!A1:AN{rows}", values=values))
    return ranges


def _make_parse_cells(rows: int, cols: int, now: datetime) -> list[SheetCell]:
    cells: list[SheetCell] = []
    for col in range(2, cols + 1):
        work_day = datetime(2026, 4, min(28, col), tzinfo=UTC).date().isoformat()
        cells.append(
            SheetCell(
                spreadsheet_id="bench-spreadsheet",
                sheet_title="Sheet1",
                row_idx=1,
                col_idx=col,
                a1=f"H{col}",
                value_text=work_day,
                ingested_at=now,
            )
        )
    for row in range(2, rows + 1):
        cells.append(
            SheetCell(
                spreadsheet_id="bench-spreadsheet",
                sheet_title="Sheet1",
                row_idx=row,
                col_idx=1,
                a1=f"A{row}",
                value_text=f"Employee {row}",
                ingested_at=now,
            )
        )
        for col in range(2, cols + 1):
            task_text = f"09:00-10:00 Task {row}-{col}\n10:00-10:30 Follow-up {row}-{col}"
            cells.append(
                SheetCell(
                    spreadsheet_id="bench-spreadsheet",
                    sheet_title="Sheet1",
                    row_idx=row,
                    col_idx=col,
                    a1=f"{col}{row}",
                    value_text=task_text,
                    ingested_at=now,
                )
            )
    return cells


def _make_raw_tasks_for_normalize(parsed_rows: list, now: datetime) -> list[RawTask]:
    result: list[RawTask] = []
    for idx, row in enumerate(parsed_rows, start=1):
        result.append(
            RawTask(
                raw_task_id=idx,
                spreadsheet_id=row.spreadsheet_id,
                sheet_title=row.sheet_title,
                row_idx=row.row_idx,
                col_idx=row.col_idx,
                cell_a1=row.cell_a1,
                cell_ingested_at=now - timedelta(minutes=idx % 7),
                employee_name_raw=row.employee_name_raw,
                work_date=row.work_date,
                line_no=row.line_no,
                line_text=row.line_text,
            )
        )
    return result


def _bench_settings():
    from WorkAI.config import get_settings

    settings = get_settings()
    settings.normalize.enabled = True
    settings.normalize.max_errors_per_sheet = 10000
    settings.normalize.fuzzy_enabled = False
    settings.normalize.time_parse_enabled = True
    return settings


def _to_markdown(report: dict) -> str:
    return "\n".join(
        [
            "# Phase 12 Performance Baseline",
            "",
            f"- Generated at: `{report['generated_at']}`",
            f"- Dataset: `{json.dumps(report['dataset'], ensure_ascii=False)}`",
            "",
            "## Ingest",
            f"- Duration (ms): `{report['ingest']['duration_ms']}`",
            f"- Ranges: `{report['ingest']['ranges']}`",
            f"- Flattened cells: `{report['ingest']['flattened_cells']}`",
            "",
            "## Parse",
            f"- Duration (ms): `{report['parse']['duration_ms']}`",
            f"- Tasks emitted: `{report['parse']['tasks_emitted']}`",
            "",
            "## Normalize",
            f"- Duration (ms): `{report['normalize']['duration_ms']}`",
            f"- Rows emitted: `{report['normalize']['rows_emitted']}`",
            f"- Rows failed: `{report['normalize']['rows_failed']}`",
            "",
            "## Acceptance Guidance",
            f"- Ingest: {report['acceptance_guidance']['ingest']}",
            f"- Parse: {report['acceptance_guidance']['parse']}",
            f"- Normalize: {report['acceptance_guidance']['normalize']}",
            "",
            "## Raw JSON",
            "```json",
            json.dumps(report, ensure_ascii=False, indent=2),
            "```",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
