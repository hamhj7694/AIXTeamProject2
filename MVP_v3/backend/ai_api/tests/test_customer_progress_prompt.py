import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from contracts.ai_internal.case_copilot import CaseCopilotInput
from ai_api.app.domains.case_support.copilot_errors import CaseCopilotProviderError
from ai_api.app.domains.case_support.copilot_service import CaseCopilotService
from ai_api.app.domains.case_support.customer_support_service import CustomerSupportService


class CustomerSupportServiceTest(unittest.IsolatedAsyncioTestCase):
    async def invoke(self, prompt, *, reply="현재 기록만으로는 확인하기 어렵습니다.", **fields):
        case_id = fields.pop("case_id", "customer-safe-test")
        create = AsyncMock(return_value=SimpleNamespace(output_text=reply, status="completed"))
        client = SimpleNamespace(responses=SimpleNamespace(create=create))
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "OPENAI_CUSTOMER_SUPPORT_MODEL": "customer-support-test-model",
        }), patch(
            "ai_api.app.domains.case_support.customer_support_service.AsyncOpenAI",
            return_value=client,
        ):
            result = await CaseCopilotService().generate(CaseCopilotInput(
                case_id=case_id, prompt=prompt,
                assistant_mode="CUSTOMER_SUPPORT", **fields,
            ))
        return result, create.await_args.kwargs

    async def test_customer_route_uses_isolated_prompt_and_customer_model(self):
        result, args = await self.invoke(
            "지금 화면 질문에 답하면 되나요?",
            reply="네, 이 상담 화면의 확인 질문에는 아는 범위에서 답하셔도 됩니다. 실제 인증번호는 입력하지 마세요.",
            customer_service_questions=[{
                "question_text": "인증번호를 제공하셨나요?",
                "customer_explanation": "인증정보 제공 여부만 확인합니다.",
                "options": ["제공함", "제공하지 않음"],
            }],
            customer_ui_capabilities=["OPEN_ACTIVE_QUESTION"],
            customer_progress=["고객 공개: 접수 결과 대기"],
            published_verification_results=["공개된 기관 확인 결과"],
        )

        self.assertEqual(args["model"], "customer-support-test-model")
        self.assertEqual(result.model_mode, "customer-support-test-model")
        self.assertIn("인증번호를 제공하셨나요?", args["input"])
        self.assertIn("OPEN_ACTIVE_QUESTION", args["input"])
        self.assertIn("접수 결과 대기", args["input"])
        self.assertIn("공개된 기관 확인 결과", args["input"])
        self.assertIn("외부 상대의 요구", args["instructions"])
        self.assertIn("비밀번호, OTP·인증번호", args["instructions"])
        self.assertIn("현재 고객 화면에는 없다고", args["instructions"])
        self.assertEqual(result.recommended_actions, [])

    async def test_prompt_distinguishes_question_origin_and_never_accepts_secret_values(self):
        cases = [
            "이 상담 화면의 확인 질문을 말하는 건가요?",
            "전화한 사람이 OTP를 알려 달래요.",
            "이 질문에 실제 비밀번호를 적어도 돼요?",
            "어디서 온 질문인지 잘 모르겠어요.",
            "이미 돈을 보냈고 은행 앱에서 뭘 해야 하나요?",
            "이 서비스에서 거래 내역 조회 버튼을 쓸 수 있나요?",
        ]
        for index, prompt in enumerate(cases):
            with self.subTest(prompt=prompt):
                _, args = await self.invoke(
                    prompt,
                    case_id=f"customer-safe-{index}",
                    customer_service_questions=[{"question_text": "송금하셨나요?"}],
                    customer_ui_capabilities=["OPEN_ACTIVE_QUESTION"],
                )
                self.assertIn(prompt, args["input"])
                self.assertIn("외부 상대의 요구", args["instructions"])
                self.assertIn("실제 비밀값은 적지 말라고", args["instructions"])
                self.assertIn("목록에 없는 화면, 버튼, 메뉴", args["instructions"])

    async def test_unsupported_screen_and_unverified_phone_are_replaced_with_safe_fallback(self):
        for reply in (
            "거래 내역 조회 메뉴를 누르면 송금 내역을 확인할 수 있습니다.",
            "은행 고객센터 02-1234-5678로 전화하세요.",
            "은행 고객센터 1588-1234로 전화하세요.",
        ):
            with self.subTest(reply=reply):
                result, _ = await self.invoke("어떤 메뉴나 번호를 이용하나요?", reply=reply)
                self.assertEqual(result.model_mode, "CUSTOMER_SUPPORT_SAFE_FALLBACK")
                self.assertNotIn("02-1234-5678", result.content)
                self.assertNotIn("1588-1234", result.content)
                self.assertNotIn("거래 내역 조회 메뉴", result.content)

    async def test_no_active_question_means_no_question_navigation_capability(self):
        _, args = await self.invoke("현재 답변할 질문이 있나요?")

        self.assertNotIn("OPEN_ACTIVE_QUESTION", args["input"])
        self.assertNotIn("CSR_QUESTION_CARD", args["input"])

    async def test_bank_only_fields_are_rejected_by_customer_contract(self):
        for field in (
            {"staff_context": ["비공개 직원 메모"]},
            {"pending_actions": ["내부 지급정지 업무"]},
            {"unresolved_verifications": ["담당자 검증 대상"]},
            {"primary_assignee": "담당자"},
            {"transfer_status": "YES"},
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                CaseCopilotInput(
                    case_id="customer-contract", prompt="현재 상황을 알려 주세요.",
                    assistant_mode="CUSTOMER_SUPPORT", **field,
                )

    async def test_customer_ui_capabilities_cannot_be_sent_in_bank_mode(self):
        with self.assertRaises(ValueError):
            CaseCopilotInput(
                case_id="bank-contract", prompt="현재 상황을 요약해 주세요.",
                assistant_mode="BANK_INTERNAL",
                customer_ui_capabilities=["OPEN_ACTIVE_QUESTION"],
            )

    async def test_provider_failure_is_not_replaced_with_made_up_customer_guidance(self):
        create = AsyncMock(side_effect=RuntimeError("provider unavailable"))
        client = SimpleNamespace(responses=SimpleNamespace(create=create))
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), patch(
            "ai_api.app.domains.case_support.customer_support_service.AsyncOpenAI",
            return_value=client,
        ), self.assertRaises(CaseCopilotProviderError):
            await CustomerSupportService().generate(CaseCopilotInput(
                case_id="provider-error", prompt="이미 송금했어요. 어떻게 해야 하나요?",
                assistant_mode="CUSTOMER_SUPPORT",
            ))


if __name__ == "__main__":
    unittest.main()
