from __future__ import annotations

import asyncio
import re
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from contracts.user_text import LABELS, user_text
import general_api.app.main as main
from general_api.app.domains.cases.repository import InMemoryCaseRepository


class AtomicAnswerTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.repo = InMemoryCaseRepository()
        self.repo._records.append({'case_id': 'audit', 'context_revision': 1})
        self.repo._customer_questions.append({'case_id': 'audit', 'question_id': 'q1', 'status': 'ASKED',
            'target_field': 'personal_info_shared', 'question_text': '개인정보를 제공했나요?'})

    async def test_concurrent_retries_commit_one_answer_and_receipt(self):
        results = await asyncio.gather(*[
            self.repo.submit_customer_answer('audit', 'q1', '아니요', 'customer', '고객') for _ in range(4)
        ])
        self.assertEqual(len({r['answer_message_id'] for r in results}), 1)
        self.assertEqual(len(self.repo._messages), 2)
        self.assertEqual(len(self.repo._case_facts), 1)
        self.assertEqual(self.repo._messages[0]['content'], '아니요')
        self.assertEqual(self.repo._messages[1]['visibility'], 'AI_PRIVATE')
        self.assertIn('답변: 아니요', self.repo._messages[1]['content'])

    async def test_invalid_or_conflicting_answer_has_no_extra_writes(self):
        with self.assertRaises(KeyError):
            await self.repo.submit_customer_answer('audit', 'missing', '예', 'customer', '고객')
        self.assertEqual(self.repo._messages, [])
        await self.repo.submit_customer_answer('audit', 'q1', '아니요', 'customer', '고객')
        with self.assertRaisesRegex(ValueError, 'CUSTOMER_ANSWER_CONFLICT'):
            await self.repo.submit_customer_answer('audit', 'q1', '예', 'customer', '고객')
        self.assertEqual(len(self.repo._messages), 2)
        self.assertEqual(self.repo._case_facts[0]['value'], '아니요')


class AuditEndpointTest(unittest.TestCase):
    def test_answer_error_cannot_save_a_message_before_validation(self):
        repo = AsyncMock()
        repo.get.return_value = {'case_id': 'audit'}
        with patch.object(main, 'repository', repo), TestClient(main.app) as client:
            for error, status in [(KeyError('missing'), 404), (ValueError('CUSTOMER_ANSWER_CONFLICT'), 409)]:
                repo.submit_customer_answer.side_effect = error
                response = client.post('/api/cases/audit/customer-questions/q1/answer', json={
                    'raw_answer': '예', 'actor_user_id': 'customer', 'actor_display_name': '고객'})
                self.assertEqual(response.status_code, status)
            repo.append_message.assert_not_awaited()
            repo.propose_case_fact.assert_not_awaited()

    def test_export_translates_prose_but_preserves_closure_note(self):
        report = {'sections': [
            {'section_key': 'verified_facts', 'content': {'items': ['personal_info_shared: UNKNOWN']}},
            {'section_key': 'internal_section', 'content': {'text': 'Impersonation/Social Engineering', 'closure_note': 'audit_reference_code: confirmed'}},
        ]}
        blocks = main._report_export_lines('audit', report)
        self.assertIn('개인정보 제공 여부: 확인되지 않음', blocks[1][1])
        self.assertEqual(blocks[2][0], '추가 보고 내용')
        self.assertEqual(blocks[2][1][0], '기관·신분 사칭/심리적 기만')
        self.assertEqual(blocks[2][1][1], '담당자 종결 메모: audit_reference_code: confirmed')

    def test_frontend_and_backend_label_dictionaries_match(self):
        source = (Path(__file__).resolve().parents[3] / 'frontend/src/userText.ts').read_text(encoding='utf-8')
        declaration = source.split('const labels: Record<string, string> = {', 1)[1].split('};', 1)[0]
        frontend = {quoted or bare: value for quoted, bare, value in re.findall(r"(?:'([^']+)'|([a-z_]+)):\s*'([^']*)'", declaration)}
        self.assertEqual(frontend, LABELS)
        self.assertEqual(user_text('Social Engineering / SOCIAL_ENGINEERING / social-engineering'), '심리적 기만 / 심리적 기만 / 심리적 기만')
        self.assertEqual(user_text('https://example.com/personal_info_shared personal_info_shared.pdf my_unknown_id'), 'https://example.com/personal_info_shared personal_info_shared.pdf my_unknown_id')
