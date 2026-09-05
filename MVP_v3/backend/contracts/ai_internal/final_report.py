"""Internal contract for an AI-authored final Case report."""

from __future__ import annotations

from pydantic import Field

from contracts.diagnosis import StrictModel


class FinalCaseReportInput(StrictModel):
    case_id: str
    case_summary: str = Field(default="", max_length=4_000)
    workflow_status: str
    case_mode: str
    known_facts: list[str] = Field(default_factory=list, max_length=40)
    recent_conversation: list[str] = Field(default_factory=list, max_length=30)
    verification_results: list[str] = Field(default_factory=list, max_length=30)
    action_results: list[str] = Field(default_factory=list, max_length=30)
    customer_answers: list[str] = Field(default_factory=list, max_length=30)
    closure_note: str = Field(default="", max_length=10_000)


class FinalCaseReportOutput(StrictModel):
    title: str
    executive_summary: str
    incident_summary: str
    verified_facts: list[str] = Field(default_factory=list, max_length=20)
    actions_taken: list[str] = Field(default_factory=list, max_length=20)
    resolution: str
    follow_up: list[str] = Field(default_factory=list, max_length=12)
    cautions: list[str] = Field(default_factory=list, max_length=12)
    model_mode: str
