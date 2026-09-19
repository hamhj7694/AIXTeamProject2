import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from contracts.ai_internal.case_copilot import CaseCopilotInput
from contracts.public_api.case_context_v2 import PublicCaseContextResourcesV2
from general_api.app.domains.cases.case_retrieval import (
    CaseRecord, CaseRetriever, collect_records, merge_support_records,
    retrieve_context, similar_question, workspace_records,
    bank_source_context,
)
from contracts.question_target import encode_follow_up_target
from general_api.app.domains.cases.repository import InMemoryCaseRepository
import general_api.app.main as main


class CaseRetrievalTest(unittest.TestCase):
    def test_korean_synonyms_retrieve_old_relevant_record(self):
        records = [CaseRecord('a', 'old', '대화', '고객은 백만원을 이체했고 영수증을 제출했습니다.', 'CUSTOMER')]
        records += [CaseRecord('a', str(i), '대화', '휴대폰 앱 설치 여부를 확인합니다.', 'CUSTOMER') for i in range(40)]
        hits = CaseRetriever().search('a', 'CUSTOMER', '송금 영수증 제출했었나요?', records)
        self.assertEqual(hits[0]['source_id'], 'old')

    def test_case_and_audience_are_filtered_before_search(self):
        records = [CaseRecord('a', 'public', '대화', '송금 영수증', 'CUSTOMER'),
                   CaseRecord('a', 'internal', '결정', '송금 영수증 내부', 'BANK_INTERNAL'),
                   CaseRecord('b', 'foreign', '대화', '송금 영수증', 'CUSTOMER'),
                   CaseRecord('a', 'private', '대화', '송금 영수증', 'AI_PRIVATE')]
        search = CaseRetriever()
        self.assertEqual([h['source_id'] for h in search.search('a', 'CUSTOMER', '송금 영수증', records)], ['public'])
        self.assertEqual({h['source_id'] for h in search.search('a', 'BANK_INTERNAL', '송금 영수증', records)}, {'public', 'internal'})

    def test_edits_and_deletions_replace_cached_index(self):
        search = CaseRetriever(max_indexes=2)
        before = [CaseRecord('a', 'id', '업무', '지급정지 완료')]
        self.assertTrue(search.search('a', 'BANK_INTERNAL', '지급정지', before))
        after = [CaseRecord('a', 'id', '업무', '지급정지 취소')]
        self.assertIn('취소', search.search('a', 'BANK_INTERNAL', '지급정지', after)[0]['text'])
        self.assertEqual(search.search('a', 'BANK_INTERNAL', '지급정지', []), [])
        for key in ('b', 'c', 'd'):
            search.search(key, 'CUSTOMER', '조회', [])
        self.assertEqual(len(search._indexes), 2)

    def test_empty_and_irrelevant_results_do_not_invent_evidence(self):
        self.assertEqual(retrieve_context('a', '우주선 항해', [CaseRecord('a', 'id', '업무', '지급정지 확인')]), [])

    def test_search_budget(self):
        records = [CaseRecord('a', str(i), '업무', '송금 ' * 1000) for i in range(30)]
        hits = CaseRetriever().search('a', 'BANK_INTERNAL', '송금', records, limit=999)
        self.assertEqual(len(hits), 6)
        self.assertTrue(all(len(h['text']) <= 750 for h in hits))

    def test_generated_answers_and_unpublished_questions_are_not_customer_evidence(self):
        messages = [dict(message_id='ai', visibility='CUSTOMER', message_kind='AI_RESPONSE', content='허위 완료'),
                    dict(message_id='private', visibility='AI_PRIVATE', content='개인 메모')]
        questions = [dict(question_id='pending', status='PENDING', question_text='아직 미발송'),
                     dict(question_id='asked', status='ANSWERED', question_text='송금했나요?', answer_text='아니요')]
        records = collect_records('a', messages=messages, questions=questions, customer=True)
        self.assertEqual([r.source_id for r in records], ['asked'])
        self.assertIn('사실 확정 아님', records[0].text)

    def test_lexical_duplicate_guard_is_conservative(self):
        self.assertTrue(similar_question('어제 계좌로 이체하셨나요?', '어제 계좌로 송금하셨나요?'))
        self.assertFalse(similar_question('개인정보를 제공하셨나요?', '인증번호를 제공하셨나요?'))
        self.assertFalse(similar_question('네?', '네?'))


