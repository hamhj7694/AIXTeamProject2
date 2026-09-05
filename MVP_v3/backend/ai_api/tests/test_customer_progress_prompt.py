import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from contracts.ai_internal.case_copilot import CaseCopilotInput
from ai_api.app.domains.case_support.copilot_service import CaseCopilotService


class CustomerProgressPromptTest(unittest.IsolatedAsyncioTestCase):
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
