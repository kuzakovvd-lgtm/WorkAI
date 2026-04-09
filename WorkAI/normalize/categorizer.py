"""Rule-based task categorization."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

CategoryRules = dict[str, list[str]]


def load_category_rules(path: str) -> CategoryRules:
    """Load category mapping from JSON file."""

    with Path(path).open("r", encoding="utf-8") as fh:
        payload = json.load(fh)

    if not isinstance(payload, Mapping):
        raise ValueError("Category rules file must contain a JSON object")

    rules: CategoryRules = {}
    for category, values in payload.items():
        if not isinstance(category, str) or category.strip() == "":
            continue
        if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
            continue
        keywords = [str(item).strip().casefold() for item in values if str(item).strip()]
        if keywords:
            rules[category.strip()] = keywords
    return rules


def categorize(text_norm: str, rules: CategoryRules) -> str | None:
    """Return category code by deterministic keyword contains match."""

    haystack = text_norm.casefold()
    for category in sorted(rules):
        keywords = rules[category]
        for keyword in keywords:
            if keyword in haystack:
                return category
    return None
