"""Generate a bounded structured work-card proposal from current Case context."""

from __future__ import annotations

import json
import os
import re

from openai import AsyncOpenAI, AuthenticationError, RateLimitError

from contracts.ai_internal.work_card import CaseWorkCardInput, CaseWorkCardOutput, WorkCardQuestion

WORK_CARD_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "card_type": {"type": "string", "enum": ["FACT_REVIEW", "QUESTION_PLAN", "VERIFICATION_REQUEST", "BANK_ACTION", "CUSTOMER_NOTICE", "CASE_TRANSITION"]},
        "title": {"type": "string"}, "summary": {"type": "string"},
        "context_sources": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
        "rationale": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
        "next_action": {"type": "string"},
        "questions": {"type": "array", "maxItems": 10, "items": {
            "type": "object", "additionalProperties": False,
            "properties": {
                "question_id": {"type": "string"}, "target_field": {"type": "string"}, "question_text": {"type": "string"},
                "reason": {"type": "string"}, "priority": {"type": "string", "enum": ["P0", "P1", "P2"]},
                "options": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
                "customer_explanation": {"type": ["string", "null"]},
                "answer_mode": {"type": "string", "enum": ["SINGLE_CHOICE", "TEXT", "CHOICE_OR_TEXT"]},
                "allow_free_text": {"type": "boolean"},
            },
            "required": ["question_id", "target_field", "question_text", "reason", "priority", "options", "customer_explanation", "answer_mode", "allow_free_text"],
        }},
        "suggested_claim": {"type": ["string", "null"]}, "suggested_target": {"type": ["string", "null"]},
        "suggested_action_type": {"type": ["string", "null"]}, "suggested_action_note": {"type": ["string", "null"]},
        "suggested_notice": {"type": ["string", "null"]}, "suggested_transition": {"type": ["string", "null"]},
        "warnings": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
    },
    "required": ["card_type", "title", "summary", "context_sources", "rationale", "next_action", "questions", "suggested_claim", "suggested_target", "suggested_action_type", "suggested_action_note", "suggested_notice", "suggested_transition", "warnings"],
}


def _short(value: str, limit: int = 220) -> str:
    clean = " ".join(value.split())
    return clean if len(clean) <= limit else f"{clean[:limit].rstrip()}…"


def _verification_seed(request: CaseWorkCardInput) -> tuple[str, str]:
    if request.pending_verifications:
        target, separator, claim = request.pending_verifications[0].partition(":")
        if separator:
            return claim.strip() or "공식 발신 여부 확인", target.strip() or "확인 대상 기관"
    context = " ".join([request.case_summary, *request.known_facts, *request.recent_conversation])
    organization_patterns = (
        r"서울(?:중앙|동부|서부|남부|북부)?지검", r"(?:서울)?중앙지방검찰청", r"검찰청",
        r"금융감독원", r"경찰청", r"경찰서", r"국세청", r"국민건강보험공단",
        r"[가-힣A-Za-z]{2,12}은행", r"[가-힣A-Za-z]{2,12}카드",
    )
    organization = next((match.group(0) for pattern in organization_patterns if (match := re.search(pattern, context))), None)
    if organization:
        return (
            f"상대방이 {organization} 소속 또는 관계자라고 주장했으며, 안내 내용이 실제 공식 업무인지 확인이 필요합니다.",
            f"{organization} 공식 대표번호·담당자 및 사건/업무 안내의 실재 여부",
        )
    fraud_label = request.fraud_type if request.fraud_type and "확인" not in request.fraud_type else "공공기관·금융기관 사칭"
    return (
        f"상대방이 {fraud_label} 관계자라고 주장했습니다. 공식 기관의 실제 안내인지 확인이 필요합니다.",
        "사칭 기관명·발신 연락처·사건번호의 공식 등록 여부",
    )


