"""Grounding checks for Case Briefs and customer-question candidates."""
from __future__ import annotations

from contracts.ai_internal.case_snapshot import CaseSnapshotAiInput, CaseSnapshotPresentation
from contracts.ai_internal.mvp_workflow import TargetField


_QUESTION_EVIDENCE_FAMILIES = {
    TargetField.TRANSFER_STATUS: {"MONEY_MOVEMENT"},
    TargetField.TRANSFER_PURPOSE: {"MONEY_MOVEMENT"},
    TargetField.CLAIMED_ORGANIZATION: {"IMPERSONATION"},
    TargetField.INCIDENT_CLAIM: {"IMPERSONATION", "PSY_STRATEGY"},
    TargetField.PERSONAL_INFORMATION_EXPOSURE: {"ACTION_REQUEST"},
    TargetField.AUTHENTICATION_INFORMATION_EXPOSURE: {"ACTION_REQUEST"},
    TargetField.REMOTE_CONTROL_APP: {"ACTION_REQUEST"},
}


def validate_case_support_grounding(
    presentation: CaseSnapshotPresentation, ai_input: CaseSnapshotAiInput,
) -> None:
    """Reject support output that invents evidence or asks outside unresolved scope."""
    brief = presentation.case_brief
    if brief is None:
        return
    diagnosis = ai_input.diagnosis
    diagnosis_evidence = {
        (item.turn, item.event_family, item.subtype, item.text)
        for item in (diagnosis.evidence if diagnosis else [])
    }
    for item in brief.risk_evidence:
        if (item.turn, item.event_family, item.subtype, item.text) not in diagnosis_evidence:
            raise ValueError("Case Brief가 진단 결과에 없는 근거를 포함했습니다.")

    unresolved = {item.target_field for item in brief.unresolved_items}
    for question in presentation.recommended_questions:
        if question.target_field not in unresolved:
            raise ValueError("확인 질문이 현재 미확인 항목에 연결되지 않았습니다.")
        allowed = _QUESTION_EVIDENCE_FAMILIES.get(question.target_field, set())
        for evidence in question.evidence_refs:
            if evidence.event_family not in allowed or (
                evidence.turn, evidence.event_family, evidence.subtype, evidence.text
            ) not in diagnosis_evidence:
                raise ValueError("확인 질문이 허용되지 않은 근거를 참조했습니다.")


def safe_question_evidence_count(presentation: CaseSnapshotPresentation) -> int:
    """Privacy-safe metric for audit/export without exposing source text."""
    return sum(len(item.evidence_refs) for item in presentation.recommended_questions)