class RetrievalWiringTest(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryCaseRepository()
        self.repo._records = [{'case_id': 'VP-RAG', 'context_revision': 1, 'initial_brief': '', 'status': 'TRIAGE'}]
        self.repo._members = [{'case_id': 'VP-RAG', 'user_id': 'staff', 'role': 'REVIEWER', 'display_name': '담당자', 'status': 'ACTIVE'}]
        self.repo_patch = patch.object(main, 'repository', self.repo)
        self.repo_patch.start()
        self.ai = AsyncMock(return_value={'content': '테스트 응답', 'model_mode': 'TEST_ONLY'})
        self.ai_patch = patch.object(main.service.ai_client, 'generate_case_copilot_reply', self.ai)
        self.ai_patch.start()
        self.client = TestClient(main.app)

    def tearDown(self):
        self.client.close()
        self.ai_patch.stop()
        self.repo_patch.stop()

    def test_bank_receives_staff_records_but_customer_does_not(self):
        response = self.client.post('/api/cases/VP-RAG/context-v2/tasks?actor_user_id=staff', json={
            'client_request_id': 'task-rag-001', 'task_type': 'OTHER', 'priority': 'NORMAL',
            'title': '계좌 내부 검토', 'description': '은행 내부 제한 정보',
        })
        self.assertEqual(response.status_code, 201, response.text)
        bank = self.client.post('/api/cases/VP-RAG/ai/invocations', json={
            'prompt': '계좌 내부 검토 진행 상황', 'channel': 'TEAM', 'requester_user_id': 'staff', 'requester_display_name': '담당자',
        })
        self.assertEqual(bank.status_code, 201, bank.text)
        bank_input = self.ai.await_args.args[0]
        parsed_bank_input = CaseCopilotInput.model_validate(bank_input)
        self.assertEqual(parsed_bank_input.requester_user_id, 'staff')
        self.assertEqual(parsed_bank_input.requester_display_name, '담당자')
        self.assertEqual(parsed_bank_input.requester_role, 'REVIEWER')
        self.assertIn('은행 내부 제한 정보', ' '.join(bank_input['staff_context']))
        self.assertTrue(bank_input['retrieved_context'])
        customer = self.client.post('/api/cases/VP-RAG/ai/customer-replies', json={'prompt': '계좌 내부 검토 진행 상황', 'requester_user_id': 'customer', 'requester_display_name': '고객', 'reply_to_message_id': 'message-customer'})
        self.assertEqual(customer.status_code, 201, customer.text)
        customer_input = self.ai.await_args.args[0]
        CaseCopilotInput.model_validate(customer_input)
        self.assertNotIn('은행 내부 제한 정보', str(customer_input))
        self.assertEqual(customer_input['retrieved_context'], [])
        self.assertNotIn('source_context', customer_input)

    def test_staff_confirmation_reaches_support_without_rewriting_legacy_fact(self):
        store = main.case_context_v2_repository()
        fact = asyncio.run(store.create_fact('VP-RAG', {
            'client_request_id': 'fact-rag-001', 'semantic_key': 'transfer.actual.status',
            'display_label': '실제 송금 여부', 'value': {'status': 'NO'}, 'display_value': '송금하지 않았음',
        }, 'staff'))
        asyncio.run(store.review_fact('VP-RAG', fact.fact_id, 1, 'CONFIRM', '담당자 거래 확인', 'staff'))
        resources = asyncio.run(store.list_resources('VP-RAG'))
        legacy = [{'fact_id': 'old', 'field': 'transfer_status', 'value': 'YES', 'status': 'PROPOSED'}]
        facts, _ = merge_support_records(resources, legacy, [])
        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0]['status'], 'CONFIRMED')
        self.assertEqual(legacy[0]['value'], 'YES')
        self.assertIn('transfer_status', main.build_question_recommendation_context(facts, [])['confirmed_fields'])

    def test_bank_production_input_preserves_source_status_evidence_and_freshness(self):
        store = main.case_context_v2_repository()
        fact = asyncio.run(store.create_fact('VP-RAG', {
            'client_request_id': 'typed-fact-001', 'semantic_key': 'transfer.actual.status',
            'display_label': '송금', 'value': {'status': 'TRANSFERRED', 'amount_krw': 10_000_000},
            'display_value': '1,000만원 송금함',
            'evidence_refs': [{'type': 'QUESTION_ANSWER', 'id': 'msg-answer', 'revision': 1}],
        }, 'customer-answer', source_kind='CUSTOMER_STATEMENT'))
        confirmed = asyncio.run(store.review_fact('VP-RAG', fact.fact_id, 1, 'CONFIRM', '진술 확인', 'staff'))
        self.repo._customer_questions = [dict(question_id='cq-parent', case_id='VP-RAG', target_field='transfer_status',
            question_text='송금하셨나요?', status='ANSWERED', answer_text='기억이 잘 안 나요', sequence=1,
            created_at='2026-09-18T01:00:00Z', answered_at='2026-09-18T02:00:00Z'),
            dict(question_id='cq-child', case_id='VP-RAG', target_field=encode_follow_up_target('transfer_status', 'cq-parent'),
            question_text='거래내역을 확인할 수 있나요?', status='ANSWERED', answer_text='1,000만원 송금했어요', sequence=2,
            answer_message_id='msg-answer', answered_at='2026-09-18T03:00:00Z')]
        self.repo._messages = [dict(message_id='old-ai', case_id='VP-RAG', actor_type='BANK_AGENT',
            content='없는 거래 영수증이 확인되었습니다', message_kind='AI_RESPONSE', visibility='BANK_INTERNAL', channel='TEAM')]
        response = self.client.post('/api/cases/VP-RAG/ai/invocations', json={
            'prompt': '송금 근거를 설명해 주세요', 'channel': 'TEAM', 'requester_user_id': 'staff', 'requester_display_name': '담당자',
        })
        self.assertEqual(response.status_code, 201, response.text)
        payload = self.ai.await_args.args[0]
        parsed = CaseCopilotInput.model_validate(payload)
        transmitted = parsed.source_context.facts[0]
        self.assertEqual(transmitted.model_dump(), confirmed.model_dump())
        self.assertEqual((transmitted.source_kind, transmitted.status), ('CUSTOMER_STATEMENT', 'CONFIRMED'))
        self.assertEqual(parsed.source_context.questions[1].canonical_scope, 'transfer_status')
        self.assertEqual(parsed.source_context.questions[1].parent_question_id, 'cq-parent')
        self.assertIsNotNone(parsed.source_context.questions[1].answered_at)
        self.assertEqual(parsed.source_context.messages, [])
        self.assertNotIn('없는 거래 영수증', str(payload['recent_conversation']))
        self.assertNotIn('source_context', response.json())

    def test_superseded_records_and_completed_verification_are_transmitted_without_source_promotion(self):
        store = main.case_context_v2_repository()
        old = asyncio.run(store.create_fact('VP-RAG', {
            'client_request_id': 'typed-old', 'semantic_key': 'offender.claimed_organization',
            'display_label': '기관', 'value': {'text': '검찰청'}, 'display_value': '검찰청 주장',
        }, 'staff'))
        asyncio.run(store.review_fact('VP-RAG', old.fact_id, old.version, 'CONFIRM', '기존 사실 확인', 'staff'))
        new = asyncio.run(store.create_fact('VP-RAG', {
            'client_request_id': 'typed-new', 'semantic_key': 'offender.claimed_organization',
            'display_label': '기관', 'value': {'text': '기관 사칭'}, 'display_value': '기관 사칭 확인',
            'evidence_refs': [{'type': 'VERIFICATION_RESULT', 'id': 'verification', 'revision': 2}],
        }, 'staff', source_kind='OFFICIAL_VERIFICATION'))
        asyncio.run(store.review_fact('VP-RAG', new.fact_id, 1, 'CONFIRM', '확인 결과', 'staff', old.fact_id))
        self.repo._verifications = [dict(verification_task_id='verification', case_id='VP-RAG', target='검찰청',
            claim='기관 실재', status='COMPLETED', result_summary='기관 사칭 확인', version=2,
            verified_by='staff', evidence_url='https://example.invalid/result', updated_at='2026-09-18T03:00:00Z')]
        resources = asyncio.run(store.list_resources('VP-RAG'))
        context = bank_source_context('VP-RAG', resources, facts=[], questions=[], messages=[], verifications=self.repo._verifications)
        by_id = {f.fact_id: f for f in context.facts}
        self.assertEqual(by_id[old.fact_id].status, 'SUPERSEDED')
        self.assertEqual(by_id[old.fact_id].supersedes_fact_id, new.fact_id)
        self.assertEqual(by_id[new.fact_id].source_kind, 'OFFICIAL_VERIFICATION')
        self.assertEqual(context.verifications[0].version, 2)
        self.assertEqual(context.verifications[0].verified_by, 'staff')
        self.assertIsNotNone(context.verifications[0].updated_at)

    def test_cross_case_context_rejected_and_record_limits_are_explicit(self):
        resources = PublicCaseContextResourcesV2(case_id='VP-RAG', context_revision=1)
        messages = [dict(message_id=f'm-{i}', case_id='VP-RAG', actor_type='CUSTOMER', content='송금했어요') for i in range(25)]
        context = bank_source_context('VP-RAG', resources, facts=[], questions=[], verifications=[], messages=messages)
        self.assertEqual(len(context.messages), 20)
        self.assertTrue(context.truncated)
        messages[0]['case_id'] = 'OTHER'
        with self.assertRaises(ValueError):
            bank_source_context('VP-RAG', resources, facts=[], questions=[], verifications=[], messages=messages)

    def test_source_messages_preserve_human_identity_and_conversation_boundary(self):
        resources = PublicCaseContextResourcesV2(case_id='VP-RAG', context_revision=1)
        messages = [dict(
            message_id='staff-introduction', case_id='VP-RAG', actor_type='BANK_STAFF',
            actor_user_id='staff', actor_display_name='김담당', actor_role='REVIEWER',
            channel='TEAM', audience='BANK_INTERNAL', visibility='BANK_INTERNAL',
            content='제 이름은 김담당입니다.',
        ), dict(
            message_id='customer-report', case_id='VP-RAG', actor_type='CUSTOMER',
            actor_user_id='customer', actor_display_name='이고객', actor_role='CUSTOMER',
            channel='CUSTOMER', audience='CUSTOMER', visibility='CUSTOMER',
            content='상대방은 박사칭이라고 했어요.',
        )]

        context = bank_source_context(
            'VP-RAG', resources, facts=[], questions=[], verifications=[], messages=messages,
        )

        staff, customer = context.messages
        self.assertEqual(
            (staff.actor_type, staff.actor_user_id, staff.actor_display_name, staff.actor_role,
             staff.channel, staff.audience),
            ('BANK_STAFF', 'staff', '김담당', 'REVIEWER', 'TEAM', 'BANK_INTERNAL'),
        )
        self.assertEqual(
            (customer.actor_type, customer.actor_display_name, customer.channel, customer.audience),
            ('CUSTOMER', '이고객', 'CUSTOMER', 'CUSTOMER'),
        )
        self.assertNotEqual(staff.actor_display_name, '박사칭')

    def test_legacy_fact_provenance_preserved_without_inferred_customer_or_bank_source(self):
        resources = PublicCaseContextResourcesV2(case_id='VP-RAG', context_revision=1)
        raw = dict(fact_id='legacy', case_id='VP-RAG', field='transfer_status', value='송금했어요',
            source='AI_EXTRACTED', status='PROPOSED', evidence_message_id='msg', source_question_id='cq-parent',
            created_at='2026-09-18T01:00:00Z')
        context = bank_source_context('VP-RAG', resources, facts=[raw], questions=[], messages=[], verifications=[])
        self.assertEqual(context.legacy_facts[0].source, 'AI_EXTRACTED')
        self.assertEqual(context.legacy_facts[0].evidence_message_id, 'msg')
        self.assertEqual(context.legacy_facts[0].source_question_id, 'cq-parent')
        self.assertIsNone(context.legacy_facts[0].confirmed_at)
