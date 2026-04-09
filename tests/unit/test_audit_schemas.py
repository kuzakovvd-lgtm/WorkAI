from __future__ import annotations

from datetime import date

from WorkAI.audit.schemas import FinalAuditReport, PriorityItem


def test_final_report_derives_trust_and_priority() -> None:
    report = FinalAuditReport.model_validate(
        {
            "employee_id": 1,
            "task_date": date(2026, 4, 9),
            "executive_summary": "Summary",
            "index_of_trust_base": 0.9,
            "none_time_source_ratio": 0.5,
            "non_smart_ratio": 0.25,
            "ghost_time_hours": 1.0,
            "top_3_priorities": [
                {"title": "P1", "rationale": "R1"},
                {"title": "P2", "rationale": "R2"},
                {"title": "P3", "rationale": "R3"},
                {"title": "P4", "rationale": "R4"},
            ],
            "methodology_recommendation": "Use standard flow",
        }
    )

    assert report.index_of_trust == 0.65
    assert report.management_priority == "medium"
    assert len(report.top_3_priorities) == 3


def test_final_report_high_priority_by_ghost_time() -> None:
    report = FinalAuditReport.model_validate(
        {
            "employee_id": 2,
            "task_date": date(2026, 4, 9),
            "executive_summary": "Summary",
            "index_of_trust_base": 0.95,
            "none_time_source_ratio": 0.0,
            "non_smart_ratio": 0.0,
            "ghost_time_hours": 4.2,
            "top_3_priorities": [PriorityItem(title="Fix", rationale="ghost time")],
            "methodology_recommendation": "Reduce ghost windows",
        }
    )
    assert report.management_priority == "high"
