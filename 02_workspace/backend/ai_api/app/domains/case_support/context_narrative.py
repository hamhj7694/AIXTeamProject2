"""Deterministic, evidence-preserving narrative assembly for Structured Case Facts.

This module does not inspect raw text or invoke an LLM.  It only renders the
already validated values in ``StructuredCaseFacts`` into a human-readable
domain result.
"""
from __future__ import annotations

from typing import Iterable

from pydantic import Field

from .context_facts import (
    DemandFact,
    EvidenceBackedFact,
    EvidenceProvenance,
    MentionedAmount,
    StrictContextFactsModel,
    StructuredCaseFacts,
)


class ContextNarrativeResult(StrictContextFactsModel):
    """Narrative text and its separately traceable Structured Facts provenance."""

    schema_version: str = "context_narrative.v1"
    narrative: str
    used_fact_types: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceProvenance] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ContextNarrativeBuilder:
    """Build readable context without adding facts, risk decisions, or advice."""

    def build(self, facts: StructuredCaseFacts) -> ContextNarrativeResult:
        sentences: list[str] = []
        used_fact_types: list[str] = []
        evidence_refs: list[EvidenceProvenance] = []

        self._add_evidence_fact_sentence(
            sentences, used_fact_types, evidence_refs, "impersonated_entities",
            facts.impersonated_entities,
            "상대방은 다음 기관 또는 인물을 사칭한 것으로 구조화되었습니다: {values}.",
        )
        self._add_evidence_fact_sentence(
            sentences, used_fact_types, evidence_refs, "claims", facts.claims,
            "상대방의 주장: {values}.",
        )

        for demand in facts.demands:
            sentences.append(f"상대방의 요구 내용은 {self._describe_demand(demand)}입니다.")
            self._record("demands", [demand.evidence], used_fact_types, evidence_refs)

        if facts.mentioned_amounts:
            amounts = ", ".join(self._format_amount(item.amount_krw) for item in facts.mentioned_amounts)
            sentences.append(f"언급된 금액: {amounts}.")
            self._record(
                "mentioned_amounts", (item.evidence for item in facts.mentioned_amounts),
                used_fact_types, evidence_refs,
            )

        self._add_evidence_fact_sentence(
            sentences, used_fact_types, evidence_refs, "pressure_signals", facts.pressure_signals,
            "상대방 발화에서 구조화된 압박 관련 표현: {values}.",
        )
        self._add_evidence_fact_sentence(
            sentences, used_fact_types, evidence_refs, "isolation_signals", facts.isolation_signals,
            "상대방 발화에서 구조화된 고립 관련 표현: {values}.",
        )
        self._add_evidence_fact_sentence(
            sentences, used_fact_types, evidence_refs, "app_installation_requests",
            facts.app_installation_requests, "앱 설치 요청: {values}.",
        )
        self._add_evidence_fact_sentence(
            sentences, used_fact_types, evidence_refs, "credential_requests", facts.credential_requests,
            "인증정보 요청: {values}.",
        )
        self._add_evidence_fact_sentence(
            sentences, used_fact_types, evidence_refs, "personal_information_requests",
            facts.personal_information_requests, "개인정보 요청: {values}.",
        )
        self._add_evidence_fact_sentence(
            sentences, used_fact_types, evidence_refs, "transfer_context", facts.transfer_context,
            "송금 관련 맥락: {values}.",
        )

        if facts.unresolved_items:
            descriptions = "; ".join(item.description for item in facts.unresolved_items)
            sentences.append(f"아직 확인되지 않은 사항: {descriptions}.")
            self._record(
                "unresolved_items",
                (evidence for item in facts.unresolved_items for evidence in item.related_evidence),
                used_fact_types, evidence_refs,
            )

        if not sentences:
            sentences.append("현재 제공된 구조화 사실로는 사건 내용을 조립할 수 없습니다.")

        return ContextNarrativeResult(
            narrative=" ".join(sentences),
            used_fact_types=used_fact_types,
            evidence_refs=evidence_refs,
            warnings=list(facts.warnings),
        )

    def _add_evidence_fact_sentence(
        self,
        sentences: list[str],
        used_fact_types: list[str],
        evidence_refs: list[EvidenceProvenance],
        fact_type: str,
        facts: Iterable[EvidenceBackedFact],
        template: str,
    ) -> None:
        values_and_evidence = list(facts)
        if not values_and_evidence:
            return
        values = "; ".join(item.value for item in values_and_evidence)
        sentences.append(template.format(values=values))
        self._record(fact_type, (item.evidence for item in values_and_evidence), used_fact_types, evidence_refs)

    @staticmethod
    def _describe_demand(demand: DemandFact) -> str:
        parts = [demand.action]
        amount_krw = demand.amount_krw
        target = demand.target
        reason = demand.reason
        if amount_krw is not None:
            parts.append(f"금액 {ContextNarrativeBuilder._format_amount(amount_krw)}")
        if target:
            parts.append(f"대상 {target}")
        if reason:
            parts.append(f"사유 {reason}")
        return ", ".join(parts)

    @staticmethod
    def _format_amount(amount_krw: int) -> str:
        return f"{amount_krw:,}원"

    @staticmethod
    def _record(
        fact_type: str,
        evidence: Iterable[EvidenceProvenance],
        used_fact_types: list[str],
        evidence_refs: list[EvidenceProvenance],
    ) -> None:
        if fact_type not in used_fact_types:
            used_fact_types.append(fact_type)
        for item in evidence:
            if item not in evidence_refs:
                evidence_refs.append(item)
