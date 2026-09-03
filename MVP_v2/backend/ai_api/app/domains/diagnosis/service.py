from __future__ import annotations

import asyncio

from contracts.diagnosis import ContextResult, DiagnosisResult, WindowAnalysisResult

from .extractor import build_context_from_events
from .budget import diagnosis_budget_scope
from .full_context_llm import FullContextDiagnosisHandler
from .risk_fusion import DiagnosisFusion
from .window_ai import WindowAiAdapter


class DiagnosisService:
    def __init__(
        self,
        window_ai: WindowAiAdapter | None = None,
        full_context_llm: FullContextDiagnosisHandler | None = None,
        fusion: DiagnosisFusion | None = None,
    ) -> None:
        self.window_ai = window_ai or WindowAiAdapter()
        self.full_context_llm = full_context_llm or FullContextDiagnosisHandler()
        self.fusion = fusion or DiagnosisFusion()

    async def analyze(self, text: str, case_id: str | None = None) -> DiagnosisResult:
        # 서로 독립적인 WindowAI pipeline과 전체 맥락 LLM을 동시에 시작한다.
        with diagnosis_budget_scope():
            window_raw, context_raw = await asyncio.gather(
                self.window_ai.analyze(text), self.full_context_llm.analyze(text),
                return_exceptions=True,
            )
        if isinstance(window_raw, BaseException):
            raise window_raw
        window_result: WindowAnalysisResult = window_raw

        fallback_warnings: list[str] = []
        if isinstance(context_raw, BaseException):
            context: ContextResult = build_context_from_events(window_result.events)
            fallback_warnings.append(
                f"전체 맥락 LLM 실패로 이벤트 기반 요약을 사용했습니다: {type(context_raw).__name__}"
            )
        else:
            context = context_raw
        return self.fusion.merge(
            window_result, context, case_id=case_id, additional_warnings=fallback_warnings,
        )
