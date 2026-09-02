"""CaseBrief의 미확인 항목을 담당자 검토용 질문 후보로 변환한다."""
from __future__ import annotations

from contracts.ai_internal.mvp_workflow import (
    CaseBrief,
    QuestionCandidate,
    QuestionPriority,
    TargetField,
)
from contracts.diagnosis import Evidence

from .question_prompt import QUESTION_PROMPT_VERSION


_QUESTION_SPECS: dict[TargetField, tuple[QuestionPriority, str, str, tuple[str, ...]]] = {
    TargetField.TRANSFER_STATUS: (
        QuestionPriority.P0,
        "상대방의 요구대로 실제로 송금하거나 이체하셨나요?",
        "실제 송금 여부는 즉시 대응 판단에 필요합니다.",
        ("MONEY_MOVEMENT",),
    ),
    TargetField.PERSONAL_INFORMATION_EXPOSURE: (
        QuestionPriority.P0,
        "주민등록번호나 계좌번호 등 개인정보를 제공하셨나요?",
        "개인정보 노출 여부는 추가 보호 조치 판단에 필요합니다.",
        ("ACTION_REQUEST",),
    ),
    TargetField.AUTHENTICATION_INFORMATION_EXPOSURE: (
        QuestionPriority.P0,
        "인증번호, 비밀번호 또는 OTP를 제공하셨나요?",
        "인증정보 노출 여부는 계정 보호 판단에 필요합니다.",
        ("ACTION_REQUEST",),
    ),
    TargetField.TRANSFER_PURPOSE: (
        QuestionPriority.P1,
        "상대방은 어떤 이유로 송금이나 자금 이동을 요구했나요?",
        "자금 이동 요구의 맥락을 확인하는 데 필요합니다.",
        ("MONEY_MOVEMENT",),
    ),
    TargetField.CLAIMED_ORGANIZATION: (
        QuestionPriority.P1,
        "상대방은 어느 기관이나 회사 소속이라고 말했나요?",
        "상대방의 소속 주장 확인에 필요합니다.",
        ("IMPERSONATION",),
    ),
    TargetField.INCIDENT_CLAIM: (
        QuestionPriority.P1,
        "상대방은 어떤 사건이나 문제가 발생했다고 말했나요?",
        "상대방 주장 내용을 확인하는 데 필요합니다.",
        ("IMPERSONATION", "PSY_STRATEGY"),
    ),
}


class QuestionIntelligenceService:
    """질문을 자동 전송하지 않고 ``QuestionCandidate``만 반환한다."""

    prompt_version = QUESTION_PROMPT_VERSION

    def recommend_questions(self, brief: CaseBrief) -> list[QuestionCandidate]:
        """unresolved_items만 사용해 중복 없는 P0/P1 후보를 만든다."""
        candidates: list[QuestionCandidate] = []
        seen_fields: set[TargetField] = set()

        for item in brief.unresolved_items:
            if item.target_field in seen_fields:
                continue
            spec = _QUESTION_SPECS.get(item.target_field)
            if spec is None:
                continue
            seen_fields.add(item.target_field)
            priority, question, default_reason, event_families = spec
            candidates.append(
                QuestionCandidate(
                    question_id=f"q_{item.target_field.value}",
                    priority=priority,
                    target_field=item.target_field,
                    question=question,
                    # Brief가 전달한 미확인 사유를 우선 보존한다.
                    reason=item.description.strip() or default_reason,
                    evidence_refs=self._select_evidence(brief.risk_evidence, event_families),
                )
            )

        return sorted(candidates, key=lambda item: (self._priority_order(item.priority), item.question_id))

    @staticmethod
    def _select_evidence(evidence: list[Evidence], event_families: tuple[str, ...]) -> list[Evidence]:
        return [item for item in evidence if item.event_family in event_families]

    @staticmethod
    def _priority_order(priority: QuestionPriority) -> int:
        return {QuestionPriority.P0: 0, QuestionPriority.P1: 1, QuestionPriority.P2: 2}[priority]
