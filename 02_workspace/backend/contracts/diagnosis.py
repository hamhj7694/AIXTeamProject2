from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


SCHEMA_VERSION = "diagnosis.v1"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RiskLevel(str, Enum):
    NORMAL = "NORMAL"
    LOW = "LOW"
    HIGH = "HIGH"


class AnalyzeTextRequest(StrictModel):
    text: str = Field(min_length=1, max_length=50_000)
    client_request_id: str | None = Field(default=None, max_length=100)
    sample_type: str | None = Field(default=None, max_length=50)


class Evidence(StrictModel):
    turn: int = Field(ge=1)
    event_family: str
    subtype: str | None = None
    text: str


class ExtractedEvent(StrictModel):
    event_family: Literal[
        "IMPERSONATION", "PSY_STRATEGY", "ACTION_REQUEST", "MONEY_MOVEMENT", "AMOUNT"
    ]
    subtype: str | None = None
    impersonation_group: str | None = None
    evidence_turn_id: int = Field(ge=1)
    evidence_text: str
    amount_krw: float | None = Field(default=None, ge=0)
    amount_context: str | None = None
    is_requested: bool | None = None
    detected_at_turn: int = Field(ge=1)


class WindowResult(StrictModel):
    segment_id: str
    start_turn: int
    end_turn: int
    text: str
    features: dict[str, float]
    raw_ml_risk_score: float = Field(ge=0, le=100)
    final_risk_score: float = Field(ge=0, le=100)
    threshold_score: float = Field(ge=0, le=100)
    candidate_signal_count: int = Field(ge=0)
    guardrail_applied: bool
    label: Literal["NORMAL", "PHISHING"]


class ContextResult(StrictModel):
    summary: str
    incident_type: str
    claims: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class WindowAnalysisResult(StrictModel):
    turns: list[str]
    events: list[ExtractedEvent]
    windows: list[WindowResult]
    extractor_model: str
    warnings: list[str] = Field(default_factory=list)


class DiagnosisResult(StrictModel):
    schema_version: str = SCHEMA_VERSION
    case_id: str | None = None
    risk_level: RiskLevel
    risk_score: float = Field(ge=0, le=100)
    model_label: Literal["NORMAL", "PHISHING"]
    context: ContextResult
    events: list[ExtractedEvent]
    windows: list[WindowResult]
    evidence: list[Evidence]
    features: dict[str, float]
    model_metadata: dict[str, Any]
    confidence: float = Field(ge=0, le=1)
    partial_failure: bool = False
    warnings: list[str] = Field(default_factory=list)


class AiError(StrictModel):
    code: str
    message: str
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class ReportSection(StrictModel):
    section_key: Literal[
        "summary", "risk_context", "transfer_status", "verification_status",
        "current_actions", "unresolved_items", "next_checks",
    ]
    content: dict[str, Any]
    version: int = 1


class InitialReport(StrictModel):
    report_id: str
    case_id: str
    report_version: int = 1
    status: Literal["LIVE"] = "LIVE"
    sections: list[ReportSection]
    created_at: str


class AnalyzeCaseResponse(StrictModel):
    schema_version: str = SCHEMA_VERSION
    disposition: Literal["CASE_CREATED", "NO_CASE", "FAILED"]
    case_id: str | None = None
    risk: RiskLevel | None = None
    mode: Literal["PREVENT"] | None = None
    status: Literal["TRIAGE"] | None = None
    initial_brief: str | None = None
    diagnosis: DiagnosisResult | None = None
    initial_report: InitialReport | None = None
    error: AiError | None = None
