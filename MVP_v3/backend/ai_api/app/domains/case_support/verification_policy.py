"""B-owned distinction and semantic mapping for verification recommendations/results."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import Field

from contracts.diagnosis import StrictModel


class VerificationSubject(str, Enum):
    UNKNOWN = "UNKNOWN"
    ORGANIZATION = "ORGANIZATION"
    CONTACT = "CONTACT"


class VerificationRecommendation(StrictModel):
    kind: Literal["RECOMMENDATION"] = "RECOMMENDATION"
    claim: str = Field(min_length=1)
    target: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class VerificationResult(StrictModel):
    kind: Literal["RESULT"] = "RESULT"
    verification_task_id: str = Field(min_length=1)
    version: int = Field(ge=1)
    claim: str = Field(min_length=1)
    target: str = Field(min_length=1)
    status: Literal["PENDING", "IN_PROGRESS", "COMPLETED", "ON_HOLD", "FAILED"]
    result_summary: str | None = None
    subject: VerificationSubject = VerificationSubject.UNKNOWN


class VerificationSemanticProposal(StrictModel):
    client_request_id: str
    semantic_key: Literal["offender.claimed_organization", "offender.contact"]
    display_label: str
    value: dict[str, str]
    display_value: str
    evidence_refs: list[dict[str, str | int]]
    visibility: Literal["BANK_INTERNAL"] = "BANK_INTERNAL"
    confidence: float = Field(default=1.0, ge=0, le=1)


class VerificationSemanticMapper:
    """Create a proposal only when an existing semantic key is a conservative fit."""

    _CONTACT_MARKERS = ("전화번호", "연락처", "발신번호", "문자번호", "전화", "발신", "연락")
    _ORGANIZATION_MARKERS = (
        "기관", "조직", "소속", "검찰", "지검", "경찰", "은행", "금융감독원", "금감원", "공단", "관공서",
    )

    @classmethod
    def map_result(cls, result: VerificationResult) -> VerificationSemanticProposal | None:
        if result.kind != "RESULT" or result.status != "COMPLETED" or not (result.result_summary or "").strip():
            return None
        subject = result.subject
        if subject is VerificationSubject.UNKNOWN:
            subject = cls._infer_subject(result.target)
        mapping = {
            VerificationSubject.ORGANIZATION: (
                "offender.claimed_organization", "사칭 기관", "name",
            ),
            VerificationSubject.CONTACT: (
                "offender.contact", "상대방 연락처", "value",
            ),
        }.get(subject)
        if mapping is None:
            return None
        semantic_key, display_label, value_key = mapping
        target = " ".join(result.target.split())
        summary = " ".join((result.result_summary or "").split())
        return VerificationSemanticProposal(
            client_request_id=f"verification-result-{result.verification_task_id}-{result.version}",
            semantic_key=semantic_key,
            display_label=display_label,
            # 기존 semantic Fact validator가 요구하는 대표 값 키를 유지한다.
            value={value_key: target, "verification_result": summary},
            display_value=f"{target}: {summary}",
            evidence_refs=[{
                "type": "VERIFICATION_RESULT", "id": result.verification_task_id, "revision": result.version,
            }],
        )

    @classmethod
    def _infer_subject(cls, target: str) -> VerificationSubject:
        compact = "".join(target.split()).casefold()
        if any(marker in compact for marker in cls._CONTACT_MARKERS):
            return VerificationSubject.CONTACT
        if any(marker in compact for marker in cls._ORGANIZATION_MARKERS):
            return VerificationSubject.ORGANIZATION
        return VerificationSubject.UNKNOWN
