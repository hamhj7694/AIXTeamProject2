from __future__ import annotations

import unittest

from contracts.ai_internal.context_fact_extraction import ContextFactExtractionInput, ContextFactExtractionMessage
from ai_api.app.domains.case_support.context_fact_extraction_service import ContextFactExtractionService


class ContextFactExtractionTests(unittest.IsolatedAsyncioTestCase):
    async def extract(self, text: str):
        return await ContextFactExtractionService().extract(ContextFactExtractionInput(message=ContextFactExtractionMessage(
            message_id="msg-1", case_id="VP-1", actor_type="CUSTOMER", content=text,
        )))

    async def test_otp_demand_is_not_exposure(self):
        result = await self.extract("검사가 OTP 번호를 알려달라고 요구했어요")
        keys = {item.semantic_key for item in result.proposals}
        self.assertIn("circumstance.demand", keys)
        self.assertNotIn("exposure.authentication_information", keys)

    async def test_otp_supplied_is_exposure(self):
        result = await self.extract("OTP 번호를 상대방에게 알려줬어요")
        self.assertIn("exposure.authentication_information", {item.semantic_key for item in result.proposals})

    async def test_requested_amount_is_separate_from_actual_amount(self):
        result = await self.extract("상대가 300만원을 보내라고 요구했어요")
        keys = {item.semantic_key for item in result.proposals}
        self.assertIn("transfer.requested.amount", keys)
        self.assertNotIn("transfer.actual.amount", keys)

    async def test_actual_amount_sets_transfer_status(self):
        result = await self.extract("실제로 120만원을 송금했어요")
        keys = {item.semantic_key for item in result.proposals}
        self.assertIn("transfer.actual.amount", keys)
        self.assertIn("transfer.actual.status", keys)

    async def test_requested_and_actual_amounts_stay_distinct_in_one_message(self):
        result = await self.extract("500만원을 보내라고 했는데 실제로는 300만원만 보냈어요")
        requested = next(item for item in result.proposals if item.semantic_key == "transfer.requested.amount")
        actual = next(item for item in result.proposals if item.semantic_key == "transfer.actual.amount")
        status = next(item for item in result.proposals if item.semantic_key == "transfer.actual.status")
        self.assertEqual(requested.value["amount_krw"], 5_000_000)
        self.assertEqual(actual.value["amount_krw"], 3_000_000)
        self.assertEqual(status.value["status"], "TRANSFERRED")

    async def test_prosecutor_impersonation(self):
        result = await self.extract("서울중앙지검 검사라고 말했어요")
        keys = {item.semantic_key for item in result.proposals}
        self.assertIn("offender.claimed_organization", keys)
        self.assertIn("offender.claimed_person_or_role", keys)

    async def test_structured_answer_text_can_propose_authentication_and_card_exposure(self):
        result = await self.extract("OTP\n카드번호도 알려줬어요.")
        keys = {item.semantic_key for item in result.proposals}
        self.assertIn("exposure.authentication_information", keys)
        self.assertIn("exposure.identity_or_card", keys)

    async def test_remote_control_app_installation(self):
        result = await self.extract("상대가 시켜서 애니데스크 원격제어 앱을 설치했어요")
        proposal = next(item for item in result.proposals if item.semantic_key == "device.remote_control_app")
        self.assertEqual(proposal.value["status"], "INSTALLED")


if __name__ == "__main__":
    unittest.main()