def _fallback_questions(request: CaseWorkCardInput) -> list[WorkCardQuestion]:
    if request.question_candidates:
        return request.question_candidates
    defaults = [
        ("transfer_status", "상대방 요구대로 송금하거나 이체한 금액이 있나요?", ["아니요", "송금 진행 중", "이미 송금했어요", "잘 모르겠어요"]),
        ("personal_information_exposure", "주민등록번호나 계좌번호 등 개인정보를 알려주셨나요?", ["아니요", "일부 알려줬어요", "모두 알려줬어요", "잘 모르겠어요"]),
        ("authentication_information_exposure", "인증번호·비밀번호·OTP를 알려주셨나요?", ["아니요", "일부 알려줬어요", "알려줬어요", "잘 모르겠어요"]),
    ]
    return [WorkCardQuestion(
        question_id=f"fallback-{field}", target_field=field, question_text=text,
        reason="현재 Case에서 피해 범위와 즉시 조치 필요성을 판단하기 위해 확인이 필요합니다.",
        priority="P0", options=options,
        customer_explanation="기억나는 범위에서 선택해 주세요. 확실하지 않으면 ‘잘 모르겠어요’를 선택할 수 있습니다.",
        answer_mode="CHOICE_OR_TEXT", allow_free_text=True,
    ) for field, text, options in defaults]


