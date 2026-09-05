from __future__ import annotations

from contracts.diagnosis import ContextResult, DiagnosisResult, WindowAnalysisResult
from request_trace import trace_stage

from .extractor import signal_context_payload
from .budget import diagnosis_budget_scope
from .full_context_llm import FullContextDiagnosisHandler
from .risk_fusion import DiagnosisFusion
from .window_ai import WindowAiAdapter
from .context_features import extract_case_context_features


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
            # Source text is transient: only the two extraction stages see it.
            with trace_stage("ai.events_and_ml"):
                window_result: WindowAnalysisResult = await self.window_ai.analyze(text)
            with trace_stage("ai.context_features"):
                context_features = await extract_case_context_features(text)
            # The context LLM receives codes and references, never raw utterances.
            payload = signal_context_payload(window_result.events)
            payload["case_context_features"] = context_features.model_dump(mode="json")
            with trace_stage("ai.context_summary"):
                context: ContextResult = await self.full_context_llm.analyze(payload)
        result = self.fusion.merge(
            window_result, context, case_id=case_id,
        )
        return result.model_copy(update={"case_context_features": context_features})
