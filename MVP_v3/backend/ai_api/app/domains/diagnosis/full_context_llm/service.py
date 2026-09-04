from __future__ import annotations

from typing import Any

from contracts.diagnosis import ContextResult

from ..extractor import extract_context_from_signal_payload


class FullContextDiagnosisHandler:
    """전체 맥락을 구조화하되 최종 위험 판정은 수행하지 않는다."""

    async def analyze(self, signal_payload: dict[str, Any]) -> ContextResult:
        """Create Case context from privacy-safe structured signals only."""
        return await extract_context_from_signal_payload(signal_payload)
