import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from contracts.ai_internal.case_copilot import CaseCopilotInput
from contracts.public_api.case_context_v2 import PublicCaseContextResourcesV2
from general_api.app.domains.cases.case_retrieval import (
    CaseRecord, CaseRetriever, collect_records, merge_support_records,
    retrieve_context, similar_question, workspace_records,
)
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
        CaseCopilotInput.model_validate(bank_input)
        self.assertIn('은행 내부 제한 정보', ' '.join(bank_input['staff_context']))
        self.assertTrue(bank_input['retrieved_context'])
        customer = self.client.post('/api/cases/VP-RAG/ai/customer-replies', json={'prompt': '계좌 내부 검토 진행 상황', 'requester_user_id': 'customer', 'requester_display_name': '고객', 'reply_to_message_id': 'message-customer'})
        self.assertEqual(customer.status_code, 201, customer.text)
        customer_input = self.ai.await_args.args[0]
        CaseCopilotInput.model_validate(customer_input)
        self.assertNotIn('은행 내부 제한 정보', str(customer_input))
        self.assertEqual(customer_input['retrieved_context'], [])

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
