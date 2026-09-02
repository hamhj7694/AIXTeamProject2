from __future__ import annotations

import os

from contracts.diagnosis import WindowAnalysisResult, WindowResult

from ..extractor import extract_events
from ..features import features_from_events
from ..model_adapter import predict


class WindowAiAdapter:
    """원문 → 문장별 Event → Feature Builder → Window Logistic 경계."""

    async def analyze(self, text: str) -> WindowAnalysisResult:
        extraction = await extract_events(text)
        windows: list[WindowResult] = []
        window_turns = int(os.getenv("WINDOW_TURNS", "10"))
        for turn_id in extraction.successful_turn_ids:
            start_turn = max(1, turn_id - window_turns + 1)
            window_events = [
                event for event in extraction.events
                if start_turn <= event.detected_at_turn <= turn_id
            ]
            features = features_from_events(window_events)
            windows.append(WindowResult(
                segment_id=f"seg-{start_turn:04d}-{turn_id:04d}",
                start_turn=start_turn, end_turn=turn_id,
                text=" ".join(extraction.turns[start_turn - 1:turn_id]),
                features=features, **predict(features),
            ))
        if not windows:
            raise RuntimeError("분석 가능한 Window가 없습니다.")
        return WindowAnalysisResult(
            turns=extraction.turns, events=extraction.events, windows=windows,
            extractor_model=extraction.extractor_model, warnings=extraction.warnings,
        )
