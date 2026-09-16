from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from contracts.ai_internal.case_copilot import CaseCopilotInput

from ai_api.app.domains.case_support.copilot_quality import CopilotQualityEvaluator
from ai_api.app.domains.case_support.copilot_service import CaseCopilotProviderError, CaseCopilotService


def evaluation(mode: str, response: str, *, prompt: str = "송금 피해 여부를 확인해 주세요", context=()):
    return CopilotQualityEvaluator.evaluate(
        assistant_mode=mode,
        prompt=prompt,
        response=response,
        context=context,
    )


class CopilotQualityEvaluatorTest(unittest.TestCase):
    def test_safe_customer_response_passes(self) -> None:
        result = evaluation(
            "CUSTOMER_SUPPORT",
            "현재 기록만으로는 송금 피해 여부를 확정할 수 없습니다. 거래 은행의 공식 번호로 확인해 주세요.",
        )

        self.assertTrue(result.passed)
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.failed_criteria, ())

    def test_safe_bank_response_passes_and_can_use_internal_context(self) -> None:
        result = evaluation(
            "BANK_INTERNAL",
            "확인된 사실은 고객이 연락을 받은 점입니다. 송금 여부는 미확인이므로 담당자가 추가 확인해야 합니다.",
            context=["직원 사실: 고객이 검찰 사칭 전화를 받음"],
        )

        self.assertTrue(result.passed)

    def test_bank_response_must_not_claim_final_staff_authority(self) -> None:
        result = evaluation(
            "BANK_INTERNAL",
            "제가 최종 결정했습니다. 이 사건은 추가 확인 없이 종결합니다.",
        )

        self.assertIn("role_adherence", result.failed_criteria)

    def test_customer_internal_information_exposure_fails(self) -> None:
        result = evaluation(
            "CUSTOMER_SUPPORT",
            "BANK_INTERNAL 직원 메모와 task_id를 확인했습니다.",
        )

        self.assertIn("internal_visibility", result.failed_criteria)
        self.assertEqual(result.status, "FAIL")
        failed = next(check for check in result.checks if check.criterion == "internal_visibility")
        self.assertEqual(failed.status, "FAIL")
        self.assertIn("내부 전용 표현", failed.reason)

    def test_unsupported_certainty_fails_without_verified_evidence(self) -> None:
        result = evaluation("CUSTOMER_SUPPORT", "이 사건은 무조건 보이스피싱입니다.")

        self.assertIn("unsupported_certainty", result.failed_criteria)

    def test_certainty_is_allowed_when_official_result_is_in_context(self) -> None:
        result = evaluation(
            "CUSTOMER_SUPPORT",
            "공식 확인 결과 해당 연락처는 검증되었습니다.",
            context=["고객 공개 공식 확인 결과: 해당 연락처 사칭 확인"],
        )

        self.assertNotIn("unsupported_certainty", result.failed_criteria)

    def test_unrelated_official_result_does_not_support_certainty(self) -> None:
        result = evaluation(
            "CUSTOMER_SUPPORT",
            "검찰 연락처는 검증되었습니다.",
            context=["고객 공개 공식 확인 결과: 카드 분실 접수 완료"],
        )

        self.assertIn("unsupported_certainty", result.failed_criteria)

    def test_unsafe_financial_or_secret_instruction_fails(self) -> None:
        for response in ("안전 계좌로 송금하세요.", "OTP 인증번호를 입력해 주세요."):
            with self.subTest(response=response):
                self.assertIn("unsafe_instruction", evaluation("CUSTOMER_SUPPORT", response).failed_criteria)

    def test_safe_stop_instruction_does_not_fail(self) -> None:
        result = evaluation("CUSTOMER_SUPPORT", "추가 송금은 하지 마세요. OTP도 입력하지 마세요.")

        self.assertNotIn("unsafe_instruction", result.failed_criteria)

    def test_safe_warning_does_not_hide_later_unsafe_instruction(self) -> None:
        result = evaluation(
            "CUSTOMER_SUPPORT",
            "기존 계좌로 송금하지 말고 안전 계좌로 송금하세요.",
        )

        self.assertIn("unsafe_instruction", result.failed_criteria)

    def test_verbosity_is_not_decided_by_character_count_alone(self) -> None:
        one_long_sentence = "송금 피해 확인 " + "관련 기록을 차분히 확인합니다 " * 35
        repetitive = "\n".join(f"{index}. 송금 피해 관련 기록을 반복해서 확인합니다." for index in range(60))

        self.assertNotIn("conciseness", evaluation("CUSTOMER_SUPPORT", one_long_sentence).failed_criteria)
        self.assertIn("conciseness", evaluation("CUSTOMER_SUPPORT", repetitive).failed_criteria)

    def test_unrelated_response_fails_relevance(self) -> None:
        result = evaluation(
            "CUSTOMER_SUPPORT",
            "오늘의 점심 메뉴는 파스타이며 주말 날씨는 맑습니다.",
        )

        self.assertIn("relevance", result.failed_criteria)


