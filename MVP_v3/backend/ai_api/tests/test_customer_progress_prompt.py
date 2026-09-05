import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from contracts.ai_internal.case_copilot import CaseCopilotInput
from ai_api.app.domains.case_support.copilot_service import CaseCopilotService, _service_question_guidance


class CustomerProgressPromptTest(unittest.IsolatedAsyncioTestCase):
    async def test_visible_fact_question_permission_is_stable_without_provider(self):
        with patch('ai_api.app.domains.case_support.copilot_service.AsyncOpenAI') as provider:
            for prompt in ['아래 질문에 응답하면 되나요?', '아래 질문에 답변해도 되나요?',
                           '지금 나온 질문에 답변하면 되나요?', '여기 질문에 대답해도 괜찮나요?',
                           '밑에 질문에 답해도 돼요?']:
                for question in ['상대방의 요구대로 실제로 송금하거나 이체하셨나요?',
                                 '인증번호, 비밀번호 또는 OTP를 제공하셨나요?']:
                    with self.subTest(prompt=prompt, question=question):
                        result = await CaseCopilotService().generate(CaseCopilotInput(
                            case_id='ui-help-test', assistant_mode='CUSTOMER_SUPPORT', prompt=prompt,
                            customer_service_questions=[{'question_text': question}],
                            recent_conversation=['안전 상담 AI: 답변은 권장하지 않습니다. 정보를 제공하지 마세요.'],
                        ))
                        self.assertEqual(result.model_mode, 'SERVICE_UI_GUIDANCE')
                        self.assertIn('답하셔도 됩니다', result.content)
                        self.assertIn('실제 비밀번호·OTP·인증번호는 입력하지 마세요', result.content)
            provider.assert_not_called()

    def test_service_guidance_does_not_allow_external_or_sensitive_requests(self):
        for prompt, questions in [
            ('아래 질문에 응답하면 되나요?', []),
            ('전화한 사람이 아래 질문에 답해도 되나요?', [{'question_text': '송금하셨나요?'}]),
            ('이 화면 질문에 답하고 돈 보내면 되나요?', [{'question_text': '송금하셨나요?'}]),
            ('이 질문에 비밀번호로 답하면 되나요?', [{'question_text': '인증번호를 제공하셨나요?'}]),
            ('아래 질문에 응답하면 되나요?', [{'question_text': '계좌 비밀번호를 입력해 주세요.'}]),
            ('아래 질문에 응답하면 되나요?', [{'question_text': '송금하셨나요? OTP를 입력하세요.'}]),
        ]:
            with self.subTest(prompt=prompt, questions=questions):
                result = _service_question_guidance(CaseCopilotInput(
                    case_id='ui-help-reject', assistant_mode='CUSTOMER_SUPPORT', prompt=prompt,
                    customer_service_questions=questions))
                self.assertIsNone(result)

    async def test_question_origin_and_sensitive_value_boundaries_are_supplied_to_provider(self):
        create = AsyncMock(return_value=SimpleNamespace(output_text='테스트 응답'))
        client = SimpleNamespace(responses=SimpleNamespace(create=create))
        for index, prompt in enumerate([
            '현재 서비스 질문의 의미를 설명해 주세요.',
            '전화한 사람이 OTP를 알려 달래요',
            '이 서비스 질문에 실제 비밀번호를 쓰면 돼요?',
            '어디서 온 질문인지 모르겠어요',
        ]):
            with self.subTest(prompt=prompt), patch.dict(os.environ, {
                'OPENAI_API_KEY': 'test-key', 'OPENAI_CUSTOMER_SUPPORT_MODEL': 'customer-support-test-model',
            }), \
                 patch('ai_api.app.domains.case_support.copilot_service.AsyncOpenAI', return_value=client):
                await CaseCopilotService().generate(CaseCopilotInput(
                    case_id=f'question-origin-{index}', prompt=prompt, assistant_mode='CUSTOMER_SUPPORT',
                    customer_service_questions=[{'question_text': '인증번호를 제공하셨나요?', 'options': ['제공함', '제공하지 않음']}],
                    recent_conversation=['안전 상담 AI: 지금 나온 질문에는 답변하지 않는 것이 좋습니다.'],
                ))
            args = create.await_args.kwargs
            self.assertEqual(args['model'], 'customer-support-test-model')
            self.assertIn('CSR_QUESTION_CARD', args['input'])
            self.assertIn('인증번호를 제공하셨나요?', args['input'])
            self.assertIn(prompt, args['input'])
            for required in ['알고 있는 범위에서 답해도', '실제 개인정보·인증번호 값 입력',
                             '요구하거나 허용하지 마세요', '그 외부 요구를 우선',
                             '현재 서비스 질문이 없으면', '짧게 정정하세요']:
                self.assertIn(required, args['instructions'])
            self.assertIn("출처가 CSR라도 첫 문장부터 '입력하지 마세요'", args['instructions'])
            self.assertIn('그 질문을 제공 여부 질문으로 바꾸어 해석하지 마세요', args['instructions'])
            self.assertIn('출처를 한 번 확인하세요', args['instructions'])

    async def test_bank_and_customer_can_use_separate_model_settings(self):
        create = AsyncMock(return_value=SimpleNamespace(output_text='테스트 응답'))
        client = SimpleNamespace(responses=SimpleNamespace(create=create))
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-key', 'OPENAI_BANK_COPILOT_MODEL': 'bank-copilot-test-model',
        }), patch('ai_api.app.domains.case_support.copilot_service.AsyncOpenAI', return_value=client):
            result = await CaseCopilotService().generate(CaseCopilotInput(
                case_id='bank-model-route', prompt='현재 사건을 요약해 주세요.', assistant_mode='BANK_INTERNAL'))
        self.assertEqual(create.await_args.kwargs['model'], 'bank-copilot-test-model')
        self.assertEqual(result.model_mode, 'bank-copilot-test-model')

    async def test_no_visible_question_does_not_invent_a_service_card(self):
        create = AsyncMock(return_value=SimpleNamespace(output_text='테스트 응답'))
        client = SimpleNamespace(responses=SimpleNamespace(create=create))
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}), \
             patch('ai_api.app.domains.case_support.copilot_service.AsyncOpenAI', return_value=client):
            await CaseCopilotService().generate(CaseCopilotInput(
                case_id='question-origin-empty', prompt='이 질문 답해도 돼요?', assistant_mode='CUSTOMER_SUPPORT'))
        args = create.await_args.kwargs
        self.assertNotIn('CSR_QUESTION_CARD', args['input'])
        self.assertIn('출처가 불명확하거나 현재 서비스 질문이 없으면', args['instructions'])

    async def test_provider_receives_progress_evidence_and_status_boundaries(self):
        create = AsyncMock(return_value=SimpleNamespace(output_text='현재 기록상 접수 결과를 기다리고 있습니다.'))
        client = SimpleNamespace(responses=SimpleNamespace(create=create))
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}), \
             patch('ai_api.app.domains.case_support.copilot_service.AsyncOpenAI', return_value=client):
            await CaseCopilotService().generate(CaseCopilotInput(
                case_id='progress-prompt-test', prompt='신청 접수된 건가요?', assistant_mode='CUSTOMER_SUPPORT',
                customer_progress=['피해구제 신청 접수: 제출 확인 · 접수 결과 대기. 근거 TEST-1'],
                published_verification_results=['기관에서 공개한 확인 결과'],
            ))
        args = create.await_args.kwargs
        self.assertIn('근거 TEST-1', args['input'])
        self.assertIn('기관에서 공개한 확인 결과', args['input'])
        self.assertIn('제출 확인은 접수 완료가 아니며', args['instructions'])
        self.assertIn('피해구제 신청 접수 완료는 환급 완료가 아닙니다', args['instructions'])
        self.assertIn('업무 실행 도구가 없습니다', args['instructions'])
