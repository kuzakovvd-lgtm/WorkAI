"""Deterministic operational-cycle aggregation for assess step 3."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from difflib import SequenceMatcher
from hashlib import sha1

from WorkAI.assess.models import AssessmentTaskForAggregation, OperationalCycleRow

SIMILARITY_THRESHOLD = 0.70


@dataclass
class _CycleBuilder:
    employee_id: int
    task_date: date
    task_category: str
    representative_text: str
    anchor_ref: str
    task_ids: list[int]
    total_duration_minutes: int
    tasks_count: int
    is_zhdun: bool
    quality_scores: list[Decimal]
    smart_scores: list[Decimal]


def similarity_ratio(left: str, right: str) -> float:
    """Return deterministic text similarity in [0,1] for aggregation decisions."""

    left_norm = left.casefold().strip()
    right_norm = right.casefold().strip()
    if not left_norm and not right_norm:
        return 1.0
    return SequenceMatcher(a=left_norm, b=right_norm).ratio()


def build_cycle_key(
    *,
    employee_id: int,
    task_date: str,
    task_category: str,
    representative_text: str,
    anchor_ref: str,
) -> str:
    """Build a stable cycle key independent from surrogate task ids."""

    payload = "|".join(
        [
            str(employee_id),
            task_date,
            task_category.casefold().strip(),
            representative_text.casefold().strip(),
            anchor_ref,
        ]
    )
    digest = sha1(payload.encode("utf-8")).hexdigest()[:16]
    return f"cycle:{digest}"


def aggregate_operational_cycles(tasks: list[AssessmentTaskForAggregation]) -> list[OperationalCycleRow]:
    """Aggregate tasks into deterministic operational cycles."""

    if not tasks:
        return []

    sorted_tasks = sorted(
        tasks,
        key=lambda row: (
            row.employee_id,
            row.task_date,
            row.sheet_title,
            row.row_idx,
            row.col_idx,
            row.line_no,
            row.normalized_task_id,
        ),
    )
    # MVP limitation: we don't have reliable start/end timestamps in contract yet,
    # so "neighborhood" is approximated by deterministic sheet position order.

    cycles: list[OperationalCycleRow] = []
    current: _CycleBuilder | None = None

    for task in sorted_tasks:
        category = _normalize_category(task.task_category)
        anchor_ref = _anchor_ref(task)

        if task.is_micro:
            if _can_merge_into_current(current, task, category):
                assert current is not None
                current.task_ids.append(task.normalized_task_id)
                current.total_duration_minutes += _duration(task.duration_minutes)
                current.tasks_count += 1
                current.is_zhdun = current.is_zhdun or task.is_zhdun
                _append_scores(current, task)
            else:
                if current is not None:
                    cycles.append(_build_operational_cycle(current))
                current = _CycleBuilder(
                    employee_id=task.employee_id,
                    task_date=task.task_date,
                    task_category=category,
                    representative_text=task.canonical_text,
                    anchor_ref=anchor_ref,
                    task_ids=[task.normalized_task_id],
                    total_duration_minutes=_duration(task.duration_minutes),
                    tasks_count=1,
                    is_zhdun=task.is_zhdun,
                    quality_scores=[],
                    smart_scores=[],
                )
                _append_scores(current, task)
            continue

        if current is not None:
            cycles.append(_build_operational_cycle(current))
            current = None

        singleton = _CycleBuilder(
            employee_id=task.employee_id,
            task_date=task.task_date,
            task_category=category,
            representative_text=task.canonical_text,
            anchor_ref=anchor_ref,
            task_ids=[task.normalized_task_id],
            total_duration_minutes=_duration(task.duration_minutes),
            tasks_count=1,
            is_zhdun=task.is_zhdun,
            quality_scores=[],
            smart_scores=[],
        )
        _append_scores(singleton, task)
        cycles.append(_build_operational_cycle(singleton))

    if current is not None:
        cycles.append(_build_operational_cycle(current))

    return cycles


def _can_merge_into_current(
    current: _CycleBuilder | None,
    task: AssessmentTaskForAggregation,
    category: str,
) -> bool:
    if current is None:
        return False
    if current.employee_id != task.employee_id:
        return False
    if current.task_date != task.task_date:
        return False
    if current.task_category != category:
        return False
    return similarity_ratio(current.representative_text, task.canonical_text) >= SIMILARITY_THRESHOLD


def _build_operational_cycle(builder: _CycleBuilder) -> OperationalCycleRow:
    avg_quality = _average(builder.quality_scores)
    avg_smart = _average(builder.smart_scores)

    cycle_key = build_cycle_key(
        employee_id=builder.employee_id,
        task_date=builder.task_date.isoformat(),
        task_category=builder.task_category,
        representative_text=builder.representative_text,
        anchor_ref=builder.anchor_ref,
    )

    return OperationalCycleRow(
        employee_id=builder.employee_id,
        task_date=builder.task_date,
        cycle_key=cycle_key,
        canonical_text=builder.representative_text,
        task_category=builder.task_category,
        total_duration_minutes=builder.total_duration_minutes,
        tasks_count=builder.tasks_count,
        is_zhdun=builder.is_zhdun,
        avg_quality_score=avg_quality,
        avg_smart_score=avg_smart,
    )


def _average(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    return sum(values) / Decimal(len(values))


def _duration(value: int | None) -> int:
    return 0 if value is None else value


def _normalize_category(value: str | None) -> str:
    raw = (value or "").strip()
    return raw if raw else "uncategorized"


def _anchor_ref(task: AssessmentTaskForAggregation) -> str:
    return f"{task.spreadsheet_id}:{task.sheet_title}:{task.row_idx}:{task.col_idx}:{task.line_no}"


def _append_scores(builder: _CycleBuilder, task: AssessmentTaskForAggregation) -> None:
    if task.quality_score is not None:
        builder.quality_scores.append(task.quality_score)
    if task.smart_score is not None:
        builder.smart_scores.append(task.smart_score)
