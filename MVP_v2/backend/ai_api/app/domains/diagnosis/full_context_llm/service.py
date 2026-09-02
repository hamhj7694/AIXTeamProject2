from __future__ import annotations

from contracts.diagnosis import ContextResult

from ..extractor import extract_full_context


class FullContextDiagnosisHandler:
    """전체 맥락을 구조화하되 최종 위험 판정은 수행하지 않는다."""

    async def analyze(self, text: str) -> ContextResult:
        return await extract_full_context(text)
