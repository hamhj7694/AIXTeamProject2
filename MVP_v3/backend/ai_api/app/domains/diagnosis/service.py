from __future__ import annotations

from contracts.diagnosis import ContextResult, DiagnosisResult, WindowAnalysisResult

from .extractor import build_context_from_events, signal_context_payload
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
        with diagnosis_budget_scope():
            # Source text is transient: only the extraction/window stage sees it.
            window_result: WindowAnalysisResult = await self.window_ai.analyze(text)
            try:
                # The context LLM receives feature signals, never raw utterances.
                context_raw = await self.full_context_llm.analyze(signal_context_payload(window_result.events))
            except BaseException as exc:
                context_raw = exc

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
