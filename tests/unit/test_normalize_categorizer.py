from pathlib import Path

from WorkAI.normalize.categorizer import categorize, load_category_rules


def test_load_rules_and_categorize(tmp_path: Path) -> None:
    rules_path = tmp_path / "rules.json"
    rules_path.write_text(
        '{"meeting": ["sync", "call"], "coding": ["implement", "fix"]}',
        encoding="utf-8",
    )

    rules = load_category_rules(str(rules_path))
    assert categorize("Daily sync with team", rules) == "meeting"
    assert categorize("Implement parser fix", rules) == "coding"
    assert categorize("Lunch break", rules) is None