def _build_context_card(request: CaseWorkCardInput, model_mode: str) -> CaseWorkCardOutput:
    case_summary = _short(request.case_summary) or "Case 요약이 아직 확정되지 않았습니다."
    unresolved = [_short(item, 140) for item in request.unresolved_items[:4]]
    known = [_short(item, 140) for item in request.known_facts[:4]]
    claim, target = _verification_seed(request)
    recovery = request.case_mode == "RECOVERY"
    context_sources = ["은행 Case 상태"]
    if request.case_summary:
        context_sources.insert(0, "통화·신고 맥락")
    if request.known_facts:
        context_sources.append("고객 응답·확인 정보")
    if request.recent_conversation:
        context_sources.append("최근 고객·팀 대화")
    if request.pending_verifications:
        context_sources.append("기관 검증 현황")
    if request.pending_actions:
        context_sources.append("은행 대응 업무")
    if request.attachment_summaries:
        context_sources.append("첨부 자료")
    context_sources = context_sources[:6]

    common = {
        "card_type": request.card_type,
        "context_sources": context_sources,
        "rationale": [
            f"현재 상태: {request.workflow_status} · {request.case_mode}",
            f"Case 요약: {case_summary}",
            *(f"미확인 항목: {item}" for item in unresolved[:2]),
            *(f"확인 정보: {item}" for item in known[:2]),
        ],
        "warnings": ["AI가 구성한 초안입니다. 고객 전송·기관 확인·금융 조치는 담당자가 내용을 확인한 뒤 실행해야 합니다."],
        "model_mode": model_mode,
    }
    if request.card_type == "QUESTION_PLAN":
        questions = _fallback_questions(request)
        return CaseWorkCardOutput(
            **common, title="고객 확인 질문 추천",
            summary=f"현재 미확인 항목을 기준으로 고객에게 순서대로 확인할 질문 {len(questions)}개를 구성했습니다.",
            next_action="질문 내용을 검토하고 필요한 항목을 선택한 뒤 고객 질문으로 전달하세요.",
            questions=questions,
        )
    if request.card_type == "VERIFICATION_REQUEST":
        return CaseWorkCardOutput(
            **common, title="기관·사칭 주장 확인 초안",
            summary=f"‘{target}’ 관련 주장을 공식 채널에서 확인할 수 있도록 검증 대상과 내용을 채웠습니다.",
            next_action="사칭 주장과 확인 대상을 검토한 뒤 기관 검증 업무로 등록하세요.",
            suggested_claim=claim, suggested_target=target,
        )
    if request.card_type == "BANK_ACTION":
        action_type = "PAYMENT_HOLD_REVIEW" if recovery else "CUSTOMER_CALLBACK"
        action_note = (
            "고객의 추가 송금 여부를 즉시 확인하고, 이미 송금했다면 지급정지 가능 여부와 피해구제 접수 절차를 검토합니다."
            if recovery else
            "고객에게 추가 송금과 인증정보 제공 중단을 안내하고, 공식 연락처를 통한 재확인 및 후속 상담 일정을 등록합니다."
        )
        return CaseWorkCardOutput(
            **common, title="은행 보호조치 검토",
            summary="현재 Case 상태에 맞는 보호조치 유형과 담당자 업무 내용을 채웠습니다.",
            next_action="실제 거래 상태를 확인하고 권한 있는 담당자의 승인 절차에 따라 보호조치 업무를 등록하세요.",
            suggested_action_type=action_type, suggested_action_note=action_note,
        )
    if request.card_type == "CUSTOMER_NOTICE":
        notice = (
            "이미 피해가 발생한 것으로 확인되어 추가 송금과 인증정보 제공을 즉시 중단해 주세요. 거래내역과 대화·문자 자료를 삭제하지 말고 보존한 뒤 은행 담당자의 지급정지 및 피해구제 안내를 따라 주세요."
            if recovery else
            "현재 연락은 보이스피싱 가능성을 확인 중입니다. 추가 송금이나 개인정보·인증번호 제공을 중단하고, 상대방이 알려준 번호가 아닌 기관의 공식 대표번호로만 확인해 주세요."
        )
        return CaseWorkCardOutput(
            **common, title="고객 안전 안내 초안",
            summary="내부 위험점수나 검증 정보는 제외하고 고객에게 바로 이해되는 안내문을 작성했습니다.",
            next_action="고객이 오해하지 않도록 문안을 확인한 뒤 고객 공개 채널로 전송하세요.",
            suggested_notice=notice,
        )
    if request.card_type == "CASE_TRANSITION":
        transition = "RECOVERY" if recovery else "VERIFYING" if request.workflow_status in {"NEW", "TRIAGE"} else "IN_PROGRESS"
        return CaseWorkCardOutput(
            **common, title="다음 업무 단계 제안",
            summary=f"현재 상태와 미확인 항목을 기준으로 다음 검토 단계 ‘{transition}’을 제안합니다.",
            next_action="현재 담당자가 상태 변경의 영향을 확인하고 명시적으로 승인하세요.",
            suggested_transition=transition,
        )
    return CaseWorkCardOutput(
        **common, title="미확인 정보 검토",
        summary=f"확인된 정보 {len(request.known_facts)}건과 미확인 항목 {len(request.unresolved_items)}건을 담당자 검토 대상으로 정리했습니다.",
        next_action="근거와 신뢰도를 확인해 사실을 확정하거나 고객 확인 질문으로 전환하세요.",
    )


def _fill_empty_proposal(payload: dict, fallback: CaseWorkCardOutput) -> dict:
    fallback_payload = fallback.model_dump(mode="python")
    for key in ("title", "summary", "context_sources", "rationale", "next_action", "questions", "warnings"):
        if not payload.get(key):
            payload[key] = fallback_payload[key]
    relevant = {
        "VERIFICATION_REQUEST": ("suggested_claim", "suggested_target"),
        "BANK_ACTION": ("suggested_action_type", "suggested_action_note"),
        "CUSTOMER_NOTICE": ("suggested_notice",),
        "CASE_TRANSITION": ("suggested_transition",),
    }
    for key in relevant.get(fallback.card_type, ()):
        if not payload.get(key):
            payload[key] = fallback_payload[key]
    return payload


def _provider_fallback(card: CaseWorkCardOutput, mode: str, warning: str) -> CaseWorkCardOutput:
    return card.model_copy(update={
        "model_mode": mode,
        "warnings": [*card.warnings, warning],
    })


