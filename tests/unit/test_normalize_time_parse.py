from WorkAI.normalize.time_parse import extract_time_info


def test_extract_time_range() -> None:
    info, cleaned = extract_time_info("10:00-11:30 Task")
    assert info is not None
    assert info.start is not None and info.start.hour == 10
    assert info.end is not None and info.end.hour == 11 and info.end.minute == 30
    assert info.duration_minutes == 90
    assert cleaned == "Task"


def test_extract_duration_hours_minutes() -> None:
    info, cleaned = extract_time_info("1h30m Task")
    assert info is not None
    assert info.duration_minutes == 90
    assert cleaned == "Task"


def test_extract_duration_russian() -> None:
    info, cleaned = extract_time_info("1ч 30м Task")
    assert info is not None
    assert info.duration_minutes == 90
    assert cleaned == "Task"


def test_invalid_range_end_before_start() -> None:
    info, cleaned = extract_time_info("23:30-01:00 Night task")
    assert info is None
    assert cleaned == "23:30-01:00 Night task"
