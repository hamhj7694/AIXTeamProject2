"""Validation boundary for a future Structured Case Facts LLM extractor.

No model client is called here.  A caller supplies an LLM JSON response, and
this module accepts it only when its contract is valid and every provenance
excerpt is present in the raw text supplied for this extraction.
"""
from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from .context_facts import (
    EvidenceProvenance,
    FactStatus,
    MentionedAmount,
    StructuredCaseFacts,
)


class ContextFactsValidationError(ValueError):
    """Raised when a proposed fact is unsupported by the supplied raw text."""


class StructuredCaseFactsParser:
    """Parse and safely validate one future LLM structured-output response."""

    def parse(
        self,
        raw_text: str,
        llm_output: str | Mapping[str, Any],
        *,
        source_ref: str | None = None,
    ) -> StructuredCaseFacts:
        if not raw_text or not raw_text.strip():
            raise ContextFactsValidationError("raw_text must not be empty")

        payload = self._load_payload(llm_output)
        try:
            facts = StructuredCaseFacts.model_validate(payload)
        except ValidationError as exc:
            raise ContextFactsValidationError(f"invalid structured case facts: {exc}") from exc

        facts = self._normalize_llm_fact_statuses(facts)
        facts = self._remove_polarity_conflicts(facts)
        facts = self._validate_amounts(facts)

        evidence_items = self._all_evidence(facts)
        normalized_source = self._normalize(raw_text)
        for evidence in evidence_items:
            if evidence.turn is not None:
                # A plain excerpt has no trustworthy turn segmentation.  Do not
                # let an LLM turn an excerpt position into a call-turn fact.
                raise ContextFactsValidationError("turn is not available for an unsegmented raw_text input")
            if source_ref is None and evidence.source_ref is not None:
                raise ContextFactsValidationError("source_ref was supplied in output but not extraction input")
            if source_ref is not None and evidence.source_ref not in (None, source_ref):
                raise ContextFactsValidationError("evidence source_ref does not match extraction source_ref")
            if self._normalize(evidence.evidence_text) not in normalized_source:
                raise ContextFactsValidationError(
                    "evidence_text is not present in raw_text; unsupported fact rejected"
                )

        # Input-owned provenance is applied after validation; the LLM does not
        # get to invent a source identity.
        if source_ref is not None:
            facts = self._apply_source_ref(facts, source_ref)
        return facts

    @staticmethod
    def _normalize_llm_fact_statuses(facts: StructuredCaseFacts) -> StructuredCaseFacts:
        """LLM output is a proposal, never a human or external verification result."""
        warnings = list(facts.warnings)
        updates: dict[str, object] = {}
        for field_name in (
            "impersonated_entities", "claims", "demands", "mentioned_amounts", "pressure_signals",
            "isolation_signals", "app_installation_requests", "credential_requests",
            "personal_information_requests", "transfer_context",
        ):
            normalized_items = []
            for item in getattr(facts, field_name):
                if item.status is not FactStatus.AI_EXTRACTED:
                    warnings.append(f"{field_name} status was normalized to ai_extracted")
                normalized_items.append(item.model_copy(update={"status": FactStatus.AI_EXTRACTED}))
            updates[field_name] = normalized_items
        updates["warnings"] = warnings
        return facts.model_copy(update=updates)

    @staticmethod
    def _remove_polarity_conflicts(facts: StructuredCaseFacts) -> StructuredCaseFacts:
        """Keep explicit requests even when the same evidence says they were not carried out."""
        warnings = list(facts.warnings)
        updates: dict[str, object] = {}

        demands = []
        for item in facts.demands:
            evidence_text = item.evidence.evidence_text
            if (
                not StructuredCaseFactsParser._has_transfer_request(evidence_text)
                and StructuredCaseFactsParser._has_negative_transfer(evidence_text)
            ):
                warnings.append("demand was rejected because its evidence explicitly negates a transfer")
            else:
                demands.append(item)
        updates["demands"] = demands

        impersonated_entities = []
        for item in facts.impersonated_entities:
            if StructuredCaseFactsParser._explicitly_negates_value(item.value, item.evidence.evidence_text):
                warnings.append("impersonated entity was rejected because its evidence explicitly negates it")
            else:
                impersonated_entities.append(item)
        updates["impersonated_entities"] = impersonated_entities

        app_requests = []
        for item in facts.app_installation_requests:
            evidence_text = item.evidence.evidence_text
            if StructuredCaseFactsParser._has_app_installation_safety_prohibition(evidence_text):
                warnings.append("app installation request was rejected because its evidence is a safety prohibition")
            elif (
                not StructuredCaseFactsParser._has_app_installation_request(evidence_text)
                and StructuredCaseFactsParser._has_negative_installation(evidence_text)
            ):
                warnings.append("app installation request was rejected because its evidence explicitly denies installation")
            else:
                app_requests.append(item)
        updates["app_installation_requests"] = app_requests

        credential_requests = []
        for item in facts.credential_requests:
            evidence_text = item.evidence.evidence_text
            if (
                not StructuredCaseFactsParser._has_credential_request(evidence_text)
                and StructuredCaseFactsParser._has_negative_credential_sharing(evidence_text)
            ):
                warnings.append("credential request was rejected because its evidence explicitly denies sharing")
            else:
                credential_requests.append(item)
        updates["credential_requests"] = credential_requests

        updates["warnings"] = warnings
        return facts.model_copy(update=updates)

    @staticmethod
    def _validate_amounts(facts: StructuredCaseFacts) -> StructuredCaseFacts:
        """Keep an otherwise supported demand but never retain an unsupported amount."""
        warnings = list(facts.warnings)
        demands = []
        for item in facts.demands:
            if item.amount_krw is not None and not StructuredCaseFactsParser._amount_in_evidence(
                item.amount_krw, item.evidence.evidence_text,
            ):
                warnings.append("demand amount_krw was removed because it is absent from its evidence")
                demands.append(item.model_copy(update={"amount_krw": None}))
            else:
                demands.append(item)

        amounts: list[MentionedAmount] = []
        for item in facts.mentioned_amounts:
            if StructuredCaseFactsParser._amount_in_evidence(item.amount_krw, item.evidence.evidence_text):
                amounts.append(item)
            else:
                warnings.append("mentioned amount was rejected because it is absent from its evidence")
        return facts.model_copy(update={"demands": demands, "mentioned_amounts": amounts, "warnings": warnings})

    @staticmethod
    def _has_negative_transfer(text: str) -> bool:
        return bool(re.search(r"(?:송금|이체|보내).{0,12}(?:지\s*마|지\s*않|하지\s*마|하지\s*않|않았|못했|금지)", text))

    @staticmethod
    def _has_transfer_request(text: str) -> bool:
        return bool(re.search(r"(?:송금|이체)(?:하라고|하라|하세요|하십시오|해라|해주세요)|보내(?:라고|라|세요|십시오|주세요)", text))

    @staticmethod
    def _explicitly_negates_value(value: str, text: str) -> bool:
        return bool(re.search(rf"{re.escape(value)}(?:이|가)?\s*아니", text))

    @staticmethod
    def _has_negative_installation(text: str) -> bool:
        return bool(re.search(r"설치.{0,8}(?:하지\s*마|하지\s*않|하지\s*못|지\s*마|지\s*않|지\s*못|않았|못했)", text))

    @staticmethod
    def _has_app_installation_request(text: str) -> bool:
        return bool(re.search(r"설치(?:하라고|하라|하세요|하십시오|해라|해주세요)", text))

    @staticmethod
    def _has_app_installation_safety_prohibition(text: str) -> bool:
        """Handle only explicit prevention guidance, not a customer's non-installation."""
        return bool(re.search(r"설치하지\s*(?:말라고|마세요|말라)|설치하면\s*안\s*(?:됩니다|돼요)", text))

    @staticmethod
    def _has_negative_credential_sharing(text: str) -> bool:
        return bool(re.search(r"(?:OTP|인증번호|비밀번호).{0,16}(?:알려주지\s*마|알려주지\s*않|제공하지\s*마|제공하지\s*않|입력하지\s*마|입력하지\s*않|공유하지\s*마|공유하지\s*않|주지\s*마|주지\s*않)", text, re.IGNORECASE))

    @staticmethod
    def _has_credential_request(text: str) -> bool:
        return bool(re.search(r"(?:알려달라고|알려달라|알려주세요|알려주(?:라고|라|세요)|제공(?:해달라고|해달라|해주세요)|입력(?:하라고|하라|하세요))", text))

    @staticmethod
    def _amount_in_evidence(amount_krw: int, evidence_text: str) -> bool:
        compact = re.sub(r"[\s,]", "", evidence_text)
        if f"{amount_krw}원" in compact:
            return True
        return amount_krw % 10_000 == 0 and f"{amount_krw // 10_000}만원" in compact

    @staticmethod
    def _load_payload(llm_output: str | Mapping[str, Any]) -> Mapping[str, Any]:
        if isinstance(llm_output, str):
            try:
                llm_output = json.loads(llm_output)
            except json.JSONDecodeError as exc:
                raise ContextFactsValidationError("LLM output is not valid JSON") from exc
        if not isinstance(llm_output, Mapping):
            raise ContextFactsValidationError("LLM output must be a JSON object")
        return llm_output

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.split())

    @staticmethod
    def _all_evidence(facts: StructuredCaseFacts) -> list[EvidenceProvenance]:
        evidence: list[EvidenceProvenance] = []
        for field_name in (
            "impersonated_entities", "claims", "pressure_signals", "isolation_signals",
            "app_installation_requests", "credential_requests", "personal_information_requests",
            "transfer_context",
        ):
            evidence.extend(item.evidence for item in getattr(facts, field_name))
        evidence.extend(item.evidence for item in facts.demands)
        evidence.extend(item.evidence for item in facts.mentioned_amounts)
        evidence.extend(
            item_evidence
            for unresolved in facts.unresolved_items
            for item_evidence in unresolved.related_evidence
        )
        return evidence

    @staticmethod
    def _apply_source_ref(facts: StructuredCaseFacts, source_ref: str) -> StructuredCaseFacts:
        payload = facts.model_dump()

        def set_source(evidence: dict[str, Any]) -> None:
            evidence["source_ref"] = source_ref

        for field_name in (
            "impersonated_entities", "claims", "pressure_signals", "isolation_signals",
            "app_installation_requests", "credential_requests", "personal_information_requests",
            "transfer_context",
        ):
            for item in payload[field_name]:
                set_source(item["evidence"])
        for item in payload["demands"] + payload["mentioned_amounts"]:
            set_source(item["evidence"])
        for unresolved in payload["unresolved_items"]:
            for evidence in unresolved["related_evidence"]:
                set_source(evidence)
        return StructuredCaseFacts.model_validate(payload)
