"""LLM/Agent 없이 MVP 흐름을 연결하는 결정론적 AI skeleton."""
from __future__ import annotations

from contracts.ai_internal.mvp_workflow import (
    BriefUpdateResult, CaseBrief, CustomerAnswerResult, QuestionCandidate,
    QuestionPriority, ResolvedItem, TargetField, UnresolvedItem,
)
from contracts.diagnosis import DiagnosisResult


_QUESTIONS = {
    TargetField.TRANSFER_STATUS: (QuestionPriority.P0, "현재 상대방의 요구대로 실제 송금을 진행하셨나요?", "실제 피해 및 즉시 대응 필요 여부를 확인해야 합니다."),
    TargetField.PERSONAL_INFORMATION_EXPOSURE: (QuestionPriority.P0, "개인정보를 전달하셨나요?", "개인정보 노출 여부는 추가 보호 조치 판단에 필요합니다."),
    TargetField.AUTHENTICATION_INFORMATION_EXPOSURE: (QuestionPriority.P0, "인증번호나 비밀번호를 전달하셨나요?", "인증정보 노출 여부를 확인해야 합니다."),
    TargetField.TRANSFER_PURPOSE: (QuestionPriority.P1, "상대방은 어떤 이유로 자금 이동을 요구했나요?", "요구 맥락을 원문 근거와 함께 확인해야 합니다."),
    TargetField.CLAIMED_ORGANIZATION: (QuestionPriority.P1, "상대방은 어느 기관 소속이라고 주장했나요?", "사칭 주장 확인에 필요합니다."),
    TargetField.INCIDENT_CLAIM: (QuestionPriority.P1, "상대방은 어떤 사건이나 상황을 주장했나요?", "상대방 주장의 사실 확인 범위를 정하기 위해 필요합니다."),
}


class MvpWorkflowService:
    def build_brief(self, diagnosis: DiagnosisResult) -> CaseBrief:
        evidence = diagnosis.evidence
        impersonation = next((item.subtype for item in evidence if item.event_family == "IMPERSONATION"), None)
        transfer = next((item.text for item in evidence if item.event_family == "MONEY_MOVEMENT"), None)
        amount = float(diagnosis.features.get("requested_amount_max", 0) or 0) or None
        fields = [TargetField.TRANSFER_STATUS, TargetField.PERSONAL_INFORMATION_EXPOSURE, TargetField.AUTHENTICATION_INFORMATION_EXPOSURE]
        if transfer:
            fields.append(TargetField.TRANSFER_PURPOSE)
        if not impersonation:
            fields.append(TargetField.CLAIMED_ORGANIZATION)
        if not diagnosis.context.claims:
            fields.append(TargetField.INCIDENT_CLAIM)
        unresolved = [UnresolvedItem(target_field=f, description=_QUESTIONS[f][2], priority=_QUESTIONS[f][0]) for f in fields]
        return CaseBrief(summary=diagnosis.context.summary, incident_type=diagnosis.context.incident_type,
            risk_level=diagnosis.risk_level, risk_score=diagnosis.risk_score, impersonation_target=impersonation,
            claims=diagnosis.context.claims, transfer_context=transfer, mentioned_amount_krw=amount,
            risk_evidence=evidence, unresolved_items=unresolved, next_checks=diagnosis.context.recommended_next_steps)

    def recommend_questions(self, brief: CaseBrief) -> list[QuestionCandidate]:
        return [QuestionCandidate(question_id=f"q_{item.target_field.value}", priority=item.priority,
            target_field=item.target_field, question=_QUESTIONS[item.target_field][1], reason=item.description,
            evidence_refs=brief.risk_evidence) for item in brief.unresolved_items]

    def structure_answer(self, target_field: TargetField, raw_answer: str) -> CustomerAnswerResult:
        text = raw_answer.strip()
        normalized = text.replace(" ", "")
        value = None
        if target_field is TargetField.TRANSFER_STATUS:
            value = "NOT_TRANSFERRED" if any(x in normalized for x in ("안보냈", "송금하지않", "이체하지않")) else "TRANSFERRED" if any(x in normalized for x in ("보냈", "송금했", "이체했")) else None
        elif target_field in (TargetField.PERSONAL_INFORMATION_EXPOSURE, TargetField.AUTHENTICATION_INFORMATION_EXPOSURE):
            value = "NOT_EXPOSED" if any(x in normalized for x in ("제공하지않", "알려주지않")) else "EXPOSED" if any(x in normalized for x in ("제공했", "알려줬")) else None
        return CustomerAnswerResult(target_field=target_field, raw_answer=text, structured_value=value,
            confidence=0.95 if value else 0.0, unresolved=value is None, evidence_text=text,
            warnings=[] if value else ["답변이 불명확하여 담당자 확인이 필요합니다."])

    def update_brief(self, brief: CaseBrief, answer: CustomerAnswerResult) -> BriefUpdateResult:
        remaining = [item for item in brief.unresolved_items if item.target_field is not answer.target_field]
        resolved = [] if answer.unresolved or answer.structured_value is None else [ResolvedItem(target_field=answer.target_field, structured_value=answer.structured_value, evidence_text=answer.raw_answer)]
        summary = brief.summary if not resolved else f"{brief.summary} 고객 답변으로 {answer.target_field.value} 항목이 {answer.structured_value}로 확인되었습니다."
        return BriefUpdateResult(updated_summary=summary, resolved_items=resolved, unresolved_items=remaining if resolved else brief.unresolved_items,
            risk_evidence=brief.risk_evidence, counter_evidence=brief.counter_evidence, next_checks=brief.next_checks)
