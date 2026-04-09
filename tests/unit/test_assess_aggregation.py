from __future__ import annotations

from datetime import date
from decimal import Decimal

from WorkAI.assess.aggregation import (
    aggregate_operational_cycles,
    build_cycle_key,
    similarity_ratio,
)
from WorkAI.assess.models import AssessmentTaskForAggregation


def _task(
    *,
    task_id: int,
    employee_id: int = 1,
    task_date: date = date(2026, 4, 11),
    sheet_title: str = "Sheet1",
    row_idx: int = 2,
    col_idx: int = 2,
    line_no: int = 1,
    canonical_text: str = "sync standup",
    task_category: str | None = "meeting",
    duration_minutes: int | None = 10,
    is_micro: bool = True,
    is_zhdun: bool = False,
    quality_score: Decimal | None = Decimal("0.900"),
    smart_score: Decimal | None = Decimal("0.800"),
) -> AssessmentTaskForAggregation:
    return AssessmentTaskForAggregation(
        normalized_task_id=task_id,
        employee_id=employee_id,
        task_date=task_date,
        spreadsheet_id="spreadsheet-1",
        sheet_title=sheet_title,
        row_idx=row_idx,
        col_idx=col_idx,
        line_no=line_no,
        canonical_text=canonical_text,
        task_category=task_category,
        duration_minutes=duration_minutes,
        is_micro=is_micro,
        is_zhdun=is_zhdun,
        quality_score=quality_score,
        smart_score=smart_score,
    )


def test_similarity_ratio_threshold_behavior() -> None:
    assert similarity_ratio("sync standup", "sync standup") >= 0.99
    assert similarity_ratio("sync standup", "deep coding") < 0.7


def test_micro_tasks_are_grouped_when_similar_and_adjacent() -> None:
    tasks = [
        _task(task_id=1, canonical_text="sync standup", row_idx=2),
        _task(task_id=2, canonical_text="sync stand-up", row_idx=2, col_idx=3),
    ]
    cycles = aggregate_operational_cycles(tasks)

    assert len(cycles) == 1
    cycle = cycles[0]
    assert cycle.tasks_count == 2
    assert cycle.total_duration_minutes == 20
    assert cycle.avg_quality_score == Decimal("0.900")


def test_non_micro_task_is_singleton_cycle() -> None:
    tasks = [_task(task_id=3, is_micro=False, canonical_text="Implement feature", task_category="coding", duration_minutes=60)]
    cycles = aggregate_operational_cycles(tasks)

    assert len(cycles) == 1
    cycle = cycles[0]
    assert cycle.tasks_count == 1
    assert cycle.task_category == "coding"
    assert cycle.total_duration_minutes == 60


def test_cycle_rollups_duration_scores_and_zhdun() -> None:
    tasks = [
        _task(task_id=4, canonical_text="wait deploy", is_zhdun=True, quality_score=Decimal("0.500"), smart_score=Decimal("0.200")),
        _task(task_id=5, canonical_text="wait deploy", row_idx=3, is_zhdun=False, quality_score=Decimal("0.700"), smart_score=Decimal("0.400")),
    ]
    cycles = aggregate_operational_cycles(tasks)

    assert len(cycles) == 1
    cycle = cycles[0]
    assert cycle.is_zhdun is True
    assert cycle.total_duration_minutes == 20
    assert cycle.avg_quality_score == Decimal("0.600")
    assert cycle.avg_smart_score == Decimal("0.300")


def test_cycle_key_is_deterministic_for_same_input() -> None:
    key1 = build_cycle_key(
        employee_id=1,
        task_date="2026-04-11",
        task_category="meeting",
        representative_text="sync standup",
        anchor_ref="spreadsheet-1:Sheet1:2:2:1",
    )
    key2 = build_cycle_key(
        employee_id=1,
        task_date="2026-04-11",
        task_category="meeting",
        representative_text="sync standup",
        anchor_ref="spreadsheet-1:Sheet1:2:2:1",
    )
    assert key1 == key2
