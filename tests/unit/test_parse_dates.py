from datetime import date

from WorkAI.parse.date_parse import parse_work_date


def test_parse_work_date_iso() -> None:
    parsed = parse_work_date("2026-04-08", ["%Y-%m-%d", "%d.%m.%Y"])
    assert parsed == date(2026, 4, 8)


def test_parse_work_date_russian_dot_format() -> None:
    parsed = parse_work_date("08.04.2026", ["%Y-%m-%d", "%d.%m.%Y"])
    assert parsed == date(2026, 4, 8)


def test_parse_work_date_invalid_returns_none() -> None:
    parsed = parse_work_date("2026/04/08", ["%Y-%m-%d", "%d.%m.%Y"])
    assert parsed is None
