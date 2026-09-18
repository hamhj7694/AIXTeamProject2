"""B-owned normalization rules for deterministic and LLM question proposals."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal, Mapping

from pydantic import Field

from contracts.diagnosis import StrictModel
from contracts.ai_internal.mvp_workflow import QuestionRecommendationContext

from .question_state_evaluator import QuestionSemanticState, QuestionStateEvaluation, QuestionStateEvaluator


@dataclass(frozen=True)
class QuestionEligibility:
    evaluation: QuestionStateEvaluation
    allow_basic_question: bool
    allow_follow_up: bool
    suppression_reason: str | None


def question_eligibility(
    evaluation: QuestionStateEvaluation, *, has_active_question: bool = False,
    has_skipped_question: bool = False, has_answered_question: bool = False,
    has_confirmed_history: bool = False,
) -> QuestionEligibility:
    """의미 상태를 추천 정책으로 변환한다. follow-up은 전송 허가가 아니다."""
    if has_active_question:
        return QuestionEligibility(evaluation, False, False, "활성 질문의 답변을 기다리고 있습니다.")
    if has_skipped_question and not evaluation.is_sufficient:
        return QuestionEligibility(evaluation, False, False, "건너뛴 질문은 즉시 다시 추천하지 않습니다.")
    basic = evaluation.state == QuestionSemanticState.UNRESOLVED and not (has_answered_question or has_confirmed_history)
    # 답변 내용이나 current 관계가 없는 이력도 충분성으로 승격하지 않는다.
    # 기본 질문 반복은 막되, 의미적으로 부족한 상태의 보완 가능성은 유지한다.
    reason = None if basic else f"동일 기본 질문 억제: {evaluation.state.value}"
    if has_confirmed_history and not evaluation.is_sufficient:
        reason = "확인 이력의 원근거 연결이 필요합니다. 기본 질문은 반복하지 않습니다."
    return QuestionEligibility(evaluation, basic, evaluation.allow_follow_up, reason)


def question_eligibility_from_context(
    scope: str, question_id: str, context: QuestionRecommendationContext,
) -> QuestionEligibility:
    """원답변이 없는 기존 호출자도 이력을 충분성으로 승격하지 않고 중복만 억제한다."""
    return question_eligibility(
        QuestionStateEvaluator.evaluate(semantic_scope=scope),
        has_active_question=scope in context.pending_question_fields,
        has_answered_question=scope in context.answered_question_fields or context.has_answered_question(question_id),
        has_confirmed_history=scope in context.confirmed_fields,
    )


def dynamic_follow_up_allowed(eligibility: QuestionEligibility) -> bool:
    """P3-3 production 입력에는 conflict 관계가 없어 UNCERTAIN 보완만 연결한다."""
    return eligibility.allow_follow_up and eligibility.evaluation.state == QuestionSemanticState.UNCERTAIN


class QuestionSource(str, Enum):
    DETERMINISTIC = "DETERMINISTIC"
    LLM = "LLM"


# 목적은 서버가 scope별로 제한한다. 새로운 public purpose enum을 만들지 않는다.
FOLLOW_UP_PURPOSES = {
    "transfer_status": ("은행 앱·거래내역·거래 알림에서 실제 이체 기록 확인", ("거래내역", "거래알림", "문자알림", "은행앱", "이체내역")),
    "transfer_purpose": ("당시 대화나 메시지 기록에서 요구한 송금 명목 확인", ("대화기록", "메시지", "문자", "통화기록")),
    "claimed_organization": ("당시 메시지·통화 기록에서 상대방이 주장한 기관명 확인", ("메시지", "문자", "통화기록", "대화기록")),
    "incident_claim": ("당시 메시지·대화 기록에서 주장한 사건 내용 확인", ("메시지", "문자", "대화기록", "통화기록")),
    "personal_information_exposure": ("당시 대화나 전송 기록에서 개인정보 전달 행동 확인; 실제 값 요구 금지", ("메시지", "전송기록", "대화기록")),
    "authentication_information_exposure": ("인증번호를 읽어주거나 메시지로 보낸 행동의 기억 확인; 실제 값 요구 금지", ("읽어", "메시지", "전송기록")),
    "remote_control_app": ("기기의 설치 앱 목록·설치 기록에서 해당 앱 존재 확인; 설치 지시 금지", ("앱목록", "설치기록", "설치된앱")),
}


def validate_follow_up_question(raw: Mapping[str, Any], parent: Any) -> NormalizedQuestion:
    """Eligibility와 별개로 허용한 다음 확인 행동을 담았는지 좁게 검사한다."""
    normalized = normalize_question(raw, source=QuestionSource.LLM)
    from contracts.question_target import decode_follow_up_target
    target = decode_follow_up_target(normalized.target_field)
    if not target.is_follow_up or target.parent_question_id != parent.question_id or target.canonical_scope != parent.target_field:
        raise ValueError("follow-up parent/scope mismatch")
    compact = re.sub(r"\s+", "", normalized.question_text).casefold()
    previous = re.sub(r"\s+", "", parent.question_text).casefold()
    markers = FOLLOW_UP_PURPOSES[target.canonical_scope][1]
    if compact == previous or not any(marker in compact for marker in markers) or not any(
        marker in compact for marker in ("확인", "기억", "살펴", "조회")
    ):
        raise ValueError("follow-up must request an evidence check, not repeat the basic question")
    # 설명도 고객에게 전달되는 텍스트이므로 동일 안전 기준으로 검증한다.
    _reject_unsafe_question(normalized.customer_explanation or "", [])
    customer_text = re.sub(r"\s+", "", " ".join([
        normalized.question_text, normalized.customer_explanation or "", *normalized.options,
    ])).casefold()
    if any(term in customer_text for term in ("설치하세요", "설치해", "다운로드하", "깔아주세요")):
        raise ValueError("follow-up must not instruct app installation")
    return normalized


class NormalizedQuestion(StrictModel):
    question_id: str
    target_field: str
    question_text: str
    reason: str
    priority: Literal["P0", "P1", "P2"]
    options: list[str] = Field(default_factory=list, max_length=8)
    customer_explanation: str | None = None
    answer_mode: Literal["SINGLE_CHOICE", "TEXT", "CHOICE_OR_TEXT"] = "CHOICE_OR_TEXT"
    allow_free_text: bool = True
    allow_multi_select: bool = False
    source: QuestionSource


def _clean_required(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return " ".join(value.split())


def _normalize_options(raw_options: Any) -> list[str]:
    if raw_options is None:
        return []
    if not isinstance(raw_options, (list, tuple)):
        raise ValueError("options must be a list")
    normalized: list[str] = []
    seen: set[str] = set()
    for option in raw_options:
        if not isinstance(option, str):
            raise ValueError("each option must be a string")
        label = " ".join(option.split())
        if not label:
            continue
        dedupe_key = label.casefold()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        normalized.append(label)
    if len(normalized) > 8:
        raise ValueError("a question may contain at most 8 unique options")
    return normalized


def _read_bool(raw: Mapping[str, Any], field: str, default: bool) -> bool:
    value = raw.get(field, default)
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be a boolean")
    return value


def _reject_unsafe_question(question_text: str, options: list[str]) -> None:
    combined = re.sub(r"\s+", "", " ".join([question_text, *options])).casefold()
    secrets = ("비밀번호", "패스워드", "pin", "otp", "인증번호", "보안코드", "주민등록번호")
    value_requests = ("입력", "적어", "써", "말해", "알려", "보내", "무엇", "뭔가", "몇번")
    if any(term in combined for term in secrets) and any(term in combined for term in value_requests):
        raise ValueError("a question must not request a sensitive value")
    money_actions = ("송금", "이체", "결제", "입금")
    action_requests = ("하세요", "해주세요", "진행하", "보내세요", "실행하")
    if any(term in combined for term in money_actions) and any(term in combined for term in action_requests):
        raise ValueError("a question must not instruct a customer to move money")


def normalize_question(
    raw: Mapping[str, Any], *, source: QuestionSource,
) -> NormalizedQuestion:
    """Normalize one proposal without changing the shared Question contracts."""
    question_text = _clean_required(raw.get("question_text"), "question_text")
    options = _normalize_options(raw.get("options", []))
    answer_mode = str(raw.get("answer_mode") or "CHOICE_OR_TEXT").strip().upper()
    if answer_mode not in {"SINGLE_CHOICE", "TEXT", "CHOICE_OR_TEXT"}:
        raise ValueError("unsupported answer_mode")

    allow_free_text = _read_bool(raw, "allow_free_text", True)
    allow_multi_select = _read_bool(raw, "allow_multi_select", False)
    if answer_mode == "TEXT":
        options = []
        allow_multi_select = False
        allow_free_text = True
    elif not options and allow_free_text:
        # A choice mode without choices is represented as a plain text answer.
        answer_mode = "TEXT"
        allow_multi_select = False
    elif not options:
        raise ValueError("a choice question requires at least one option")
    if allow_multi_select and len(options) < 2:
        raise ValueError("a multi-select question requires at least two unique options")

    _reject_unsafe_question(question_text, options)
    explanation = raw.get("customer_explanation")
    if explanation is not None:
        explanation = " ".join(str(explanation).split()) or None
    priority = str(raw.get("priority") or "P1").strip().upper()
    if priority not in {"P0", "P1", "P2"}:
        raise ValueError("unsupported priority")
    return NormalizedQuestion(
        question_id=_clean_required(raw.get("question_id"), "question_id"),
        target_field=_clean_required(raw.get("target_field"), "target_field"),
        question_text=question_text,
        reason=_clean_required(raw.get("reason"), "reason"),
        priority=priority,
        options=options,
        customer_explanation=explanation,
        answer_mode=answer_mode,
        allow_free_text=allow_free_text,
        allow_multi_select=allow_multi_select,
        source=source,
    )
