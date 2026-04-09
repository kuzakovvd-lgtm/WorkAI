from pathlib import Path

from WorkAI.normalize.employee_map import (
    build_employee_alias_map,
    resolve_employee,
)


def test_build_employee_alias_map(tmp_path: Path) -> None:
    csv_path = tmp_path / "aliases.csv"
    csv_path.write_text(
        "alias,canonical\n Al , Alice Smith \n\u0411\u043e\u0431, Bob Ivanov\n",
        encoding="utf-8",
    )

    aliases = build_employee_alias_map(str(csv_path))

    assert aliases["Al"] == "Alice Smith"
    assert aliases["\u0411\u043e\u0431"] == "Bob Ivanov"


def test_resolve_employee_exact_alias_fallback() -> None:
    aliases = {
        "Al": "Alice Smith",
        "Bob I.": "Bob Ivanov",
    }

    name_norm, method = resolve_employee(
        "Alice Smith",
        aliases,
        fuzzy_enabled=False,
        fuzzy_threshold=90,
    )
    assert name_norm == "Alice Smith"
    assert method == "exact"

    name_norm, method = resolve_employee(
        "Al",
        aliases,
        fuzzy_enabled=False,
        fuzzy_threshold=90,
    )
    assert name_norm == "Alice Smith"
    assert method == "alias"

    name_norm, method = resolve_employee(
        "Unknown Person",
        aliases,
        fuzzy_enabled=False,
        fuzzy_threshold=90,
    )
    assert name_norm == "Unknown Person"
    assert method == "fallback"


def test_resolve_employee_fuzzy() -> None:
    aliases = {"Alyona Smth": "Alyona Smith"}

    name_norm, method = resolve_employee(
        "Alyona Smiht",
        aliases,
        fuzzy_enabled=True,
        fuzzy_threshold=75,
    )
    assert name_norm == "Alyona Smith"
    assert method == "fuzzy"
