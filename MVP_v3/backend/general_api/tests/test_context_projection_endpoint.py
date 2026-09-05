import json
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import general_api.app.main as general_main
from general_api.app.domains.cases.context_projection_repository import ProjectionClaim
from general_api.app.domains.cases.mysql_repository import MySqlCaseRepository


class ContextProjectionEndpointTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.original_repository = general_main.repository
        self.original_ai = general_main.service.ai_client
        fixture = Path(__file__).resolve().parents[2] / 'contracts/ai_internal/fixtures/diagnosis.high.v1.json'
        self.case = {
            'case_id': 'VP-CACHE', 'context_revision': 7,
            'diagnosis': json.loads(fixture.read_text(encoding='utf-8'))['response'],
            'victim_transfer_status': 'UNKNOWN',
        }
        self.repository = MySqlCaseRepository()
        self.repository.get = AsyncMock(return_value=self.case)
        self.repository.list_case_facts = AsyncMock(return_value=[])
        self.repository.list_customer_questions = AsyncMock(return_value=[])
        self.repository.list_verifications = AsyncMock(return_value=[])
        self.repository.list_actions = AsyncMock(return_value=[])
        general_main.repository = self.repository
        self.ai = AsyncMock()
        general_main.service.ai_client = self.ai
        self.payload = {
            'case_id': 'VP-CACHE',
            'case_brief': {'summary': '현재 요약', 'incident_type': '기관 사칭', 'risk_level': 'HIGH', 'risk_score': 0, 'next_checks': []},
            'case_context': {'situation_summary': '현재 요약'},
            'recommended_questions': [], 'unresolved_items': [], 'warnings': [],
        }

    async def asyncTearDown(self):
        general_main.repository = self.original_repository
        general_main.service.ai_client = self.original_ai

    async def test_cached_revision_does_not_call_ai(self):
        store = AsyncMock()
        store.claim.return_value = ProjectionClaim('CACHED', 7, last_success_revision=7, last_success_payload=self.payload)
        with patch.object(general_main, 'ContextProjectionRepository', return_value=store):
            response = await general_main.get_case_support_snapshot('VP-CACHE')
        self.assertTrue(response.available)
        self.assertEqual(response.projection_status, 'CURRENT')
        self.assertEqual(response.projection_revision, 7)
        self.ai.build_case_support_snapshot.assert_not_awaited()

    async def test_claimed_revision_is_saved_before_return(self):
        store = AsyncMock()
        store.claim.return_value = ProjectionClaim('CLAIMED', 7, lease_token='owner')
        store.complete.return_value = True
        self.ai.build_case_support_snapshot.return_value = self.payload
        with patch.object(general_main, 'ContextProjectionRepository', return_value=store):
            response = await general_main.get_case_support_snapshot('VP-CACHE')
        self.assertEqual(response.projection_status, 'CURRENT')
        store.complete.assert_awaited_once_with('VP-CACHE', 7, 'owner', self.payload)

    async def test_in_progress_and_failure_keep_last_success(self):
        store = AsyncMock()
        store.claim.return_value = ProjectionClaim('IN_PROGRESS', 7, last_success_revision=5, last_success_payload=self.payload)
        with patch.object(general_main, 'ContextProjectionRepository', return_value=store):
            response = await general_main.get_case_support_snapshot('VP-CACHE')
        self.assertTrue(response.available)
        self.assertEqual(response.projection_status, 'UPDATING')
        self.assertEqual(response.projection_revision, 5)
        self.assertTrue(any('직전 정상' in warning for warning in response.warnings))
