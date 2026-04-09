from datetime import date

from WorkAI.assess.ghost_time import (
    calculate_ghost_minutes,
    calculate_index_of_trust_base,
    compute_index_of_trust_base,
)


def test_ghost_time_formula_non_negative() -> None:
    assert calculate_ghost_minutes(logged_minutes=300, workday_minutes=480) == 180
    assert calculate_ghost_minutes(logged_minutes=520, workday_minutes=480) == 0


def test_index_of_trust_no_tasks_is_zero() -> None:
    assert calculate_index_of_trust_base(total_tasks=0, none_count=0, unconfirmed_count=0) == 0.0


def test_index_of_trust_partial_ratios() -> None:
    value = calculate_index_of_trust_base(total_tasks=4, none_count=1, unconfirmed_count=2)
    assert value == 0.625


def test_index_of_trust_floor_zero() -> None:
    value = calculate_index_of_trust_base(total_tasks=2, none_count=2, unconfirmed_count=2)
    assert value == 0.0


def test_compute_index_no_rows_returns_zero(monkeypatch) -> None:
    class _FakeCur:
        def execute(self, *_args, **_kwargs) -> None:
            return None

        def fetchone(self):
            return (0, 0, 0, 0)

        def __enter__(self) -> "_FakeCur":
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

    class _FakeConn:
        def cursor(self) -> _FakeCur:
            return _FakeCur()

        def __enter__(self) -> "_FakeConn":
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

    class _FakeCtx:
        def __enter__(self) -> _FakeConn:
            return _FakeConn()

        def __exit__(self, *_exc: object) -> None:
            return None

    monkeypatch.setattr("WorkAI.assess.ghost_time.connection", lambda: _FakeCtx())
    assert compute_index_of_trust_base(employee_id=1, target_date=date(2026, 4, 9)) == 0.0
