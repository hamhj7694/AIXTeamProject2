from __future__ import annotations

import json
import unittest
from unittest.mock import AsyncMock, patch

from ai_api.app.domains.diagnosis import DiagnosisService
from ai_api.app.domains.diagnosis.extractor import EventExtraction, _local_safety_events, parse_turns
from contracts.diagnosis import AnalyzeTextRequest, CaseContextFeatures, ContextResult
from general_api.app.domains.cases.repository import CaseCreationConflictError, CasePersistenceError, InMemoryCaseRepository
from general_api.app.domains.cases.service import AnalyzeCaseService


class RecordingCaseRepository(InMemoryCaseRepository):
    """Make the Case-creation call order explicit in the service contract."""

    def __init__(self) -> None:
        super().__init__()
        self.operations: list[str] = []

    async def find_by_client_request_id(self, client_request_id: str):
        self.operations.append("find_by_client_request_id")
        return await super().find_by_client_request_id(client_request_id)

    async def next_case_id(self) -> str:
        self.operations.append("next_case_id")
        return await super().next_case_id()

    async def get(self, case_id: str):
        self.operations.append("get")
        return await super().get(case_id)

    async def create(self, record: dict):
        self.operations.append("create")
        return await super().create(record)


class LocalDiagnosisClient:
    async def analyze(self, request: AnalyzeTextRequest):
        return await DiagnosisService().analyze(request.text)


class AnalyzeCaseServiceTest(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _extraction(text: str) -> EventExtraction:
        turns = parse_turns(text)
        return EventExtraction(turns, _local_safety_events(turns), list(range(1, len(turns) + 1)), "test-extractor")

    async def asyncSetUp(self) -> None:
        for target, result in [
            ("extract_case_context_features", CaseContextFeatures(extraction_method="LLM_INDEPENDENT", claim_codes=["CLAIM_CRIME_INVOLVEMENT"])),
            ("FullContextDiagnosisHandler.analyze", ContextResult(summary="기관 사칭 의심", incident_type="test", confidence=0.8)),
        ]:
            mock = patch("ai_api.app.domains.diagnosis.service." + target, new=AsyncMock(return_value=result))
            mock.start()
            self.addCleanup(mock.stop)
        self.repository = InMemoryCaseRepository()
        self.service = AnalyzeCaseService(LocalDiagnosisClient(), self.repository)

    async def test_high_risk_creates_case_and_is_idempotent(self) -> None:
        request = AnalyzeTextRequest(
            text="검찰청입니다. 지금 안전계좌로 500만원을 송금하세요.",
            client_request_id="request-1",
        )
        with patch(
            "ai_api.app.domains.diagnosis.window_ai.service.extract_events",
            new=AsyncMock(return_value=self._extraction(request.text)),
        ):
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

    async def test_case_persistence_keeps_signals_not_source_transcript(self) -> None:
        source = "검찰 수사관입니다. 오늘 안에 안전계좌로 이체하고 가족에게 알리지 마세요."
        with patch(
            "ai_api.app.domains.diagnosis.window_ai.service.extract_events",
            new=AsyncMock(return_value=self._extraction(source)),
        ):
            result = await self.service.analyze(AnalyzeTextRequest(text=source))

        stored = await self.repository.get(result.case_id or "")
        self.assertIsNotNone(stored)
        persisted = json.dumps(stored, ensure_ascii=False)
        self.assertEqual(stored["input_text"], "")
        self.assertNotIn(source, persisted)
        self.assertEqual(stored["diagnosis"]["model_metadata"]["source_text_retention"], "NONE")
        features = stored["diagnosis"]["case_context_features"]
        self.assertEqual(features["extraction_method"], "LLM_INDEPENDENT")
        self.assertEqual(features["claim_codes"], ["CLAIM_CRIME_INVOLVEMENT"])
        self.assertTrue(stored["diagnosis"]["evidence"])
        self.assertNotIn("안전계좌", persisted)

    async def test_normal_call_does_not_create_case(self) -> None:
        request = AnalyzeTextRequest(text="예금 만기일은 다음 달 15일입니다.")
        with patch(
            "ai_api.app.domains.diagnosis.window_ai.service.extract_events",
            new=AsyncMock(return_value=self._extraction(request.text)),
        ):
            result = await self.service.analyze(request)
        self.assertEqual(result.disposition, "NO_CASE")
        self.assertEqual(await self.repository.list(), [])

    async def test_insert_collision_retries_storage_without_repeating_ai(self) -> None:
        source = "검찰청입니다. 지금 안전계좌로 500만원을 송금하세요."
        original_create = self.repository.create
        attempts = 0

        async def collide_once(record):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise CaseCreationConflictError()
            return await original_create(record)

        with patch.object(self.repository, "create", new=collide_once), patch(
            "ai_api.app.domains.diagnosis.window_ai.service.extract_events",
            new=AsyncMock(return_value=self._extraction(source)),
        ) as extractor:
            result = await self.service.analyze(AnalyzeTextRequest(text=source))
        self.assertEqual(result.disposition, "CASE_CREATED")
        self.assertEqual(attempts, 2)
        extractor.assert_awaited_once()

    async def test_report_storage_failure_never_returns_created(self) -> None:
        source = "검찰청입니다. 지금 안전계좌로 500만원을 송금하세요."
        with patch.object(self.repository, "create", new=AsyncMock(side_effect=RuntimeError("storage"))), patch(
            "ai_api.app.domains.diagnosis.window_ai.service.extract_events",
            new=AsyncMock(return_value=self._extraction(source)),
        ):
            with self.assertRaises(CasePersistenceError):
                await self.service.analyze(AnalyzeTextRequest(text=source))
        self.assertEqual(await self.repository.list(), [])

    async def test_new_case_never_reads_case_id_before_it_creates_the_case(self) -> None:
        repository = RecordingCaseRepository()
        service = AnalyzeCaseService(LocalDiagnosisClient(), repository)
        source = "검찰청입니다. 지금 안전계좌로 500만원을 송금하세요."
        with patch(
            "ai_api.app.domains.diagnosis.window_ai.service.extract_events",
            new=AsyncMock(return_value=self._extraction(source)),
        ):
            created = await service.analyze(AnalyzeTextRequest(text=source, client_request_id="sequence-test"))

        self.assertEqual(created.disposition, "CASE_CREATED")
        self.assertEqual(repository.operations, [
            "find_by_client_request_id", "next_case_id", "create",
        ])


if __name__ == "__main__":
    unittest.main()
