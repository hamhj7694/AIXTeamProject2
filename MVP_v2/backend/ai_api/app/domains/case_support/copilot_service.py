"""Bounded, explicit LLM call used only after a bank user invokes CaseCopilot."""

from __future__ import annotations

import asyncio
import os
import time
from collections import defaultdict, deque

from openai import AsyncOpenAI, AuthenticationError, RateLimitError

from contracts.ai_internal.case_copilot import CaseCopilotInput, CaseCopilotOutput


class CaseCopilotQuotaError(RuntimeError):
    pass


class CaseCopilotAuthenticationError(RuntimeError):
    pass


class CustomerSupportCallBudget:
    """Per-process hard stop; production also needs a shared Redis/DB quota."""

    def __init__(self) -> None:
        self._calls: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def reserve(self, case_id: str) -> None:
        per_minute = max(1, int(os.getenv("CUSTOMER_AI_MAX_CALLS_PER_MINUTE", "6")))
        per_day = max(per_minute, int(os.getenv("CUSTOMER_AI_MAX_CALLS_PER_DAY", "40")))
        now = time.monotonic()
        async with self._lock:
            calls = self._calls[case_id]
            while calls and now - calls[0] >= 86_400:
                calls.popleft()
            if len(calls) >= per_day:
                raise CaseCopilotQuotaError("이 Case의 오늘 고객 AI 상담 한도에 도달했습니다. 은행 담당자에게 연결해 주세요.")
            recent = sum(1 for called_at in calls if now - called_at < 60)
            if recent >= per_minute:
                raise CaseCopilotQuotaError("AI 상담 요청이 연속으로 접수되었습니다. 잠시 후 다시 시도해 주세요.")
            calls.append(now)


_customer_support_budget = CustomerSupportCallBudget()
_customer_support_concurrency = asyncio.Semaphore(max(1, int(os.getenv("CUSTOMER_AI_MAX_CONCURRENCY", "2"))))


class CaseCopilotService:
    async def generate(self, request: CaseCopilotInput) -> CaseCopilotOutput:
        if len(request.prompt.strip()) > int(os.getenv("CASE_COPILOT_MAX_INPUT_CHARS", "6000")):
            raise ValueError("AI 요청은 6,000자 이하로 입력해 주세요.")
        if os.getenv("CASE_COPILOT_MODE", "openai").lower() == "fixture":
            return CaseCopilotOutput(
                content=("[개발용 AI 응답] " + request.prompt.strip() + "\n\n"
                         "실운영에서는 사용자가 요청한 시점에만 실제 CaseCopilot 분석이 생성됩니다."),
                model_mode="FIXTURE",
            )
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY가 설정되지 않아 CaseCopilot을 실행할 수 없습니다.")

        sections = {
            "확인 정보": request.known_facts,
            "최근 대화": request.recent_conversation,
            "진행 중 은행 업무": request.pending_actions,
            "첨부 자료 메타데이터": request.attachment_summaries,
            "미완료 기관 검증": request.unresolved_verifications,
        }
        context = "\n".join(
            f"[{title}]\n" + ("\n".join(f"- {item}" for item in items) if items else "- 없음")
            for title, items in sections.items()
        )
        client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "20")))
        if request.assistant_mode == "CUSTOMER_SUPPORT":
            instructions = (
                "당신은 보이스피싱 피해 예방을 돕는 고객용 안전 상담 AI입니다. 고객에게 공개 가능한 정보만 사용하세요. "
                "고객의 현재 질문에 먼저 한두 문장으로 명확히 답하고, 지금 해야 할 행동이 있으면 최대 3개로 짧게 안내하세요. "
                "이미 질문했거나 답변받은 확인 항목을 다시 묻지 마세요. 구조화된 확인 질문은 별도 질문 카드가 담당하므로 새 문진을 시작하지 마세요. "
                "은행 내부 판단, 위험 점수, 내부 검증 업무, 직원 대화는 절대 언급하지 마세요. 사실을 지어내거나 송금·계정 조치를 완료됐다고 단정하지 마세요. "
                "긴급 피해가 의심되면 추가 송금과 상대방 접촉을 중단하고 거래 은행 공식 고객센터, 경찰 112, 금융감독원 1332 등 공식 채널 확인을 안내하세요. "
                "쉽고 차분한 한국어를 사용하고 내부용 제목이나 보고서 형식은 쓰지 마세요."
            )
            request_label = "고객 메시지"
        else:
            instructions = (
                "당신은 은행 내부 보이스피싱 대응 보조 AI입니다. 담당자가 사건 맥락을 10초 안에 파악하고 바로 행동할 수 있도록 답하세요. "
                "제공된 Case 정보만 사용하고 [상황 판단], [확인된 정보], [미확인 정보], [권장 다음 행동] 순서로 구분하세요. "
                "각 문장은 짧고 구체적인 한국어로 쓰고, 다음 행동에는 우선순위가 높은 순서대로 번호를 붙이세요. "
                "금융 조치를 확정하거나 고객 정보를 지어내지 마세요. 고객에게 바로 보이는 문장이 아니라 "
                "은행 직원의 내부 작업 초안입니다. 확인된 내용이 없으면 ‘확인된 정보 없음’이라고 명시하세요."
            )
            request_label = "직원 요청"
        try:
            if request.assistant_mode == "CUSTOMER_SUPPORT":
                await _customer_support_budget.reserve(request.case_id)
            async with _customer_support_concurrency if request.assistant_mode == "CUSTOMER_SUPPORT" else _null_async_context():
                response = await client.responses.create(
                    model=os.getenv("OPENAI_CASE_COPILOT_MODEL", "gpt-4o-mini"),
                    instructions=instructions,
                    input=(
                        f"Case ID: {request.case_id}\n상태: {request.workflow_status}\n"
                        f"사기 유형: {request.fraud_type or '확인 중'}\n송금 상태: {request.transfer_status or '확인 중'}\n"
                        f"Case 요약: {request.case_summary or '없음'}\nShared Case 맥락:\n{context}\n\n"
                        f"{request_label}:\n{request.prompt.strip()}"
                    ),
                    max_output_tokens=int(os.getenv(
                        "OPENAI_CUSTOMER_AI_MAX_OUTPUT_TOKENS" if request.assistant_mode == "CUSTOMER_SUPPORT" else "OPENAI_CASE_COPILOT_MAX_OUTPUT_TOKENS",
                        "250" if request.assistant_mode == "CUSTOMER_SUPPORT" else "400",
                    )),
                )
        except RateLimitError as exc:
            raise CaseCopilotQuotaError("AI 사용 한도에 도달했습니다. 잠시 후 다시 요청해 주세요.") from exc
        except AuthenticationError as exc:
            raise CaseCopilotAuthenticationError("CaseCopilot API 인증을 확인해 주세요.") from exc
        content = response.output_text.strip()
        if not content:
            raise RuntimeError("CaseCopilot이 비어 있는 응답을 반환했습니다.")
        return CaseCopilotOutput(content=content, model_mode=os.getenv("OPENAI_CASE_COPILOT_MODEL", "gpt-4o-mini"))


class _null_async_context:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None
