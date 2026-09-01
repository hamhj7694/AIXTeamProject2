from __future__ import annotations

import os
from typing import Protocol

import httpx

from contracts.diagnosis import AnalyzeTextRequest, DiagnosisResult


class DiagnosisAiClient(Protocol):
    async def analyze(self, request: AnalyzeTextRequest) -> DiagnosisResult: ...


class AiServiceError(RuntimeError):
    pass


class HttpDiagnosisAiClient:
    def __init__(self, base_url: str | None = None, timeout_seconds: float = 30.0) -> None:
        self.base_url = (base_url or os.getenv("AI_API_BASE_URL", "http://127.0.0.1:8001")).rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def analyze(self, request: AnalyzeTextRequest) -> DiagnosisResult:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(f"{self.base_url}/ai/analyze/text", json=request.model_dump(mode="json"))
            if not response.is_success:
                payload = response.json()
                detail = payload.get("detail", {})
                message = detail.get("message", "AI 분석 서버가 요청을 처리하지 못했습니다.")
                raise AiServiceError(message)
            return DiagnosisResult.model_validate(response.json())
