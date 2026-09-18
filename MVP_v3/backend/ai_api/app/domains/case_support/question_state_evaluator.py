"""B 내부 의미 판단 기반. 질문 추천/전송이나 Fact 변경은 수행하지 않는다."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from contracts.ai_internal.case_snapshot import (
    CaseSnapshotFact,
    CaseSnapshotQuestion,
    CaseSnapshotVerification,
)
from .verification_policy import VerificationResult


class QuestionSemanticState(str, Enum):
    UNRESOLVED = "UNRESOLVED"
    WAITING = "WAITING"
    CLEAR_CUSTOMER_STATEMENT = "CLEAR_CUSTOMER_STATEMENT"
    UNCERTAIN = "UNCERTAIN"
    CONFLICT = "CONFLICT"
    STAFF_CONFIRMED = "STAFF_CONFIRMED"
    VERIFIED = "VERIFIED"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True)
class QuestionStateEvaluation:
    state: QuestionSemanticState
    is_sufficient: bool
    # 의미적 보완 가능성일 뿐 즉시 재추천/queue 허용 여부가 아니다.
    allow_follow_up: bool


def _uncertain_answer(answer: str) -> bool:
    """typed uncertainty가 없을 때만 사용하는 제한된 문자열 fallback."""
    compact = re.sub(r"\s+", "", answer)
    return any(term in compact for term in (
        "기억이안나", "기억안나", "기억나지않", "모르겠", "잘모르",
        "확실하지않", "애매", "헷갈",
    ))


class QuestionStateEvaluator:
    """이미 연결된 단일 semantic 범위를 평가한다. 원문 전체의 NLU가 아니다.

    precedence: CONFLICT > VERIFIED > STAFF_CONFIRMED > UNCERTAIN >
    CLEAR_CUSTOMER_STATEMENT > SKIPPED > WAITING > UNRESOLVED.
    미해결 충돌은 과거 검증/직원 확인만으로 해소됐다고 가정하지 않는다.
    answer_text와 명시적 flags는 호출자가 현재 범위에 연결한 입력이다.
    Verification의 target/claim 문자열로 범위를 추측하지 않는다.
    """

    @staticmethod
    def evaluate(
        *,
        semantic_scope: str,
        question: CaseSnapshotQuestion | None = None,
        answer_text: str | None = None,
        is_uncertain: bool | None = None,
        has_conflict: bool = False,
        correction_needed: bool = False,
        fact: CaseSnapshotFact | None = None,
        verification: CaseSnapshotVerification | VerificationResult | None = None,
        verification_scope: str | None = None,
    ) -> QuestionStateEvaluation:
        if not semantic_scope.strip():
            raise ValueError("semantic_scope must be non-empty")
        current_question = question if question and question.target_field == semantic_scope else None
        answer = (answer_text if answer_text is not None else (
            current_question.answer_text if current_question else None
        ) or "").strip()
        lifecycle = current_question.status if current_question else None
        uncertain = is_uncertain if is_uncertain is not None else _uncertain_answer(answer)

        if has_conflict or correction_needed:
            state = QuestionSemanticState.CONFLICT
        elif (
            verification is not None
            and verification_scope == semantic_scope
            and verification.status == "COMPLETED"
            and (verification.result_summary or "").strip()
        ):
            state = QuestionSemanticState.VERIFIED
        elif fact and fact.field == semantic_scope and fact.status == "CONFIRMED" and fact.value.strip():
            state = QuestionSemanticState.STAFF_CONFIRMED
        elif uncertain:
            state = QuestionSemanticState.UNCERTAIN
        elif answer:
            # 비어 있지 않은 범위 연결 답변을 기본 문진의 진술로만 취급한다.
            # 여기서 긍정/부정 값이나 객관적 진실을 새로 추론하지 않는다.
            state = QuestionSemanticState.CLEAR_CUSTOMER_STATEMENT
        elif lifecycle == "SKIPPED":
            state = QuestionSemanticState.SKIPPED
        elif lifecycle in {"PENDING", "ASKED"}:
            state = QuestionSemanticState.WAITING
        else:
            state = QuestionSemanticState.UNRESOLVED

        sufficient = state in {
            QuestionSemanticState.CLEAR_CUSTOMER_STATEMENT,
            QuestionSemanticState.STAFF_CONFIRMED,
            QuestionSemanticState.VERIFIED,
        }
        follow_up = state in {
            QuestionSemanticState.UNRESOLVED,
            QuestionSemanticState.UNCERTAIN,
            QuestionSemanticState.CONFLICT,
        }
        return QuestionStateEvaluation(state, sufficient, follow_up)
