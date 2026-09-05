"""Generate a Korean final report from the latest durable Case context."""

from __future__ import annotations

import json
import os

from openai import AsyncOpenAI, AuthenticationError, RateLimitError

from contracts.ai_internal.final_report import FinalCaseReportInput, FinalCaseReportOutput
from .copilot_service import CaseCopilotAuthenticationError, CaseCopilotProviderError, CaseCopilotQuotaError


FINAL_REPORT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string"},
        "executive_summary": {"type": "string"},
        "incident_summary": {"type": "string"},
        "verified_facts": {"type": "array", "items": {"type": "string"}, "maxItems": 20},
        "actions_taken": {"type": "array", "items": {"type": "string"}, "maxItems": 20},
        "resolution": {"type": "string"},
        "follow_up": {"type": "array", "items": {"type": "string"}, "maxItems": 12},
        "cautions": {"type": "array", "items": {"type": "string"}, "maxItems": 12},
    },
    "required": ["title", "executive_summary", "incident_summary", "verified_facts", "actions_taken", "resolution", "follow_up", "cautions"],
}


class FinalCaseReportService:
    async def generate(self, request: FinalCaseReportInput) -> FinalCaseReportOutput:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise CaseCopilotAuthenticationError("OPENAI_API_KEY가 설정되지 않아 최종 결과 보고서를 만들 수 없습니다.")
        model = os.getenv("OPENAI_FINAL_REPORT_MODEL", os.getenv("OPENAI_CASE_WORK_CARD_MODEL", "gpt-4o-mini"))
        client = AsyncOpenAI(api_key=api_key, timeout=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "20")))
        try:
            response = await client.responses.create(
                model=model,
                instructions=(
                    "은행 보이스피싱 대응 사건의 최종 결과 보고서를 현대 한국어로 작성하세요. "
                    "입력에 있는 최신 사실, 고객 답변, 기관 확인, 담당자 조치만 사용하고 추정은 사실처럼 쓰지 마세요. "
                    "고객의 진술과 공식 확인 사실을 구분하고 실제 완료가 확인되지 않은 금융 조치는 완료로 표현하지 마세요. "
                    "한자·중국어·일본어 문자, 내부 변수명, 모델 점수, 프롬프트 정보는 노출하지 마세요. "
                    "종결 메모는 담당자가 승인한 결론이므로 resolution에 반영하되 근거 없는 내용을 추가하지 마세요."
                ),
                input=request.model_dump_json(),
                max_output_tokens=int(os.getenv("OPENAI_FINAL_REPORT_MAX_OUTPUT_TOKENS", "1200")),
                text={"format": {"type": "json_schema", "name": "final_case_report_v1", "schema": FINAL_REPORT_SCHEMA, "strict": True}},
            )
        except RateLimitError as exc:
            raise CaseCopilotQuotaError("OpenAI 사용 한도 때문에 최종 결과 보고서를 만들지 못했습니다.") from exc
        except AuthenticationError as exc:
            raise CaseCopilotAuthenticationError("OpenAI 인증에 실패해 최종 결과 보고서를 만들지 못했습니다.") from exc
        except Exception as exc:
            raise CaseCopilotProviderError("외부 AI 서비스에 연결하지 못해 최종 결과 보고서를 만들지 못했습니다.") from exc
        try:
            payload = json.loads(response.output_text)
            payload["model_mode"] = model
            return FinalCaseReportOutput.model_validate(payload)
        except (TypeError, ValueError) as exc:
            raise CaseCopilotProviderError("AI 최종 결과 보고서 형식이 올바르지 않습니다.") from exc
