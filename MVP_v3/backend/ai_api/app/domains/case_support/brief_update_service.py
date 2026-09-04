"""Apply a confirmed customer answer to an existing case brief.

This service deliberately updates only the answered field.  It does not
recalculate diagnosis risk or infer new facts from a customer's answer.
"""
from __future__ import annotations

from contracts.ai_internal.mvp_workflow import (
    BriefUpdateResult,
    CaseBrief,
    CustomerAnswerResult,
    ResolvedItem,
    TargetField,
)


class BriefUpdateService:
    """Deterministically produce a safe incremental brief update."""

    _NEXT_CHECK_MARKERS: dict[TargetField, tuple[str, ...]] = {
        TargetField.TRANSFER_STATUS: (
            "transfer_status", "transfer status", "송금", "이체", "입금",
        ),
        TargetField.TRANSFER_PURPOSE: (
            "transfer_purpose", "transfer purpose", "송금 목적", "이체 목적", "자금 이동",
        ),
        TargetField.CLAIMED_ORGANIZATION: (
            "claimed_organization", "claimed organization", "소속 기관", "기관 확인",
        ),
        TargetField.INCIDENT_CLAIM: (
            "incident_claim", "incident claim", "사건", "상황", "주장 내용",
        ),
        TargetField.PERSONAL_INFORMATION_EXPOSURE: (
            "personal_information_exposure",
            "personal information",
            "개인정보",
        ),
        TargetField.AUTHENTICATION_INFORMATION_EXPOSURE: (
            "authentication_information_exposure",
            "authentication information",
            "인증정보",
            "otp",
            "비밀번호",
        ),
    }

    def update(self, brief: CaseBrief, answer: CustomerAnswerResult) -> BriefUpdateResult:
        """Resolve a pending field only when the supplied answer is explicit.

        A structured value alone is not enough: the answer must be marked as
        resolved and the target must be an unresolved item in this brief.
        This prevents an answer from adding unsupported facts to a case.
        """
        is_pending = any(item.target_field == answer.target_field for item in brief.unresolved_items)
        is_confirmed = (
            is_pending
            and not answer.unresolved
            and bool(answer.structured_value and answer.structured_value.strip())
        )

        if not is_confirmed:
            return BriefUpdateResult(
                updated_summary=brief.summary,
                unresolved_items=list(brief.unresolved_items),
                risk_evidence=list(brief.risk_evidence),
                counter_evidence=list(brief.counter_evidence),
                next_checks=list(brief.next_checks),
            )

        structured_value = answer.structured_value.strip()
        evidence_text = (answer.evidence_text or "").strip() or answer.raw_answer
        unresolved_items = [
            item for item in brief.unresolved_items if item.target_field != answer.target_field
        ]
        next_checks = [
            check for check in brief.next_checks if not self._is_related_next_check(check, answer.target_field)
        ]

        return BriefUpdateResult(
            updated_summary=self._updated_summary(brief.summary, answer.target_field, structured_value),
            resolved_items=[
                ResolvedItem(
                    target_field=answer.target_field,
                    structured_value=structured_value,
                    evidence_text=evidence_text,
                )
            ],
            unresolved_items=unresolved_items,
            # Customer answers must not overwrite the diagnosis evidence or risk assessment.
            risk_evidence=list(brief.risk_evidence),
            counter_evidence=list(brief.counter_evidence),
            next_checks=next_checks,
        )

    def update_brief(self, brief: CaseBrief, answer: CustomerAnswerResult) -> BriefUpdateResult:
        """Compatibility-friendly explicit name for workflow integration."""
        return self.update(brief, answer)

    @classmethod
    def _is_related_next_check(cls, check: str, target_field: TargetField) -> bool:
        normalized = check.lower()
        return any(marker in normalized for marker in cls._NEXT_CHECK_MARKERS[target_field])

    @staticmethod
    def _updated_summary(summary: str, target_field: TargetField, structured_value: str) -> str:
        # The canonical structured value is retained verbatim to avoid semantic reinterpretation.
        update = f" Customer answer confirmed {target_field.value} as {structured_value}."
        return f"{summary.rstrip()}{update}".strip()
