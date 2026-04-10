from __future__ import annotations

from datetime import date

from WorkAI.ops.parallel_diff import compare_counts


def test_compare_counts_marks_violations() -> None:
    result = compare_counts(
        target_date=date(2026, 4, 9),
        reference_counts={"raw_tasks": 100, "tasks_normalized": 95},
        candidate_counts={"raw_tasks": 97, "tasks_normalized": 80},
        tolerance_pct=5.0,
    )

    assert "raw_tasks" not in result.violations
    assert "tasks_normalized" in result.violations


def test_compare_counts_zero_reference_handling() -> None:
    result = compare_counts(
        target_date=date(2026, 4, 9),
        reference_counts={"audit_runs": 0},
        candidate_counts={"audit_runs": 0},
        tolerance_pct=5.0,
    )
    assert result.violations == []
    assert result.diffs[0].delta_pct == 0.0

