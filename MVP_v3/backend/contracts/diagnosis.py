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


class ObservedLexicalCue(StrictModel):
    """A short, allowlisted source term; never a sentence or sensitive literal."""

    surface_form: str = Field(min_length=1, max_length=16)
    lemma: str | None = Field(default=None, max_length=32)
    normalized_code: str = Field(min_length=3, max_length=64, pattern=r"^[A-Z][A-Z0-9_.]*$")
    term_type: Literal[
        "INSTITUTION", "ROLE", "SCAM_TERM", "AUTH_SECRET_TYPE", "ACTION",
        "THREAT", "URGENCY", "OBLIGATION", "QUANTITY", "SECRECY",
    ]
    semantic_value: str | None = Field(default=None, max_length=60)
    confidence: float = Field(ge=0, le=1)


class UnmappedObservation(StrictModel):
    """Privacy-safe meaning that is not yet mapped to a canonical semantic key."""

    observation_id: str = Field(min_length=1, max_length=100)
    observation_type: str = Field(min_length=1, max_length=80)
    candidate_categories: list[str] = Field(default_factory=list, max_length=12)
    lexical_codes: list[str] = Field(default_factory=list, max_length=20)
    observed_terms: list[ObservedLexicalCue] = Field(default_factory=list, max_length=12)
    speech_act: str | None = Field(default=None, max_length=60)
    action_state: str | None = Field(default=None, max_length=40)
    polarity: str = Field(default="POSITIVE", max_length=40)
    modality: str | None = Field(default=None, max_length=40)
    amount_role: str | None = Field(default=None, max_length=40)
    amount_value_krw: float | None = Field(default=None, ge=0)
    source_turn_id: int = Field(ge=1)
    source_event_id: str | None = Field(default=None, max_length=100)
    confidence: float = Field(ge=0, le=1)
    status: Literal["UNMAPPED", "REVIEWED", "MAPPED", "DISMISSED"] = "UNMAPPED"
    schema_version: str = "unmapped-observation.v1"


class SemanticAtom(StrictModel):
    """Privacy-safe, independently verifiable meaning unit."""

    atom_id: str = Field(min_length=1, max_length=80)
    atom_class: str = Field(min_length=1, max_length=80)
    speaker: str = Field(min_length=1, max_length=80)
    subject: str | None = Field(default=None, max_length=120)
    predicate: str = Field(min_length=1, max_length=120)
    actor: str | None = Field(default=None, max_length=120)
    target: str | None = Field(default=None, max_length=120)
    object: str | None = Field(default=None, max_length=120)
    destination: str | None = Field(default=None, max_length=120)
    action_state: str | None = Field(default=None, max_length=40, pattern=r"^(MENTIONED|REQUESTED|INSTRUCTED|PLANNED|ATTEMPTED|REPORTED_ACTION|VERIFIED|COMPLETED|FAILED|CANCELLED|DENIED|UNKNOWN)$")
    modality: str | None = Field(default=None, max_length=40)
    polarity: str = Field(default="POSITIVE", max_length=40)
    claim_status: str = Field(default="UNVERIFIED", max_length=80)
    lexical_cues: list[str] = Field(default_factory=list, max_length=20)
    observed_terms: list[ObservedLexicalCue] = Field(default_factory=list, max_length=12)
    speech_form_codes: list[str] = Field(default_factory=list, max_length=8)
    speech_act: str | None = Field(default=None, max_length=60)
    directive_strength: str | None = Field(default=None, max_length=40)
    obligation: str | None = Field(default=None, max_length=40)
    urgency: str | None = Field(default=None, max_length=40)
    authority_pressure: str | None = Field(default=None, max_length=40)
    fear_pressure: str | None = Field(default=None, max_length=40)
    secrecy_pressure: str | None = Field(default=None, max_length=40)
    isolation_pressure: str | None = Field(default=None, max_length=40)
    financial_pressure: str | None = Field(default=None, max_length=40)
    repetition_pressure: str | None = Field(default=None, max_length=40)
    threat_type: str | None = Field(default=None, max_length=80)
    communication_control: str | None = Field(default=None, max_length=80)
    auth_secret_type: str | None = Field(default=None, max_length=60)
    amount_scope: str | None = Field(default=None, max_length=60)
    amount_value_krw: float | None = Field(default=None, ge=0)
    # Money-event semantics are kept separate so repeated amounts are not
    # collapsed into one generic total during projection.
    amount_role: Literal["TRANSFER_OUT", "REFUND_IN", "REQUESTED_AMOUNT", "CLAIMED_LOSS"] | None = None
    amount_direction: Literal["OUT", "IN", "REQUEST"] | None = None
    amount_event_id: str | None = Field(default=None, max_length=100)
    claimed_organization: str | None = Field(default=None, max_length=100)
    claimed_role: str | None = Field(default=None, max_length=100)
    claimed_purpose: str | None = Field(default=None, max_length=100)
    source_event_id: str | None = Field(default=None, max_length=80)
    source_turn_id: int = Field(ge=1)
    semantic_fingerprint: str = Field(min_length=1, max_length=128)
    schema_version: str = "semantic-atom.v1"


