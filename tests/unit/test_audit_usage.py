from __future__ import annotations

from types import SimpleNamespace

from WorkAI.audit.crew import _extract_usage


def test_extract_usage_prefers_available_metrics() -> None:
    crew = SimpleNamespace(usage_metrics={"input_tokens": 100, "output_tokens": 50, "cost_usd": 0.12})
    result = SimpleNamespace(usage_metrics={"input_tokens": 10, "output_tokens": 5})

    usage = _extract_usage(crew_result=result, crew=crew, duration_seconds=2.345)

    assert usage["input_tokens"] == 100
    assert usage["output_tokens"] == 50
    assert usage["cost_usd"] == 0.12
    assert usage["duration_seconds"] == 2.345


def test_extract_usage_is_resilient_to_bad_format() -> None:
    crew = SimpleNamespace(usage_metrics="broken")
    result = SimpleNamespace(_usage={"prompt_tokens": "x", "completion_tokens": None})

    usage = _extract_usage(crew_result=result, crew=crew, duration_seconds=1.0)

    assert usage["input_tokens"] == 0
    assert usage["output_tokens"] == 0
    assert usage["duration_seconds"] == 1.0
