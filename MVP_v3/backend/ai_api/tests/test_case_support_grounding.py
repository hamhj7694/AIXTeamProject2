from __future__ import annotations

import pytest
from ai_api.app.domains.case_support.grounding import validate_case_support_grounding
from contracts.ai_internal.case_snapshot import CaseSnapshotAiInput, CaseSnapshotPresentation
from contracts.ai_internal.mvp_workflow import CaseBrief, QuestionCandidate, QuestionPriority, TargetField, UnresolvedItem
from contracts.diagnosis import Evidence, RiskLevel


def _input() -> CaseSnapshotAiInput:
    evidence = Evidence(turn=1, event_family="IMPERSONATION", subtype="POLICE", text="기관 사칭 정황")
    return CaseSnapshotAiInput(case_id="VP-GROUND", diagnosis={
        "risk_level": "HIGH", "risk_score": 90, "model_label": "PHISHING",
        "context": {"summary": "기관 사칭", "incident_type": "사기", "confidence": 0.9},
        "events": [], "windows": [], "evidence": [evidence], "features": {}, "model_metadata": {}, "confidence": 0.9,
    })


def _brief() -> CaseBrief:
    return CaseBrief(summary="기관 사칭 정황", incident_type="사기", risk_level=RiskLevel.HIGH, risk_score=90,
                     unresolved_items=[UnresolvedItem(target_field=TargetField.CLAIMED_ORGANIZATION, description="확인 필요", priority=QuestionPriority.P1)])


def test_brief_and_question_evidence_must_come_from_diagnosis() -> None:
    source = _input()
    evidence = source.diagnosis.evidence[0]
    question = QuestionCandidate(question_id="q", priority=QuestionPriority.P1,
        target_field=TargetField.CLAIMED_ORGANIZATION, question="어느 기관이라고 했나요?", reason="확인 필요",
        evidence_refs=[evidence])
    presentation = CaseSnapshotPresentation(case_id="VP-GROUND", case_brief=_brief(), recommended_questions=[question])
    validate_case_support_grounding(presentation, source)


def test_question_cannot_reference_an_unrelated_event_family() -> None:
    source = _input()
    evidence = Evidence(turn=1, event_family="MONEY_MOVEMENT", subtype="TRANSFER", text="송금 요구")
    question = QuestionCandidate(question_id="q", priority=QuestionPriority.P1,
        target_field=TargetField.CLAIMED_ORGANIZATION, question="어느 기관이라고 했나요?", reason="확인 필요",
        evidence_refs=[evidence])
    presentation = CaseSnapshotPresentation(case_id="VP-GROUND", case_brief=_brief(), recommended_questions=[question])
    with pytest.raises(ValueError, match="허용되지 않은 근거"):
        validate_case_support_grounding(presentation, source)
