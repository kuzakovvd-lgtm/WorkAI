from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import uuid4

from WorkAI.audit import crew as audit_crew_module
from WorkAI.audit.models import AuditPrefetchPayload, AuditRunRecord


def test_audit_retries_once_and_completes(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    state = {
        "kickoff_calls": 0,
        "mark_completed_calls": 0,
        "mark_failed_calls": 0,
    }
    run_id = uuid4()

    def fake_configure_logging(_: object) -> None:
        return None

    def fake_init_db(_: object | None = None) -> None:
        return None

    def fake_close_db() -> None:
        return None

    @contextmanager
    def fake_connection() -> object:
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
            index_of_trust_base=0.7,
            none_time_source_ratio=0.1,
            non_smart_ratio=0.2,
            ghost_time_hours=2.0,
            aggregated_tasks=[],
        )

    def fake_mark_run_completed(cur: object, run: object, report_json: dict[str, object]) -> None:
        del cur, run, report_json
        state["mark_completed_calls"] += 1

    def fake_mark_run_failed(cur: object, run: object, error: str) -> None:
        del cur, run, error
        state["mark_failed_calls"] += 1

    class _FlakyCrew:
        def kickoff(self, *, inputs: dict[str, object]) -> dict[str, object]:
            del inputs
            state["kickoff_calls"] += 1
            if state["kickoff_calls"] == 1:
                raise RuntimeError("transient LLM error")
            return {
                "executive_summary": "ok",
                "top_3_priorities": [{"title": "a", "rationale": "b"}],
                "high_priority_employees": [],
                "key_findings": ["f1"],
                "smart_actions": ["s1"],
                "blockers_zhdun": [],
                "methodology_recommendation": "m1",
            }

    def fake_crew_builder(*, settings: object, use_methodology_tool: bool) -> _FlakyCrew:
        del settings, use_methodology_tool
        return _FlakyCrew()

    monkeypatch.setattr(audit_crew_module, "configure_logging", fake_configure_logging)
    monkeypatch.setattr(audit_crew_module, "init_db", fake_init_db)
    monkeypatch.setattr(audit_crew_module, "close_db", fake_close_db)
    monkeypatch.setattr(audit_crew_module, "connection", fake_connection)
    monkeypatch.setattr(audit_crew_module, "find_completed_run", fake_find_completed_run)
    monkeypatch.setattr(audit_crew_module, "insert_run", fake_insert_run)
    monkeypatch.setattr(audit_crew_module, "fetch_prefetch_payload", fake_fetch_prefetch_payload)
    monkeypatch.setattr(audit_crew_module, "mark_run_completed", fake_mark_run_completed)
    monkeypatch.setattr(audit_crew_module, "mark_run_failed", fake_mark_run_failed)

    settings = SimpleNamespace(audit=SimpleNamespace(enabled=True, failed_retry_attempts=1))
    result = audit_crew_module.run_audit(
        employee_id=7,
        task_date=date(2026, 4, 10),
        force=True,
        settings=settings,
        crew_builder=fake_crew_builder,
    )

    assert result.status == "completed"
    assert state["kickoff_calls"] == 2
    assert state["mark_completed_calls"] == 1
    assert state["mark_failed_calls"] == 0
