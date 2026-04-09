from datetime import date

from WorkAI.assess.models import NormalizedTaskForScoring
from WorkAI.assess.scoring import compute_quality_score, compute_smart_score


def _task(**overrides: object) -> NormalizedTaskForScoring:
    base = {
        "normalized_task_id": 1,
        "employee_id": 10,
        "task_date": date(2026, 4, 9),
        "duration_minutes": 60,
        "time_source": "logged",
        "is_smart": True,
        "is_micro": False,
        "result_confirmed": True,
        "is_zhdun": False,
    }
    base.update(overrides)
    return NormalizedTaskForScoring(**base)


def test_smart_score_baseline() -> None:
    assert compute_smart_score(_task()) == 1.0


def test_smart_score_penalties() -> None:
    assert compute_smart_score(_task(is_smart=False)) == 0.5
    assert compute_smart_score(_task(is_micro=True)) == 0.8
    assert compute_smart_score(_task(is_zhdun=True)) == 0.8
    assert compute_smart_score(_task(is_smart=False, is_micro=True, is_zhdun=True)) == 0.1


def test_quality_score_time_source_variants() -> None:
    assert compute_quality_score(_task(time_source="logged", result_confirmed=True)) == 1.0
    assert compute_quality_score(_task(time_source="inferred", result_confirmed=True)) == 1.0
    assert compute_quality_score(_task(time_source="estimated", result_confirmed=True)) == 0.7
    assert compute_quality_score(_task(time_source="none", result_confirmed=True)) == 0.4


def test_quality_score_unconfirmed_penalty() -> None:
    assert compute_quality_score(_task(time_source="logged", result_confirmed=False)) == 0.6
    assert compute_quality_score(_task(time_source="none", result_confirmed=False)) == 0.0


def test_score_bounds_are_clamped() -> None:
    smart = compute_smart_score(_task(is_smart=False, is_micro=True, is_zhdun=True))
    quality = compute_quality_score(_task(time_source="none", result_confirmed=False))
    assert 0.0 <= smart <= 1.0
    assert 0.0 <= quality <= 1.0
