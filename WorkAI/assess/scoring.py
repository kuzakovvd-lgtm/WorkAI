"""Deterministic task-level scoring rules for assess step 2."""

from __future__ import annotations

from WorkAI.assess.models import NormalizedTaskForScoring


def _clamp01(value: float) -> float:
    clamped = max(0.0, min(1.0, value))
    return round(clamped, 6)


def compute_smart_score(task: NormalizedTaskForScoring) -> float:
    """Compute smart score in [0, 1] using contract boolean flags only."""

    score = 1.0
    if not task.is_smart:
        score -= 0.5
    if task.is_micro:
        score -= 0.2
    if task.is_zhdun:
        score -= 0.2
    return _clamp01(score)


def compute_quality_score(task: NormalizedTaskForScoring) -> float:
    """Compute quality score in [0, 1] from time_source/result_confirmed."""

    score = 1.0

    source = task.time_source.strip().lower()
    if source == "none":
        score -= 0.6
    elif source == "estimated":
        score -= 0.3
    elif source in {"logged", "inferred"}:
        score -= 0.0
    else:
        # Unknown source is treated conservatively as estimated-quality evidence.
        score -= 0.3

    if not task.result_confirmed:
        score -= 0.4

    return _clamp01(score)
