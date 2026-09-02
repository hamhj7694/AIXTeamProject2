"""Structured Case Facts PoC contract.

This contract deliberately represents evidence-backed facts, not a UI-ready
summary.  It is independent from the existing CaseBrief production contract.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictContextFactsModel(BaseModel):
    """Reject unrecognised LLM keys instead of silently accepting them."""

    model_config = ConfigDict(extra="forbid")


class FactStatus(str, Enum):
    """Lifecycle labels; only a future non-LLM boundary may elevate a fact."""

    AI_EXTRACTED = "ai_extracted"
    HUMAN_CONFIRMED = "human_confirmed"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    UNRESOLVED = "unresolved"


class EvidenceProvenance(StrictContextFactsModel):
    """The source excerpt that supports one extracted value.

    ``source_ref`` and ``turn`` are optional because the PoC can receive one
    unsegmented excerpt.  No timestamp is modelled or invented at this stage.
    """

    evidence_text: str = Field(min_length=1)
    source_ref: str | None = Field(default=None, min_length=1)
    turn: int | None = Field(default=None, ge=1)

    @field_validator("evidence_text")
    @classmethod
    def evidence_text_must_contain_non_whitespace(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("evidence_text must contain non-whitespace characters")
        return value


class EvidenceBackedFact(StrictContextFactsModel):
    value: str = Field(min_length=1)
    evidence: EvidenceProvenance
    status: FactStatus = FactStatus.AI_EXTRACTED


class MentionedAmount(StrictContextFactsModel):
    amount_krw: int = Field(ge=0)
    evidence: EvidenceProvenance
    status: FactStatus = FactStatus.AI_EXTRACTED


class DemandFact(StrictContextFactsModel):
    action: str = Field(min_length=1)
    reason: str | None = None
    amount_krw: int | None = Field(default=None, ge=0)
    target: str | None = None
    evidence: EvidenceProvenance
    status: FactStatus = FactStatus.AI_EXTRACTED


class TransferContextFact(StrictContextFactsModel):
    """A transfer-related context, kept plural because one case can contain many."""

    value: str = Field(min_length=1)
    evidence: EvidenceProvenance
    status: FactStatus = FactStatus.AI_EXTRACTED


class UnresolvedItem(StrictContextFactsModel):
    description: str = Field(min_length=1)
    related_evidence: list[EvidenceProvenance] = Field(default_factory=list)


class StructuredCaseFacts(StrictContextFactsModel):
    """Reusable, evidence-backed semantic units extracted from one raw source."""

    schema_version: str = "structured_case_facts.v1"
    impersonated_entities: list[EvidenceBackedFact] = Field(default_factory=list)
    claims: list[EvidenceBackedFact] = Field(default_factory=list)
    demands: list[DemandFact] = Field(default_factory=list)
    mentioned_amounts: list[MentionedAmount] = Field(default_factory=list)
    pressure_signals: list[EvidenceBackedFact] = Field(default_factory=list)
    isolation_signals: list[EvidenceBackedFact] = Field(default_factory=list)
    app_installation_requests: list[EvidenceBackedFact] = Field(default_factory=list)
    credential_requests: list[EvidenceBackedFact] = Field(default_factory=list)
    personal_information_requests: list[EvidenceBackedFact] = Field(default_factory=list)
    transfer_context: list[TransferContextFact] = Field(default_factory=list)
    unresolved_items: list[UnresolvedItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
