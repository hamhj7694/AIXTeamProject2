from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from ai_api.app.domains.diagnosis import DiagnosisService
from contracts.diagnosis import AnalyzeTextRequest
from general_api.app.domains.cases.repository import InMemoryCaseRepository
from general_api.app.domains.cases.service import AnalyzeCaseService


class LocalDiagnosisClient:
    async def analyze(self, request: AnalyzeTextRequest):
        return await DiagnosisService().analyze(request.text)


class AnalyzeCaseServiceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.repository = InMemoryCaseRepository()
        self.service = AnalyzeCaseService(LocalDiagnosisClient(), self.repository)

    async def test_high_risk_creates_case_and_is_idempotent(self) -> None:
        request = AnalyzeTextRequest(
            text="검찰청입니다. 지금 안전계좌로 500만원을 송금하세요.",
            client_request_id="request-1",
        )
        with patch.dict(os.environ, {"DIAGNOSIS_EXTRACTOR_MODE": "fixture"}):
            first = await self.service.analyze(request)
            second = await self.service.analyze(request)
        self.assertEqual(first.disposition, "CASE_CREATED")
        self.assertEqual(first.case_id, second.case_id)
        self.assertIsNotNone(first.initial_report)
        self.assertEqual(len(first.initial_report.sections), 7)
        self.assertEqual(first.initial_report.case_id, first.case_id)
        self.assertEqual(len(await self.repository.list()), 1)
        stored = await self.repository.get(first.case_id or "")
        self.assertIsNotNone(stored)
        self.assertEqual(stored["initial_brief"], first.initial_brief)

    async def test_normal_call_does_not_create_case(self) -> None:
        request = AnalyzeTextRequest(text="예금 만기일은 다음 달 15일입니다.")
        with patch.dict(os.environ, {"DIAGNOSIS_EXTRACTOR_MODE": "fixture"}):
            result = await self.service.analyze(request)
        self.assertEqual(result.disposition, "NO_CASE")
        self.assertEqual(await self.repository.list(), [])


if __name__ == "__main__":
    unittest.main()
