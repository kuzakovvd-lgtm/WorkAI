from __future__ import annotations

from WorkAI.audit.tools import should_use_methodology_lookup


def test_methodology_tool_threshold() -> None:
    assert should_use_methodology_lookup(3.99) is False
    assert should_use_methodology_lookup(4.0) is True