class CaseWorkCardService:
    async def generate(self, request: CaseWorkCardInput) -> CaseWorkCardOutput:
        fallback = _build_context_card(request, "RULE_BASED_FALLBACK")
        if os.getenv("CASE_WORK_CARD_MODE", "openai").lower() == "fixture":
            return _build_context_card(request, "FIXTURE")
        if not os.getenv("OPENAI_API_KEY"):
            return fallback
        client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "20")))
        try:
            response = await client.responses.create(
                model=os.getenv("OPENAI_CASE_WORK_CARD_MODEL", "gpt-4o-mini"),
                instructions=(
                    "은행 보이스피싱 대응 담당자가 사건 맥락을 10초 안에 이해하고 바로 행동할 수 있는 한국어 업무 카드 payload를 생성하세요. "
                    "문장은 짧고 구체적으로 쓰고, 상황 판단과 근거와 다음 행동을 분리하세요. 입력에 없는 사실은 만들지 말고 미확인으로 표시하세요. "
                    "QUESTION_PLAN은 이미 확인/대기 중인 항목을 반복하지 말고 고객이 이해하기 쉬운 질문과 선택지를 만드세요. "
                    "고객 안내는 내부 위험점수나 근거를 노출하지 마세요. 지급정지, 상태 변경, 기관 요청, 고객 전송은 반드시 사람 검토가 필요합니다. "
                    "context_sources에는 실제 입력에 포함된 통화·신고 맥락, 고객 응답·확인 정보, 은행 Case 상태, 기관 검증 현황만 표시하세요. "
                    "suggested_action_type은 PAYMENT_HOLD_REVIEW, ACCOUNT_REPORT_GUIDANCE, EVIDENCE_PRESERVATION, DEVICE_SECURITY_GUIDANCE, CUSTOMER_CALLBACK, OTHER 중 하나만 사용하세요."
                ),
                input=request.model_dump_json(),
                max_output_tokens=int(os.getenv("OPENAI_CASE_WORK_CARD_MAX_OUTPUT_TOKENS", "700")),
                text={"format": {"type": "json_schema", "name": "case_work_card_v1", "schema": WORK_CARD_SCHEMA, "strict": True}},
            )
        except RateLimitError:
            return _provider_fallback(
                fallback, "RULE_BASED_FALLBACK_QUOTA",
                "OpenAI 사용 한도에 도달해 현재 Case 데이터 기반 규칙 초안을 표시합니다.",
            )
        except AuthenticationError:
            return _provider_fallback(
                fallback, "RULE_BASED_FALLBACK_AUTH",
                "OpenAI 인증을 사용할 수 없어 현재 Case 데이터 기반 규칙 초안을 표시합니다.",
            )
        except Exception:
            return _provider_fallback(
                fallback, "RULE_BASED_FALLBACK_PROVIDER_ERROR",
                "AI 제공자 응답을 사용할 수 없어 현재 Case 데이터 기반 규칙 초안을 표시합니다. 초안을 검토한 뒤 실행하세요.",
            )
        try:
            payload = json.loads(response.output_text)
        except (TypeError, ValueError):
            return _provider_fallback(
                fallback, "RULE_BASED_FALLBACK_INVALID_OUTPUT",
                "AI 응답 형식을 확인할 수 없어 현재 Case 데이터 기반 규칙 초안을 표시합니다. 초안을 검토한 뒤 실행하세요.",
            )
        payload["card_type"] = request.card_type
        payload["model_mode"] = os.getenv("OPENAI_CASE_WORK_CARD_MODEL", "gpt-4o-mini")
        try:
            return CaseWorkCardOutput.model_validate(_fill_empty_proposal(payload, fallback))
        except (TypeError, ValueError):
            return _provider_fallback(
                fallback, "RULE_BASED_FALLBACK_INVALID_OUTPUT",
                "AI 카드 내용을 안전하게 검증할 수 없어 현재 Case 데이터 기반 규칙 초안을 표시합니다.",
            )