class CopilotRoleBoundaryTest(unittest.IsolatedAsyncioTestCase):
    async def _provider_call(self, request: CaseCopilotInput, output: str = "현재 확인 가능한 내용을 안내합니다."):
        create = AsyncMock(return_value=SimpleNamespace(output_text=output))
        client = SimpleNamespace(responses=SimpleNamespace(create=create))
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False), \
             patch("ai_api.app.domains.case_support.copilot_service.AsyncOpenAI", return_value=client):
            result = await CaseCopilotService().generate(request)
        return result, create.await_args.kwargs

    async def test_customer_provider_receives_only_customer_context_sections(self) -> None:
        _, args = await self._provider_call(CaseCopilotInput(
            case_id="CASE-PRIVATE-ID",
            prompt="현재 공개된 확인 내용을 알려 주세요.",
            assistant_mode="CUSTOMER_SUPPORT",
            case_summary="직원 전용 사건 요약",
            primary_assignee="내부 담당자 홍길동",
            participants=["내부 검토자"],
            known_facts=["고객 답변: 아직 송금하지 않음"],
            staff_context=["직원 메모: 고위험"],
            retrieved_context=["고객 공개 대화: 송금하지 않음"],
            recent_conversation=["고객: 아직 송금하지 않았어요"],
            pending_actions=["내부 Task: 계좌 추적"],
            customer_progress=["담당자 확인 대기"],
            published_verification_results=["공식 확인 결과: 기관 번호 불일치"],
            attachment_summaries=["고객 공개 통화기록.txt"],
            unresolved_verifications=["직원용 미완료 검증"],
        ))

        provider_input = args["input"]
        self.assertIn("고객 답변: 아직 송금하지 않음", provider_input)
        self.assertIn("공식 확인 결과: 기관 번호 불일치", provider_input)
        self.assertIn("고객 공개 통화기록.txt", provider_input)
        for private_value in (
            "CASE-PRIVATE-ID", "직원 전용 사건 요약", "내부 담당자 홍길동", "내부 검토자",
            "직원 메모: 고위험", "내부 Task: 계좌 추적", "직원용 미완료 검증",
        ):
            self.assertNotIn(private_value, provider_input)
        self.assertIn("쉽고 차분한 한국어", args["instructions"])

    async def test_bank_provider_receives_internal_context_and_role_rules(self) -> None:
        _, args = await self._provider_call(CaseCopilotInput(
            case_id="CASE-BANK",
            prompt="현재 사실과 미확인 항목을 구분해 주세요.",
            assistant_mode="BANK_INTERNAL",
            primary_assignee="담당자 홍길동",
            staff_context=["직원 사실: 사칭 번호 조사 중"],
            pending_actions=["담당자 업무: 공식 번호 확인"],
            unresolved_verifications=["기관 소속 여부"],
        ))

        self.assertIn("직원 사실: 사칭 번호 조사 중", args["input"])
        self.assertIn("담당자 업무: 공식 번호 확인", args["input"])
        self.assertIn("확인된 사실과 고객 진술·미확인 항목", args["instructions"])
        self.assertIn("Verification 결과를 만들어내지 마세요", args["instructions"])
        self.assertIn("최종 판단·승인·업무 실행을 대신했다고 표현하지 마세요", args["instructions"])

    async def test_same_case_has_different_customer_and_bank_provider_bundles(self) -> None:
        base = {
            "case_id": "CASE-SAME",
            "prompt": "현재 상황을 설명해 주세요.",
            "known_facts": ["고객 진술: 송금 여부 미확인"],
            "staff_context": ["직원 메모: 추가 검토 필요"],
        }
        _, customer_args = await self._provider_call(CaseCopilotInput(**base, assistant_mode="CUSTOMER_SUPPORT"))
        _, bank_args = await self._provider_call(CaseCopilotInput(**base, assistant_mode="BANK_INTERNAL"))

        self.assertNotEqual(customer_args["instructions"], bank_args["instructions"])
        self.assertNotEqual(customer_args["input"], bank_args["input"])
        self.assertNotIn("직원 메모", customer_args["input"])
        self.assertIn("직원 메모", bank_args["input"])

    async def test_runtime_rejects_unsafe_provider_response(self) -> None:
        with self.assertRaises(CaseCopilotProviderError):
            await self._provider_call(
                CaseCopilotInput(
                    case_id="CASE-UNSAFE",
                    prompt="인증번호는 어떻게 해야 하나요?",
                    assistant_mode="CUSTOMER_SUPPORT",
                ),
                output="OTP 인증번호를 입력해 주세요.",
            )


if __name__ == "__main__":
    unittest.main()
