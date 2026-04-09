from WorkAI.ops.cost_rollup import _extract_usage


def test_extract_usage_parses_values() -> None:
    report = {"_usage": {"input_tokens": 10, "output_tokens": 5, "cost_usd": 0.12}}
    usage = _extract_usage(report)
    assert usage is not None
    assert usage["input_tokens"] == 10
    assert usage["output_tokens"] == 5
    assert usage["cost_usd"] == 0.12


def test_extract_usage_handles_missing() -> None:
    assert _extract_usage({}) is None
    assert _extract_usage({"_usage": "bad"}) is None


def test_extract_usage_clamps_negative() -> None:
    report = {"_usage": {"input_tokens": -1, "output_tokens": -5, "cost_usd": -0.5}}
    usage = _extract_usage(report)
    assert usage is not None
    assert usage["input_tokens"] == 0
    assert usage["output_tokens"] == 0
    assert usage["cost_usd"] == 0.0
