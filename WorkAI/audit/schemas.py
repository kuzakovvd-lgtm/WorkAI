"""Pydantic schemas for CrewAI audit outputs and final report."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, model_validator


class OperationalEfficiencyOutput(BaseModel):
    """Output of Operational Efficiency Analyst."""

    key_findings: list[str] = Field(default_factory=list)
    smart_actions: list[str] = Field(default_factory=list)
    blockers_zhdun: list[str] = Field(default_factory=list)


class DataIntegrityOutput(BaseModel):
    """Output of Data Integrity Forensic agent."""

    manipulation_signals: list[str] = Field(default_factory=list)
    weak_evidence_notes: list[str] = Field(default_factory=list)
    integrity_score: float = 1.0


class PriorityItem(BaseModel):
    """One management priority entry."""

    title: str
    rationale: str


class HighPriorityEmployee(BaseModel):
    """Cross-employee escalation placeholder structure."""

    employee_id: int
    reason: str


class FinalAuditReport(BaseModel):
    """Final report contract persisted into audit_runs.report_json."""

    employee_id: int
    task_date: date
    executive_summary: str
    index_of_trust_base: float = Field(ge=0.0, le=1.0)
    none_time_source_ratio: float = Field(ge=0.0, le=1.0)
    non_smart_ratio: float = Field(ge=0.0, le=1.0)
    index_of_trust: float | None = Field(default=None, ge=0.0, le=1.0)
    ghost_time_hours: float = Field(ge=0.0)
    management_priority: str | None = None
    top_3_priorities: list[PriorityItem] = Field(default_factory=list)
    high_priority_employees: list[HighPriorityEmployee] = Field(default_factory=list)
    key_findings: list[str] = Field(default_factory=list)
    smart_actions: list[str] = Field(default_factory=list)
    blockers_zhdun: list[str] = Field(default_factory=list)
    methodology_recommendation: str = ""

    @model_validator(mode="after")
    def derive_scores(self) -> FinalAuditReport:
        """Derive adjusted trust and management priority from base metrics."""

        if self.index_of_trust is None:
            adjusted = self.index_of_trust_base - 0.4 * self.none_time_source_ratio - 0.2 * self.non_smart_ratio
            self.index_of_trust = min(1.0, max(0.0, round(adjusted, 3)))

        if self.management_priority is None:
            if self.ghost_time_hours >= 4.0 or self.index_of_trust < 0.4:
                self.management_priority = "high"
            elif self.ghost_time_hours >= 2.0 or self.index_of_trust < 0.7:
                self.management_priority = "medium"
            else:
                self.management_priority = "low"

        if len(self.top_3_priorities) > 3:
            self.top_3_priorities = self.top_3_priorities[:3]

        return self
