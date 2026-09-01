from __future__ import annotations

from contracts.diagnosis import WindowAnalysisResult, WindowResult

from ..extractor import extract_events
from ..features import features_from_events
from ..model_adapter import predict


class WindowAiAdapter:
    """원문 → 문장별 Event → Feature Builder → Window Logistic 경계."""

    async def analyze(self, text: str) -> WindowAnalysisResult:
        extraction = await extract_events(text)
        windows: list[WindowResult] = []
        for turn_id in extraction.successful_turn_ids:
            turn_events = [event for event in extraction.events if event.detected_at_turn == turn_id]
            features = features_from_events(turn_events)
            windows.append(WindowResult(
                segment_id=f"seg-{turn_id:04d}", start_turn=turn_id, end_turn=turn_id,
                text=extraction.turns[turn_id - 1], features=features, **predict(features),
            ))
        if not windows:
            raise RuntimeError("분석 가능한 Window가 없습니다.")
        return WindowAnalysisResult(
            turns=extraction.turns, events=extraction.events, windows=windows,
            extractor_model=extraction.extractor_model, warnings=extraction.warnings,
        )
