import asyncio
import unittest
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi.testclient import TestClient

import general_api.app.main as main
from general_api.app.domains.cases.repository import InMemoryCaseRepository
from general_api.app.domains.cases.mysql_repository import MySqlCaseRepository
from general_api.app.domains.cases.customer_progress import PREFIX, ProgressConflict, progress_items, prepare_progress


class CustomerProgressTest(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryCaseRepository()
        self.repo._records.append({'case_id': 'VP-TEST', 'mode': 'RECOVERY', 'status': 'CLOSED',
            'risk': 'HIGH', 'initial_brief': '', 'created_at': '2026-09-05T10:00:00+09:00',
            'updated_at': '2026-09-05T10:00:00+09:00'})
        self.patch = patch.object(main, 'repository', self.repo)
        self.patch.start()
        self.client = TestClient(main.app)
        self.url = '/api/cases/VP-TEST/customer-progress'

    def tearDown(self):
        self.client.close()
        self.patch.stop()

    def values(self, revision=0, **changes):
        return {'expected_revision': revision, 'status': 'COMPLETED', 'summary': '피해구제 신청 접수를 확인했습니다.',
            'next_action': '추가 제출 요청을 기다려 주세요.', 'reference': '접수번호 TEST-1',
            'confirmed_at': '2026-09-05T10:00:00+09:00', 'updated_by': '담당 직원', **changes}

    def test_guide_click_and_closed_case_do_not_complete_procedures(self):
        self.repo._messages.append({'content': '피해구제 단계 확인: 구제 신청'})
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(all(item['status'] == 'UNKNOWN' for item in response.json()))

    def test_completion_requires_evidence(self):
        for fields in ({'reference': ''}, {'confirmed_at': None}, {'summary': '  '}):
            response = self.client.put(self.url + '/RELIEF', json=self.values(**fields))
            self.assertEqual(response.status_code, 422)
        self.assertEqual(self.repo._actions, [])

    def test_only_recorded_step_completes_and_customer_bank_agree(self):
        response = self.client.put(self.url + '/RELIEF', json=self.values())
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([item['step'] for item in response.json() if item['status'] == 'COMPLETED'], ['RELIEF'])
        for view in ('customer', 'bank'):
            bundle = self.client.get('/api/cases/VP-TEST/bundle', params={'view': view})
            self.assertEqual(bundle.status_code, 200, bundle.text)
            self.assertEqual(bundle.json()['customer_progress'], response.json())
            self.assertEqual(bundle.json()['recent_actions'], [])

    def test_duplicate_confirmation_requests_are_idempotent_and_do_not_complete(self):
        for _ in range(3):
            response = self.client.post(self.url + '/RELIEF/confirmation-request')
            self.assertEqual(response.status_code, 200)
        relief = response.json()[-1]
        self.assertEqual(relief['status'], 'UNKNOWN')
        self.assertTrue(relief['confirmation_requested'])
        self.assertEqual(len(self.repo._actions), 1)
        customer_notice = [item for item in self.repo._messages if item.get('channel') == 'CUSTOMER']
        bank_notice = [item for item in self.repo._messages if item.get('channel') == 'TEAM']
        self.assertEqual(len(customer_notice), 1)
        self.assertEqual(len(bank_notice), 1)
        self.assertIn('처리 결과 확인 요청을 담당자에게 전달했습니다', customer_notice[0]['content'])
        self.assertIn('고객이', bank_notice[0]['content'])
        self.assertIn('담당자 결과 등록이 필요합니다', bank_notice[0]['content'])
        customer_bundle = self.client.get('/api/cases/VP-TEST/bundle', params={'view': 'customer'}).json()
        bank_bundle = self.client.get('/api/cases/VP-TEST/bundle', params={'view': 'bank'}).json()
        self.assertTrue(any('담당자에게 전달했습니다' in item['content'] for item in customer_bundle['recent_messages']))
        self.assertFalse(any('담당자 결과 등록이 필요합니다' in item['content'] for item in customer_bundle['recent_messages']))
        self.assertTrue(any('담당자 결과 등록이 필요합니다' in item['content'] for item in bank_bundle['recent_messages']))
        response = self.client.put(self.url + '/RELIEF', json=self.values(1))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()[-1]['confirmation_requested'])

    def test_stale_edit_conflicts_and_latest_correction_wins(self):
        self.client.put(self.url + '/RELIEF', json=self.values())
        self.assertEqual(self.client.put(self.url + '/RELIEF', json=self.values()).status_code, 409)
        response = self.client.put(self.url + '/RELIEF', json=self.values(1, status='UNKNOWN', summary='접수 여부 재확인 중', reference='', confirmed_at=None))
        self.assertEqual(response.json()[-1]['status'], 'UNKNOWN')
        self.assertEqual(len(self.repo._actions), 2)

    def test_generic_action_api_cannot_forge_or_change_progress(self):
        response = self.client.post('/api/cases/VP-TEST/actions', json={'action_type': PREFIX + 'RELIEF', 'note': '{}', 'actor_type': 'BANK_STAFF'})
        self.assertEqual(response.status_code, 422)
        self.client.put(self.url + '/RELIEF', json=self.values())
        action_id = self.repo._actions[0]['action_id']
        response = self.client.patch('/api/cases/VP-TEST/actions/' + action_id, json={'status': 'COMPLETED', 'updated_by': '직원'})
        self.assertEqual(response.status_code, 422)

    def test_unknown_case_and_step_are_rejected(self):
        self.assertEqual(self.client.get('/api/cases/missing/customer-progress').status_code, 404)
        self.assertEqual(self.client.post(self.url + '/FAKE/confirmation-request').status_code, 422)

    def test_ai_reads_same_progress_and_only_published_information(self):
        self.client.put(self.url + '/RELIEF', json=self.values())
        self.repo._verifications.extend([
            {'case_id': 'VP-TEST', 'target': '공개 기관', 'status': 'COMPLETED', 'customer_visible': True, 'result_summary': '공개 확인 결과'},
            {'case_id': 'VP-TEST', 'target': '비공개 기관', 'status': 'COMPLETED', 'customer_visible': False, 'result_summary': '내부 비밀'},
        ])
        self.repo._attachments.extend([
            {'case_id': 'VP-TEST', 'attachment_id': 'public-file', 'original_name': '고객 증빙.pdf', 'visibility': 'CUSTOMER'},
            {'case_id': 'VP-TEST', 'attachment_id': 'private-file', 'original_name': '직원 전용.pdf', 'visibility': 'BANK_INTERNAL'},
        ])
        generator = AsyncMock(return_value={'content': '현재 접수 확인 기록이 있습니다.', 'model_mode': 'test'})
        with patch.object(main.service.ai_client, 'generate_case_copilot_reply', generator):
            response = self.client.post('/api/cases/VP-TEST/ai/customer-replies', json={
                'prompt': '신청됐나요?', 'requester_user_id': 'customer', 'requester_display_name': '고객',
                'reply_to_message_id': 'msg-question',
            })
        self.assertEqual(response.status_code, 201, response.text)
        payload = generator.await_args.args[0]
        self.assertIn('TEST-1', payload['customer_progress'][-1])
        self.assertIn('담당자 완료 확인', payload['customer_progress'][-1])
        self.assertEqual(payload['attachment_summaries'], ['고객 증빙.pdf'])
        self.assertEqual(len(payload['published_verification_results']), 1)
        self.assertNotIn('내부 비밀', str(payload))
        self.assertNotIn('직원 전용', str(payload))


class ProgressSqlTransactionTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.cursor = AsyncMock()
        self.cursor.fetchone.return_value = ('VP-TEST',)
        self.cursor.fetchall.return_value = []
        self.connection = MagicMock()
        self.connection.cursor.return_value.__aenter__ = AsyncMock(return_value=self.cursor)
        self.connection.cursor.return_value.__aexit__ = AsyncMock(return_value=False)
        self.connection.commit = AsyncMock()
        self.connection.rollback = AsyncMock()
        pool = MagicMock()
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=self.connection)
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        self.repo = MySqlCaseRepository()
        self.repo._get_pool = AsyncMock(return_value=pool)

    async def test_progress_read_and_write_share_case_lock_transaction(self):
        result = await self.repo.create_action('VP-TEST', {'_progress_command': {'step': 'RELIEF', 'request_confirmation': True}})
        calls = self.cursor.execute.await_args_list
        self.assertIn('FOR UPDATE', calls[0].args[0])
        self.assertIn('SELECT action_type, note', calls[1].args[0])
        self.assertIn('INSERT INTO actions', calls[2].args[0])
        self.assertTrue(progress_items([result])[-1].confirmation_requested)
        self.connection.commit.assert_awaited_once()

    async def test_duplicate_request_releases_lock_without_inserting(self):
        record = prepare_progress([], {'step': 'RELIEF', 'request_confirmation': True}, '2026-09-05T10:00:00')
        self.cursor.fetchall.return_value = [(record['action_type'], record['note'])]
        await self.repo.create_action('VP-TEST', {'_progress_command': {'step': 'RELIEF', 'request_confirmation': True}})
        self.connection.rollback.assert_awaited_once()
        self.assertFalse(any('INSERT' in call.args[0] for call in self.cursor.execute.await_args_list))

    async def test_stale_write_rolls_back(self):
        record = prepare_progress([], {'step': 'RELIEF', 'request_confirmation': True}, '2026-09-05T10:00:00')
        self.cursor.fetchall.return_value = [(record['action_type'], record['note'])]
        with self.assertRaises(ProgressConflict):
            await self.repo.create_action('VP-TEST', {'_progress_command': {'step': 'RELIEF', 'request_confirmation': False, 'values': {'expected_revision': 0}}})
        self.connection.rollback.assert_awaited_once()

    async def test_concurrent_requests_create_one_pending_request(self):
        repo = InMemoryCaseRepository()
        repo._records.append({'case_id': 'VP-TEST'})
        await asyncio.gather(*(repo.create_action('VP-TEST', {'_progress_command': {'step': 'RELIEF', 'request_confirmation': True}}) for _ in range(8)))
        self.assertEqual(len(repo._actions), 1)
