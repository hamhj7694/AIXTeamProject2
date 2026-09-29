import asyncio
import json
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import general_api.app.main as main
from ai_api.app.domains.case_support.context_fact_extraction_service import ContextFactExtractionService
from contracts.public_api.collaboration import PublicAiInvocationRequest, PublicGuidanceRequest
from contracts.public_api.case_activity import to_public_message
from general_api.app.domains.cases.repository import InMemoryCaseRepository
from general_api.app.domains.cases.case_context_v2_repository import InMemoryCaseContextV2Repository
from general_api.app.domains.cases.copilot_state import read_operational_state
from general_api.app.domains.cases.copilot_tasks import apply_task_intents
from general_api.app.domains.cases.copilot_jobs import CopilotJobs


class CopilotWorkflowTest(unittest.IsolatedAsyncioTestCase):
    def test_distinct_task_buttons_share_a_tool_without_disappearing(self):
        raw = [dict(action_key='CUSTOMER_QUESTION', kind='TOOL', target_channel='TEAM',
                    target_type='TASK', target_id=task_id, expected_version=1)
               for task_id in ('task-one', 'task-two')]
        actions = main.normalize_public_recommended_actions(raw, 'TEAM')
        self.assertEqual([action.target_id for action in actions], ['task-one', 'task-two'])
        self.assertEqual(main.normalize_public_recommended_actions(raw, 'CUSTOMER'), [])

    async def asyncSetUp(self):
        self.repo = InMemoryCaseRepository()
        fixture = Path(__file__).resolve().parents[2] / 'contracts/ai_internal/fixtures/diagnosis.high.v1.json'
        self.repo._records = [{'case_id': 'C', 'context_revision': 1, 'status': 'TRIAGE',
                              'diagnosis': json.loads(fixture.read_text(encoding='utf-8'))['response']}]
        self.store = InMemoryCaseContextV2Repository(self.repo)
        self.repo_patch = patch.object(main, 'repository', self.repo)
        self.repo_patch.start()
        self.addCleanup(self.repo_patch.stop)
        self.perm = patch.object(main, 'require_context_v2_member', new=AsyncMock(return_value=None))
        self.perm.start()
        self.addCleanup(self.perm.stop)
        self.no_network = patch.object(main.service.ai_client, 'generate_case_copilot_reply', new=AsyncMock(side_effect=AssertionError('unexpected provider call')))
        self.no_network.start()
        self.addCleanup(self.no_network.stop)

    async def state(self):
        return await read_operational_state(self.repo, self.store, 'C')

    async def staff(self, content, extract=False):
        message = await self.repo.append_message('C', dict(actor_type='BANK_STAFF', actor_user_id='staff',
            actor_display_name='담당자', content=content, channel='TEAM', audience='BANK_INTERNAL', visibility='BANK_INTERNAL', message_kind='CHAT'))
        if extract:
            with patch.object(main.service.ai_client, 'extract_context_facts', new=AsyncMock(side_effect=ContextFactExtractionService().extract)):
                await main.enqueue_context_extraction(message)
                await main.process_message_context_extraction('C', message['message_id'])
        return message

    def create(self):
        return dict(operation='CREATE', title='고객 정보 제공 여부 질문', description='이미 제공한 항목의 종류만 질문한다.',
                    task_type='CUSTOMER_CONTACT', priority='HIGH', evidence_ids=['analysis'])

    async def test_task_create_retry_cancel_and_same_evidence_suppressed(self):
        before = await self.state()
        receipts, buttons = await apply_task_intents(self.store, before, [self.create()], 'staff', [])
        self.assertEqual(receipts[0]['status'], 'APPLIED')
        task = (await self.state()).resources.tasks[0]
        self.assertEqual(task.source, 'AI_RECOMMENDED')
        self.assertEqual(task.created_by, 'system:case-copilot')
        self.assertTrue(task.evidence_refs)
        self.assertEqual(before.guidance_key(), (await self.state()).guidance_key())
        await apply_task_intents(self.store, await self.state(), [self.create()], 'staff', [])
        self.assertEqual(len((await self.state()).tasks), 1)
        message = await self.staff('고객 정보 제공 여부 질문 업무 삭제해 줘')
        result, _ = await apply_task_intents(self.store, await self.state(), [dict(operation='CANCEL', target_id=task.task_id,
            expected_version=1, source_message_id=message['message_id'])], 'staff', [message['message_id']], allow_cancel=True)
        self.assertEqual(result[0]['status'], 'APPLIED')
        result, _ = await apply_task_intents(self.store, await self.state(), [self.create()], 'staff', [])
        self.assertEqual(result[0]['status'], 'SUPPRESSED')
        self.assertEqual(len((await self.state()).tasks), 1)

    async def test_distinct_official_targets_are_separate_tasks(self):
        state = await self.state()
        base = dict(operation='CREATE', description='해당 기관 공식 연락처로 소속을 대조한다.',
                    task_type='INSTITUTION_VERIFICATION', priority='HIGH', evidence_ids=['analysis'])
        receipts, _ = await apply_task_intents(self.store, state, [
            {**base, 'title': '검찰 소속 공식 확인'}, {**base, 'title': '금융감독원 소속 공식 확인'}], 'staff', [])
        self.assertEqual([item['status'] for item in receipts], ['APPLIED', 'APPLIED'])
        self.assertEqual(len((await self.state()).tasks), 2)

    async def test_completion_requires_report_and_unambiguous_target(self):
        await apply_task_intents(self.store, await self.state(), [self.create()], 'staff', [])
        task = (await self.state()).tasks[0]
        for content in ['그거 완료했어', '고객 질문 완료할까?', '고객 질문 아직 완료 못했어']:
            message = await self.staff(content)
            result, _ = await apply_task_intents(self.store, await self.state(), [dict(operation='COMPLETE', target_id=task['task_id'], expected_version=1,
                source_message_id=message['message_id'], result_summary='질문 완료')], 'staff', [message['message_id']])
            self.assertEqual(result[0]['status'], 'FAILED', content)
        message = await self.staff('고객 정보 제공 여부 질문 업무 완료했어')
        result, _ = await apply_task_intents(self.store, await self.state(), [dict(operation='COMPLETE', target_id=task['task_id'], expected_version=1,
            source_message_id=message['message_id'], result_summary='직원 질문 완료 보고')], 'staff', [message['message_id']])
        self.assertEqual(result[0]['status'], 'APPLIED')
        saved = (await self.state()).resources.tasks[0]
        self.assertEqual(saved.completed_by, 'staff')
        self.assertEqual(saved.status, 'COMPLETED')
        self.assertTrue(saved.completed_at)

    async def test_transfer_add_correction_repeat_and_demand(self):
        for text, total in [('500만원 송금 확인됨', 5000000), ('200만원 추가', 7000000),
                            ('500이 아니라 300', 5000000),
                            ('300만원 송금했어', 5000000), ('900만원 송금하라고 요구함', 5000000)]:
            await self.staff(text, extract=True)
            state = await self.state()
            self.assertEqual(state.payload()['money_events']['reported_outgoing_krw'], total, text)
        active = (await self.state()).facts
        self.assertTrue(any(f.get('staff_reported') for f in active))
        self.assertIn('transfer_status', main.question_fields_covered_by_case(active, []))

    async def test_unknown_denial_and_request_do_not_become_actual_performance(self):
        for text in ['500만원 송금했는지 모르겠어', '원격제어 앱 설치했는지 확인해야 해',
                     'OTP 전달했는지 모르겠어', '개인정보 제공하라고 요구했어']:
            await self.staff(text, extract=True)
        state = await self.state()
        self.assertEqual(state.payload()['money_events']['reported_outgoing_krw'], 0)
        self.assertFalse(any(f.get('staff_reported') for f in state.facts))
        for text in ['개인정보 제공 안했어', '인증정보 전달 안했어', '송금 안했어', '원격제어 앱 설치 안했어']:
            await self.staff(text, extract=True)
        covered = main.question_fields_covered_by_case((await self.state()).facts, [])
        self.assertTrue({'transfer_status', 'personal_information_exposure', 'authentication_information_exposure', 'remote_control_app'} <= covered)

    async def test_persist_buttons_receipts_latest_state_and_privacy(self):
        provider = AsyncMock(side_effect=[dict(content='질문 업무를 준비합니다.', model_mode='test', task_intents=[self.create()]),
                                         dict(content='고객 질문 업무를 등록했습니다.', model_mode='test', recommended_actions=[])])
        request = PublicAiInvocationRequest(prompt='다음 무슨 조치 취해야 해?', channel='TEAM', requester_user_id='staff', requester_display_name='담당자', client_request_id='invoke-1')
        with patch.object(main.service.ai_client, 'generate_case_copilot_reply', provider):
            reply = await main.invoke_case_copilot('C', request)
            duplicate = await main.invoke_case_copilot('C', request)
        self.assertEqual(provider.await_count, 2)
        self.assertEqual(reply.message_id, duplicate.message_id)
        saved = (await self.repo.list_messages('C'))[-1]
        public = to_public_message(saved)
        self.assertEqual(public.recommended_actions, reply.recommended_actions)
        self.assertEqual(public.mutation_results[0]['status'], 'APPLIED')
        self.assertEqual(provider.await_args.args[0]['case_state']['tasks'][0]['task_id'], reply.recommended_actions[0].target_id)
        customer = to_public_message({**saved, 'channel': 'CUSTOMER', 'visibility': 'CUSTOMER'})
        self.assertEqual(customer.recommended_actions, [])
        self.assertEqual(customer.mutation_results, [])

    async def test_reply_persists_only_one_recommended_tool(self):
        provider = AsyncMock(return_value=dict(
            content='고객의 정보 제공 여부를 확인하세요.', model_mode='test',
            recommended_actions=[
                dict(action_key='CUSTOMER_QUESTION', kind='TOOL', target_channel='TEAM'),
                dict(action_key='OFFICIAL_VERIFICATION', kind='TOOL', target_channel='TEAM'),
            ],
        ))
        request = PublicAiInvocationRequest(
            prompt='지금 무엇을 해야 해?', channel='TEAM', requester_user_id='staff',
            requester_display_name='담당자', client_request_id='one-tool',
        )
        with patch.object(main.service.ai_client, 'generate_case_copilot_reply', provider):
            reply = await main.invoke_case_copilot('C', request)
        saved = to_public_message((await self.repo.list_messages('C'))[-1])
        self.assertEqual([item.action_key for item in reply.recommended_actions], ['CUSTOMER_QUESTION'])
        self.assertEqual(saved.recommended_actions, reply.recommended_actions)

    async def test_guidance_durable_dedup_and_self_loop(self):
        req = PublicGuidanceRequest(actor_user_id='staff')
        a, b = await asyncio.gather(main.ensure_copilot_guidance('C', req), main.ensure_copilot_guidance('C', req))
        self.assertEqual(a['job_id'], b['job_id'])
        jobs = CopilotJobs(self.repo)
        candidate = (await jobs.pending())[0]
        provider = AsyncMock(return_value=dict(content='고객에게 실제 정보 제공 여부를 질문하세요.', model_mode='test', recommended_actions=[dict(action_key='CUSTOMER_QUESTION',kind='TOOL',target_channel='TEAM')]))
        with patch.object(main.service.ai_client, 'generate_case_copilot_reply', provider):
            await asyncio.gather(main.process_copilot_guidance(candidate), main.process_copilot_guidance(candidate))
            await main.process_copilot_guidance(candidate)
        self.assertEqual(provider.await_count, 1)
        self.assertIn('현 상황 한 줄', provider.await_args.args[0]['prompt'])
        self.assertIn('행동 한 가지만', provider.await_args.args[0]['prompt'])
        self.assertEqual(len(await self.repo.list_messages('C')), 1)
        self.assertEqual((await main.ensure_copilot_guidance('C', req))['status'], 'COMPLETED')

    async def test_changed_case_guidance_asks_for_fresh_one_step(self):
        state = await self.state()
        jobs = CopilotJobs(self.repo)
        await jobs.enqueue('C', state.guidance_key(), 'CHANGE', state.revision, 'staff')
        candidate = (await jobs.pending())[0]
        provider = AsyncMock(return_value=dict(
            content='**현 상황:** 고객 답변이 반영됐습니다.\n**지금 할 일:** 답변을 확인하세요.',
            model_mode='test', recommended_actions=[],
        ))
        with patch.object(main.service.ai_client, 'generate_case_copilot_reply', provider):
            await main.process_copilot_guidance(candidate)
        self.assertEqual(provider.await_count, 1)
        self.assertIn('새로 반영된 고객 답변', provider.await_args.args[0]['prompt'])
        self.assertIn('이전 안내를 반복하지 마세요', provider.await_args.args[0]['prompt'])

    async def test_stale_job_superseded_and_provider_failure_retryable(self):
        await main.ensure_copilot_guidance('C', PublicGuidanceRequest(actor_user_id='staff'))
        job = (await CopilotJobs(self.repo).pending())[0]
        await self.staff('500만원 송금 확인됨', extract=True)
        await main.process_copilot_guidance(job)
        self.assertEqual(self.repo._copilot_jobs[('C',job['dedupe_key'])]['status'], 'SUPERSEDED')
        await main.ensure_copilot_guidance('C', PublicGuidanceRequest(actor_user_id='staff'))
        job = (await CopilotJobs(self.repo).pending())[0]
        with patch.object(main.service.ai_client, 'generate_case_copilot_reply', new=AsyncMock(side_effect=main.AiServiceError('provider unavailable'))):
            await main.process_copilot_guidance(job)
        self.assertEqual(self.repo._copilot_jobs[('C',job['dedupe_key'])]['status'], 'FAILED')
        self.assertFalse(any(m['actor_type'] == 'BANK_AGENT' for m in await self.repo.list_messages('C')))
