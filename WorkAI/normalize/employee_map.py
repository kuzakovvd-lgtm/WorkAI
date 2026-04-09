"""Employee canonicalization and matching helpers."""

from __future__ import annotations

import csv
import re
from difflib import SequenceMatcher
from pathlib import Path

from WorkAI.normalize.text_norm import normalize_unicode, normalize_whitespace

_NON_ALNUM_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)


def canonicalize_employee_name(name: str) -> str:
    """Normalize employee name for deterministic matching."""

    return normalize_whitespace(normalize_unicode(name))


def _key_for_match(name: str) -> str:
    normalized = canonicalize_employee_name(name).casefold()
    cleaned = _NON_ALNUM_RE.sub(" ", normalized)
    return normalize_whitespace(cleaned)


def build_employee_alias_map(csv_path: str) -> dict[str, str]:
    """Load alias map from CSV file alias,canonical."""

    result: dict[str, str] = {}
    with Path(csv_path).open("r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        for row in reader:
            if not row:
                continue
            if len(row) < 2:
                continue
            alias_raw = row[0].strip()
            canonical_raw = row[1].strip()
            if not alias_raw or not canonical_raw:
                continue
            if alias_raw.casefold() == "alias" and canonical_raw.casefold() == "canonical":
                continue
            result[canonicalize_employee_name(alias_raw)] = canonicalize_employee_name(canonical_raw)
    return result


def resolve_employee(
    name_raw: str,
    alias_map: dict[str, str],
    *,
    fuzzy_enabled: bool,
    fuzzy_threshold: int,
) -> tuple[str, str]:
    """Resolve employee name to canonical form and return match method."""

    canonical_raw = canonicalize_employee_name(name_raw)
    canonical_values = {canonicalize_employee_name(v) for v in alias_map.values()}

    if canonical_raw in canonical_values:
        return canonical_raw, "exact"

    alias_target = alias_map.get(canonical_raw)
    if alias_target is not None:
        return alias_target, "alias"

    if fuzzy_enabled and alias_map:
        target_by_key = {_key_for_match(v): v for v in canonical_values}
        probe = _key_for_match(canonical_raw)
        best_score = -1.0
        best_target: str | None = None
        for target_key, target_value in target_by_key.items():
            score = SequenceMatcher(None, probe, target_key).ratio() * 100.0
            if score > best_score:
                best_score = score
                best_target = target_value

        if best_target is not None and round(best_score) >= fuzzy_threshold:
            return best_target, "fuzzy"

    return canonical_raw, "fallback"