class SemanticRelation(StrictModel):
    """A relation between existing atoms; it never contains source text."""

    relation_id: str = Field(min_length=1, max_length=100)
    relation_type: Literal[
        "SUPPORTS", "JUSTIFIES", "REQUIRES", "CAUSES",
        "CONDITIONAL_ON", "CONTRADICTS",
    ]
    source_atom_id: str = Field(min_length=1, max_length=80)
    target_atom_id: str = Field(min_length=1, max_length=80)
    confidence: float = Field(ge=0, le=1)
    derivation: Literal["DETERMINISTIC_ATOM_RULE", "LLM_VERIFIED"] = "DETERMINISTIC_ATOM_RULE"
    schema_version: str = "semantic-relation.v1"


class ContextSignal(StrictModel):
    """A privacy-safe composite signal grounded in atom IDs."""

    signal_id: str = Field(min_length=1, max_length=100)
    signal_code: str = Field(min_length=1, max_length=120)
    atom_ids: list[str] = Field(min_length=2, max_length=50)
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    confidence: float = Field(ge=0, le=1)
    claim_status: Literal["CALLER_CLAIM", "CUSTOMER_REPORTED", "STAFF_REPORTED", "UNVERIFIED", "VERIFIED", "UNKNOWN"]
    visibility: Literal["BANK_INTERNAL", "CUSTOMER_SHARED", "SHARED"] = "BANK_INTERNAL"
    derivation: Literal["DETERMINISTIC_ATOM_RULE", "LLM_VERIFIED"] = "DETERMINISTIC_ATOM_RULE"
    schema_version: str = "context-signal.v1"


class SemanticAuditResult(StrictModel):
    """Privacy-safe audit outcome for structured diagnosis output."""

    schema_version: str = "semantic-audit.v1"
    audit_status: Literal["PASS", "NEEDS_REVIEW", "REEXTRACTION_REQUIRED"]
    overall_score: float = Field(ge=0, le=1)
    missing_features: list[str] = Field(default_factory=list, max_length=100)
    invalid_features: list[str] = Field(default_factory=list, max_length=100)
    privacy_violations: list[str] = Field(default_factory=list, max_length=100)
    unsupported_terms: list[str] = Field(default_factory=list, max_length=100)
    mixed_atoms: list[str] = Field(default_factory=list, max_length=100)
    orphan_references: list[str] = Field(default_factory=list, max_length=100)
    metrics: dict[str, float] = Field(default_factory=dict, max_length=20)
    recommended_action: Literal["NONE", "HUMAN_REVIEW", "TARGETED_REEXTRACTION"] = "NONE"


