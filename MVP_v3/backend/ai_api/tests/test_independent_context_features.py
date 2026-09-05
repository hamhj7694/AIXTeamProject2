import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import ValidationError
from ai_api.app.domains.diagnosis.context_features import extract_case_context_features
from ai_api.app.domains.diagnosis.budget import diagnosis_budget_scope
from ai_api.app.domains.diagnosis.service import DiagnosisService
from contracts.diagnosis import CaseContextFeatures, ContextResult, WindowAnalysisResult


class IndependentContextTest(unittest.IsolatedAsyncioTestCase):
    async def extract(self, observations):
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        client.responses.create = AsyncMock(return_value=SimpleNamespace(output_text=json.dumps({"observations": observations})))
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test"}), patch(
            "ai_api.app.domains.diagnosis.context_features.AsyncOpenAI", return_value=client,
        ), diagnosis_budget_scope():
            result = await extract_case_context_features("고객 계좌가 범죄에 연루됐다는 주장입니다.")
        client.responses.create.assert_awaited_once()
        return result

    async def test_claim_survives_without_any_ml_events(self):
        features = await self.extract([{"code": "CLAIM_CRIME_INVOLVEMENT", "turn": 1, "status": "CLAIMED"}])
        self.assertEqual(features.claim_codes, ["CLAIM_CRIME_INVOLVEMENT"])
        self.assertEqual(features.extraction_method, "LLM_INDEPENDENT")
        self.assertNotIn("계좌", features.model_dump_json())

    async def test_unrecognized_text_cannot_be_used_as_code(self):
        with self.assertRaises(ValidationError):
            await self.extract([{"code": "개인정보 원문", "turn": 1, "status": "CLAIMED"}])

    async def test_out_of_range_source_is_rejected(self):
        with self.assertRaises(ValueError):
            await self.extract([{"code": "REQUEST_TRANSFER", "turn": 99, "status": "REQUESTED"}])

    async def test_denied_request_is_not_a_demand(self):
        features = await self.extract([{"code": "REQUEST_AUTH_INFO", "turn": 1, "status": "DENIED"}])
        self.assertEqual(features.requested_action_codes, [])
        self.assertIn("DENIED", features.chronology[0])

    async def test_service_passes_independent_features_to_narrator_and_result(self):
        features = CaseContextFeatures(claim_codes=["CLAIM_DEVICE_BROKEN"], extraction_method="LLM_INDEPENDENT")
        window = AsyncMock()
        window.analyze.return_value = WindowAnalysisResult(turns=[], events=[], windows=[], extractor_model="test")
        narrator = AsyncMock()
        narrator.analyze.return_value = ContextResult(summary="요약", incident_type="test", confidence=0.8)
        fusion = MagicMock()
        source = "저장되면 안 되는 원문"
        with patch("ai_api.app.domains.diagnosis.service.extract_case_context_features", new=AsyncMock(return_value=features)):
            await DiagnosisService(window_ai=window, full_context_llm=narrator, fusion=fusion).analyze(source)
        payload = narrator.analyze.await_args.args[0]
        self.assertEqual(payload["case_context_features"]["claim_codes"], ["CLAIM_DEVICE_BROKEN"])
        self.assertNotIn(source, json.dumps(payload, ensure_ascii=False))
        fusion.merge.return_value.model_copy.assert_called_once_with(update={"case_context_features": features})
