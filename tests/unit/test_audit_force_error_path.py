from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from WorkAI.audit import crew as audit_crew_module
from WorkAI.audit.models import AuditPrefetchPayload, AuditRunRecord
from WorkAI.common import DatabaseError


def test_force_error_path_persists_failed_even_if_pool_was_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    state = {
        "pool_open": False,
        "init_calls": 0,
        "mark_failed_calls": 0,
    }

    def fake_configure_logging(_: object) -> None:
        return None

    def fake_init_db(_: object | None = None) -> None:
        state["pool_open"] = True
        state["init_calls"] += 1

    def fake_close_db() -> None:
        state["pool_open"] = False

    @contextmanager
    def fake_connection() -> object:
        if not state["pool_open"]:
            raise DatabaseError("pool closed")

        class _DummyCursor:
            def __enter__(self) -> _DummyCursor:
                return self

            def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
                return False

        class _DummyConn:
            def cursor(self) -> _DummyCursor:
                return _DummyCursor()

            def commit(self) -> None:
                return None

        yield _DummyConn()

    run_id = uuid4()

    def fake_find_completed_run(cur: object, employee_id: int, task_date: date) -> None:
        del cur, employee_id, task_date
        return None

    def fake_insert_run(
        cur: object,
        *,
        employee_id: int,
        task_date: date,
        status: str,
        report_json: dict[str, object] | None,
        error: str | None,
        forced: bool,
    ) -> AuditRunRecord:
        del cur, status, report_json, error, forced
        return AuditRunRecord(
            id=run_id,
            employee_id=employee_id,
            task_date=task_date,
            status="processing",
            started_at=datetime.now(UTC),
            finished_at=None,
            report_json=None,
            forced=True,
        )

    def fake_fetch_prefetch_payload(cur: object, employee_id: int, task_date: date) -> AuditPrefetchPayload:
        del cur
        return AuditPrefetchPayload(
            employee_id=employee_id,
            task_date=task_date,
            index_of_trust_base=0.5,
            none_time_source_ratio=0.2,
            non_smart_ratio=0.2,
            ghost_time_hours=5.0,
            aggregated_tasks=[],
        )

    def fake_mark_run_failed(cur: object, run: object, error: str) -> None:
        del cur, run, error
        state["mark_failed_calls"] += 1

    class _FailingCrew:
        def kickoff(self, *, inputs: dict[str, object]) -> dict[str, object]:
            del inputs
            # Simulate pool closure during tool execution (previously came from KB lookup close_db()).
            fake_close_db()
            raise RuntimeError("forced test failure")

    def fake_crew_builder(*, settings: object, use_methodology_tool: bool) -> _FailingCrew:
        del settings, use_methodology_tool
        return _FailingCrew()

    monkeypatch.setattr(audit_crew_module, "configure_logging", fake_configure_logging)
    monkeypatch.setattr(audit_crew_module, "init_db", fake_init_db)
    monkeypatch.setattr(audit_crew_module, "close_db", fake_close_db)
    monkeypatch.setattr(audit_crew_module, "connection", fake_connection)
    monkeypatch.setattr(audit_crew_module, "find_completed_run", fake_find_completed_run)
    monkeypatch.setattr(audit_crew_module, "insert_run", fake_insert_run)
    monkeypatch.setattr(audit_crew_module, "fetch_prefetch_payload", fake_fetch_prefetch_payload)
    monkeypatch.setattr(audit_crew_module, "mark_run_failed", fake_mark_run_failed)

    settings = SimpleNamespace(audit=SimpleNamespace(enabled=True))

    with pytest.raises(RuntimeError, match="forced test failure"):
        audit_crew_module.run_audit(
            employee_id=7,
            task_date=date(2026, 4, 10),
            force=True,
            settings=settings,
            crew_builder=fake_crew_builder,
        )

    # Initial init + one re-init for failed-run persistence after pool closure.
    assert state["init_calls"] == 2
    assert state["mark_failed_calls"] == 1
