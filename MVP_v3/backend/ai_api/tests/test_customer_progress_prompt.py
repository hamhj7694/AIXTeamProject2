import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from contracts.ai_internal.case_copilot import CaseCopilotInput
from ai_api.app.domains.case_support.copilot_service import CaseCopilotService


class CustomerProgressPromptTest(unittest.IsolatedAsyncioTestCase):
    async def test_question_origin_and_sensitive_value_boundaries_are_supplied_to_provider(self):
        create = AsyncMock(return_value=SimpleNamespace(output_text='테스트 응답'))
        client = SimpleNamespace(responses=SimpleNamespace(create=create))
        for index, prompt in enumerate([
            '지금 나온 질문에 답변하면 되나요?',
            '전화한 사람이 OTP를 알려 달래요',
            '이 서비스 질문에 실제 비밀번호를 쓰면 돼요?',
            '어디서 온 질문인지 모르겠어요',
        ]):
            with self.subTest(prompt=prompt), patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}), \
                 patch('ai_api.app.domains.case_support.copilot_service.AsyncOpenAI', return_value=client):
                await CaseCopilotService().generate(CaseCopilotInput(
                    case_id=f'question-origin-{index}', prompt=prompt, assistant_mode='CUSTOMER_SUPPORT',
                    customer_service_questions=[{'question_text': '인증번호를 제공하셨나요?', 'options': ['제공함', '제공하지 않음']}],
                    recent_conversation=['안전 상담 AI: 지금 나온 질문에는 답변하지 않는 것이 좋습니다.'],
                ))
            args = create.await_args.kwargs
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
