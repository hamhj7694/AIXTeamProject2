from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from pydantic import ValidationError

from ai_api.app.domains.diagnosis import DiagnosisService
from ai_api.app.domains.diagnosis.extractor import (
    EventExtraction,
    extract_events,
    extract_full_context,
)
from ai_api.app.domains.diagnosis.model_adapter import load_model_bundle, predict
from contracts.diagnosis import ContextResult


class _FailingFullContext:
    def __init__(self, error: Exception) -> None:
        self.error = error

    async def analyze(self, text: str) -> ContextResult:
        raise self.error


class _StaticFullContext:
    async def analyze(self, text: str) -> ContextResult:
        return ContextResult(
            summary="검증용 전체 맥락", incident_type="유형 확인 필요", confidence=0.7,
        )


class DiagnosisFailureTest(unittest.IsolatedAsyncioTestCase):
    def tearDown(self) -> None:
        load_model_bundle.cache_clear()

    async def test_full_context_failure_preserves_event_fallback(self) -> None:
        for error in (asyncio.TimeoutError(), RuntimeError("OpenAI API error")):
            with self.subTest(error=type(error).__name__), patch.dict(
                os.environ, {"DIAGNOSIS_EXTRACTOR_MODE": "fixture"}, clear=False,
            ):
                result = await DiagnosisService(
                    full_context_llm=_FailingFullContext(error),
                ).analyze("검찰입니다. 지금 500만원을 송금하세요.")

            self.assertTrue(result.partial_failure)
            self.assertTrue(result.evidence)
            self.assertEqual(result.risk_level.value, "HIGH")
            self.assertTrue(any("이벤트 기반 요약" in warning for warning in result.warnings))

    async def test_partial_turn_failure_is_exposed_in_diagnosis_result(self) -> None:
        extraction = EventExtraction(
            turns=["안전한 안내 문장"], events=[], successful_turn_ids=[1],
            extractor_model="mock-openai", warnings=["Turn 2 이벤트 추출 실패: TimeoutError"],
        )
        with patch(
            "ai_api.app.domains.diagnosis.window_ai.service.extract_events",
            new=AsyncMock(return_value=extraction),
        ):
            result = await DiagnosisService(full_context_llm=_StaticFullContext()).analyze(
                "안전한 안내 문장",
            )

        self.assertTrue(result.partial_failure)
        self.assertTrue(any("TimeoutError" in warning for warning in result.warnings))
        self.assertEqual(result.context.summary, "검증용 전체 맥락")

    async def test_all_turn_extraction_failures_raise_instead_of_normal_result(self) -> None:
        client = Mock()
        client.responses.create = AsyncMock(return_value=SimpleNamespace(output_text="not-json"))
        with patch(
            "ai_api.app.domains.diagnosis.extractor.AsyncOpenAI", return_value=client,
        ), patch.dict(
            os.environ,
            {"DIAGNOSIS_EXTRACTOR_MODE": "openai", "OPENAI_API_KEY": "test-key"},
            clear=False,
        ):
            with self.assertRaisesRegex(RuntimeError, "모든 문장의 이벤트 추출"):
                await extract_events("첫 번째 문장.")

    async def test_openai_timeout_keeps_successful_turn_and_uses_configured_timeout(self) -> None:
        client = Mock()
        client.responses.create = AsyncMock(side_effect=[
            asyncio.TimeoutError(),
            SimpleNamespace(output_text=json.dumps({"events": []})),
        ])
        with patch(
            "ai_api.app.domains.diagnosis.extractor.AsyncOpenAI", return_value=client,
        ) as openai_client, patch.dict(
            os.environ,
            {
                "DIAGNOSIS_EXTRACTOR_MODE": "openai",
                "OPENAI_API_KEY": "test-key",
                "OPENAI_TIMEOUT_SECONDS": "12.5",
            },
            clear=False,
        ):
            extraction = await extract_events("첫 번째 문장. 두 번째 문장.")

        self.assertEqual(extraction.successful_turn_ids, [2])
        self.assertTrue(any("TimeoutError" in warning for warning in extraction.warnings))
        self.assertEqual(openai_client.call_args.kwargs["timeout"], 12.5)

    async def test_full_context_invalid_json_raises_validation_error(self) -> None:
        client = Mock()
        client.responses.create = AsyncMock(return_value=SimpleNamespace(output_text="not-json"))
        with patch(
            "ai_api.app.domains.diagnosis.extractor.AsyncOpenAI", return_value=client,
        ), patch.dict(
            os.environ,
            {"DIAGNOSIS_EXTRACTOR_MODE": "openai", "OPENAI_API_KEY": "test-key"},
            clear=False,
        ):
            with self.assertRaises(ValidationError):
                await extract_full_context("검증용 문장")

    def test_missing_artifact_fails_fast(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"WINDOW_MODEL_PATH": str(Path(directory) / "missing.pkl")}, clear=False,
        ):
            with self.assertRaises(FileNotFoundError):
                load_model_bundle()

    def test_artifact_sha_mismatch_fails_fast(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "invalid.pkl"
            artifact.write_bytes(b"not a model artifact")
            with patch.dict(os.environ, {"WINDOW_MODEL_PATH": str(artifact)}, clear=False):
                with self.assertRaisesRegex(ValueError, "SHA-256"):
                    load_model_bundle()

    def test_missing_required_bundle_key_fails_fast(self) -> None:
        with patch("ai_api.app.domains.diagnosis.model_adapter.joblib.load", return_value={}):
            with self.assertRaises(KeyError):
                load_model_bundle()

    def test_joblib_load_failure_is_not_hidden(self) -> None:
        with patch(
            "ai_api.app.domains.diagnosis.model_adapter.joblib.load",
            side_effect=OSError("artifact load failed"),
        ):
            with self.assertRaisesRegex(OSError, "artifact load failed"):
                load_model_bundle()

    def test_predict_failure_is_not_converted_to_normal_result(self) -> None:
        model = Mock()
        model.predict_proba.side_effect = RuntimeError("predict failed")
        bundle = {
            "model": model,
            "model_features": ["feature_a"],
            "threshold": 0.5,
            "guardrail_signal_features": ["feature_a"],
            "guardrail": {},
        }
        with patch(
            "ai_api.app.domains.diagnosis.model_adapter.load_model_bundle", return_value=bundle,
        ):
            with self.assertRaisesRegex(RuntimeError, "predict failed"):
                predict({"feature_a": 1.0})


if __name__ == "__main__":
    unittest.main()
