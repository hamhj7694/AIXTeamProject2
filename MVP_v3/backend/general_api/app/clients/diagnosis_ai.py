from __future__ import annotations

import os
from typing import Protocol

import httpx

from contracts.diagnosis import AnalyzeTextRequest, DiagnosisResult
from contracts.ai_internal.context_fact_extraction import ContextFactExtractionInput, ContextFactExtractionOutput
from request_trace import request_id


class DiagnosisAiClient(Protocol):
    async def analyze(self, request: AnalyzeTextRequest) -> DiagnosisResult: ...
    async def extract_context_facts(self, request: ContextFactExtractionInput) -> ContextFactExtractionOutput: ...


class AiServiceError(RuntimeError):
    code = "AI_SERVICE_UNAVAILABLE"
    retryable = True

    def __init__(self, message: str, *, code: str | None = None, retryable: bool | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code
        if retryable is not None:
            self.retryable = retryable


class AiServiceQuotaError(AiServiceError):
    code = "AI_PROVIDER_RATE_LIMITED"


class AiServiceBudgetError(AiServiceError):
    """The local case-analysis safety budget rejected the request."""

    code = "AI_BUDGET_LIMIT_REACHED"
    retryable = False


class AiServiceAuthenticationError(AiServiceError):
    code = "AI_PROVIDER_AUTH_ERROR"
    retryable = False


class AiServiceTimeoutError(AiServiceError):
    code = "AI_PROVIDER_TIMEOUT"


class HttpDiagnosisAiClient:
    def __init__(self, base_url: str | None = None, timeout_seconds: float | None = None) -> None:
        self.base_url = (base_url or os.getenv("AI_API_BASE_URL", "http://127.0.0.1:8101")).rstrip("/")
        self.timeout_seconds = timeout_seconds or float(os.getenv("AI_API_TIMEOUT_SECONDS", "120"))

    async def analyze(self, request: AnalyzeTextRequest) -> DiagnosisResult:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                # Demo-only adapter: inside this request the source text is
                # converted to an Analysis Envelope before the CSR core runs.
                # Keeping one request preserves the existing per-analysis call
                # and token budget. Production integrations call
                # /ai/analyze/signals directly with an upstream Envelope.
                response = await client.post(
                    f"{self.base_url}/ai/analyze/text",
                    json=request.model_dump(mode="json"), headers={"X-Request-ID": request_id.get()},
                )
                if not response.is_success:
                    payload = response.json()
                    detail = payload.get("detail", {})
                    message = detail.get("message", "AI 분석 서버가 요청을 처리하지 못했습니다.")
                    if response.status_code == 429 and detail.get("code") == "AI_BUDGET_LIMIT_REACHED":
                        raise AiServiceBudgetError(message)
                    if response.status_code == 429:
                        raise AiServiceQuotaError(message)
                    if response.status_code == 401:
                        raise AiServiceAuthenticationError(message)
                    raise AiServiceError(message)
                return DiagnosisResult.model_validate(response.json())
        except httpx.TimeoutException as exc:
            raise AiServiceTimeoutError(f"AI 분석 제한시간({self.timeout_seconds:.0f}초)을 초과했습니다. 다시 시도해 주세요.") from exc
        except httpx.RequestError as exc:
            raise AiServiceError("AI 분석 서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.") from exc

    async def extract_context_facts(self, request: ContextFactExtractionInput) -> ContextFactExtractionOutput:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/ai/context/facts/extract",
                    json=request.model_dump(mode="json"),
                    headers={"X-Request-ID": request_id.get()},
                )
                if not response.is_success:
                    raise AiServiceError("AI 맥락 사실 추출에 실패했습니다.")
                return ContextFactExtractionOutput.model_validate(response.json())
        except httpx.TimeoutException as exc:
            raise AiServiceError("AI 맥락 사실 추출 제한 시간을 초과했습니다.") from exc
        except httpx.RequestError as exc:
            raise AiServiceError("AI 맥락 사실 추출 서버에 연결할 수 없습니다.") from exc

    async def generate_case_copilot_reply(self, payload: dict) -> dict:
        """One user-initiated, bounded CaseCopilot request."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/ai/case-copilot/replies", json=payload)
                if not response.is_success:
                    detail = response.json().get("detail", {})
                    message = detail.get("message", "CaseCopilot 응답을 만들지 못했습니다.")
                    if response.status_code == 429:
                        raise AiServiceQuotaError(message)
                    if response.status_code == 401:
                        raise AiServiceAuthenticationError(message)
                    raise AiServiceError(message)
                return response.json()
        except httpx.TimeoutException as exc:
            raise AiServiceError(f"CaseCopilot 응답 시간이 {self.timeout_seconds:.0f}초를 초과했습니다.") from exc
        except httpx.RequestError as exc:
            raise AiServiceError("CaseCopilot 서버에 연결할 수 없습니다.") from exc

    async def build_case_support_snapshot(self, snapshot: dict) -> dict:
        """AI 내부 snapshot을 호출하되, Public API에는 내부 DTO를 그대로 내보내지 않는다."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/ai/case-support/snapshot", json=snapshot)
                if not response.is_success:
                    raise AiServiceError("AI 사건 지원 결과를 만들지 못했습니다.")
                return response.json()
        except httpx.TimeoutException as exc:
            raise AiServiceError(f"AI 사건 지원 제한시간({self.timeout_seconds:.0f}초)을 초과했습니다.") from exc
        except httpx.RequestError as exc:
            raise AiServiceError("AI 사건 지원 서버에 연결할 수 없습니다.") from exc

    async def generate_work_card(self, payload: dict) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/ai/work-cards/generate", json=payload)
                if not response.is_success:
                    detail = response.json().get("detail", {})
                    message = detail.get("message", "AI 업무 카드를 만들지 못했습니다.")
                    if response.status_code == 429:
                        raise AiServiceQuotaError(message)
                    if response.status_code == 401:
                        raise AiServiceAuthenticationError(message)
                    raise AiServiceError(message)
                return response.json()
        except httpx.TimeoutException as exc:
            raise AiServiceError(f"AI 업무 카드 생성 시간이 {self.timeout_seconds:.0f}초를 초과했습니다.") from exc
        except httpx.RequestError as exc:
            raise AiServiceError("AI 업무 카드 서버에 연결할 수 없습니다.") from exc

    async def generate_final_report(self, payload: dict) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/ai/final-reports/generate", json=payload)
                if not response.is_success:
                    detail = response.json().get("detail", {})
                    message = detail.get("message", "AI 최종 결과 보고서를 만들지 못했습니다.")
                    if response.status_code == 429:
                        raise AiServiceQuotaError(message)
                    if response.status_code == 401:
                        raise AiServiceAuthenticationError(message)
                    raise AiServiceError(message)
                return response.json()
        except httpx.TimeoutException as exc:
            raise AiServiceError(f"AI 최종 결과 보고서 생성 시간이 {self.timeout_seconds:.0f}초를 초과했습니다.") from exc
        except httpx.RequestError as exc:
            raise AiServiceError("AI 최종 결과 보고서 서버에 연결할 수 없습니다.") from exc