class SemanticAuditReview(StrictModel):
    """LLM reviewer output containing codes only; never source quotations."""

    schema_version: str = "semantic-audit-review.v1"
    review_status: Literal["PASS", "NEEDS_REVIEW", "REEXTRACTION_REQUIRED"]
    issue_codes: list[str] = Field(default_factory=list, max_length=100)
    missing_turns: list[int] = Field(default_factory=list, max_length=30)
    rationale_codes: list[str] = Field(default_factory=list, max_length=30)


class ConversationEpisode(StrictModel):
    episode_id: str = Field(min_length=1, max_length=100)
    start_turn: int = Field(ge=1)
    end_turn: int = Field(ge=1)
    atom_ids: list[str] = Field(min_length=1, max_length=100)
    episode_type: Literal["IDENTITY_CLAIM", "PRESSURE", "ACTION", "MIXED", "OTHER"]
    schema_version: str = "conversation-episode.v1"


class ActionGroup(StrictModel):
    group_id: str = Field(min_length=1, max_length=100)
    action_predicate: str = Field(min_length=1, max_length=120)
    atom_ids: list[str] = Field(min_length=1, max_length=100)
    action_states: list[str] = Field(min_length=1, max_length=10)
    target_codes: list[str] = Field(default_factory=list, max_length=20)
    schema_version: str = "action-group.v1"


class EntityReference(StrictModel):
    entity_id: str = Field(min_length=1, max_length=100)
    entity_code: str = Field(min_length=1, max_length=100)
    mention_roles: list[str] = Field(default_factory=list, max_length=20)
    atom_ids: list[str] = Field(min_length=1, max_length=100)
    source_turn_ids: list[int] = Field(min_length=1, max_length=100)
    schema_version: str = "entity-reference.v1"


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
    demands: list[str] = Field(default_factory=list)
    manipulation_tactics: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class CaseContextFeatures(StrictModel):
    """원문 없이 사건 서사를 재구성하기 위한 ML 독립 피처 묶음."""

    claimed_actor_types: list[str] = Field(default_factory=list)
    claim_codes: list[str] = Field(default_factory=list)
    requested_action_codes: list[str] = Field(default_factory=list)
    manipulation_tactic_codes: list[str] = Field(default_factory=list)
    exposure_risk_codes: list[str] = Field(default_factory=list)
    amount_values_krw: list[float] = Field(default_factory=list)
    requested_amount_values_krw: list[float] = Field(default_factory=list)
    chronology: list[str] = Field(default_factory=list)
    unknown_fields: list[str] = Field(default_factory=list)
    source: Literal["STRUCTURED_CONTEXT_FEATURES_ONLY"] = "STRUCTURED_CONTEXT_FEATURES_ONLY"
    schema_version: str = "case_context_features.v1"
    observations: list[dict[str, Any]] = Field(default_factory=list)
    extraction_method: Literal["EVENT_DERIVED", "LLM_INDEPENDENT"] = "EVENT_DERIVED"


class WindowAnalysisResult(StrictModel):
    turns: list[str]
    events: list[ExtractedEvent]
    windows: list[WindowResult]
    extractor_model: str
    warnings: list[str] = Field(default_factory=list)
    semantic_atoms: list[SemanticAtom] = Field(default_factory=list)


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
    case_context_features: CaseContextFeatures = Field(default_factory=CaseContextFeatures)
    semantic_atoms: list[SemanticAtom] = Field(default_factory=list)
    unmapped_observations: list[UnmappedObservation] = Field(default_factory=list)
    semantic_relations: list[SemanticRelation] = Field(default_factory=list)
    context_signals: list[ContextSignal] = Field(default_factory=list)
    conversation_episodes: list[ConversationEpisode] = Field(default_factory=list)
    action_groups: list[ActionGroup] = Field(default_factory=list)
    entity_registry: list[EntityReference] = Field(default_factory=list)
    semantic_audit: SemanticAuditResult | None = None
    semantic_audit_review: SemanticAuditReview | None = None
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
