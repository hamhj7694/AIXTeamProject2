from __future__ import annotations

import unittest

from contracts.ai_internal.context_fact_extraction import ContextFactExtractionInput, ContextFactExtractionMessage, ExistingContextFact
from ai_api.app.domains.case_support.context_fact_extraction_service import ContextFactExtractionService


class ContextFactExtractionTests(unittest.IsolatedAsyncioTestCase):
    async def extract(self, text: str, actor_type: str = "CUSTOMER"):
        return await ContextFactExtractionService().extract(ContextFactExtractionInput(message=ContextFactExtractionMessage(
            message_id="msg-1", case_id="VP-1", actor_type=actor_type, content=text,
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

    async def test_additional_reported_transfer_is_a_separate_event_for_colloquial_korean(self):
        result = await self.extract("200만원 더 송금했데!", "BANK_STAFF")
        amount = next(item for item in result.proposals if item.semantic_key == "transfer.actual.amount")
        self.assertEqual(amount.value["amount_krw"], 2_000_000)
        self.assertEqual(amount.value["amount_scope"], "EVENT")
        self.assertEqual(amount.value["direction"], "OUT")
        self.assertEqual(amount.display_value, "2,000,000원 송금")

    async def test_explicit_amount_correction_replaces_the_old_active_fact(self):
        result = await ContextFactExtractionService().extract(ContextFactExtractionInput(
            message=ContextFactExtractionMessage(
                message_id="correction-msg", case_id="VP-1", actor_type="BANK_STAFF",
                content="500만원이 아니라 700만원 송금했어. 앞의 금액을 정정해.",
            ),
            existing_facts=[ExistingContextFact(
                fact_id="old-transfer", semantic_key="transfer.actual.amount",
                value={"amount_krw": 5_000_000, "currency": "KRW", "direction": "OUT", "amount_scope": "EVENT"},
                status="PROPOSED",
            )],
        ))
        amounts = [item for item in result.proposals if item.semantic_key == "transfer.actual.amount"]
        self.assertEqual(len(amounts), 1)
        self.assertEqual(amounts[0].value["amount_krw"], 7_000_000)
        self.assertEqual(amounts[0].supersedes_fact_id, "old-transfer")

    async def test_reported_transfer_denial_is_not_recorded_as_completed(self):
        for text in ("200만원 송금 안 했대", "200만원 보내지 않았다고 해요"):
            with self.subTest(text=text):
                result = await self.extract(text, "BANK_STAFF")
                self.assertNotIn("transfer.actual.amount", {item.semantic_key for item in result.proposals})

    async def test_staff_reported_completed_transfer_is_near_confirmed_without_lifecycle_promotion(self):
        result = await self.extract("500만원 송금 됐다고 확인 됨.", "BANK_STAFF")
        status = next(item for item in result.proposals if item.semantic_key == "transfer.actual.status")
        amount = next(item for item in result.proposals if item.semantic_key == "transfer.actual.amount")
        self.assertEqual(status.value["status"], "TRANSFERRED")
        self.assertEqual(status.display_value, "송금했음")
        self.assertEqual(status.value["staff_attestation"], "EXPLICIT_STAFF_CHECK")
        self.assertEqual(amount.value["amount_krw"], 5_000_000)
        self.assertEqual(amount.value["staff_attestation"], "EXPLICIT_STAFF_CHECK")

    async def test_customer_or_requested_transfer_is_not_staff_attested(self):
        customer = await self.extract("500만원 송금 됐다고 확인 됨.", "CUSTOMER")
        self.assertNotIn("staff_attestation", next(
            item.value for item in customer.proposals if item.semantic_key == "transfer.actual.status"
        ))
        demand = await self.extract("상대방이 500만원 송금하라고 했고 직원 확인이 필요합니다.", "BANK_STAFF")
        self.assertNotIn("transfer.actual.status", {item.semantic_key for item in demand.proposals})

    async def test_requested_and_actual_amounts_stay_distinct_in_one_message(self):
        result = await self.extract("500만원을 보내라고 했는데 실제로는 300만원만 보냈어요")
        requested = next(item for item in result.proposals if item.semantic_key == "transfer.requested.amount")
        actual = next(item for item in result.proposals if item.semantic_key == "transfer.actual.amount")
        status = next(item for item in result.proposals if item.semantic_key == "transfer.actual.status")
        self.assertEqual(requested.value["amount_krw"], 5_000_000)
        self.assertEqual(actual.value["amount_krw"], 3_000_000)
        self.assertEqual(status.value["status"], "TRANSFERRED")

    async def test_amount_request_without_transfer_keyword_is_extracted(self):
        result = await self.extract("상대방에게 300만원 요구받았다고 합니다")
        proposal = next(item for item in result.proposals if item.semantic_key == "transfer.requested.amount")
        self.assertEqual(proposal.value["amount_krw"], 3_000_000)
        self.assertEqual(proposal.value["amount_role"], "REQUESTED_AMOUNT")

    async def test_transfer_and_refund_keep_direction_and_role(self):
        result = await self.extract("300만원을 송금하고 20만원을 돌려 받고, 5만원 더 송금했데!")
        amounts = [item for item in result.proposals if item.semantic_key == "transfer.actual.amount"]
        self.assertEqual({item.value["amount_krw"] for item in amounts}, {3_000_000, 200_000, 50_000})
        self.assertEqual({item.value["direction"] for item in amounts}, {"OUT", "IN"})
        self.assertIn("REFUND_IN", {item.value["amount_role"] for item in amounts})
        self.assertIn("TRANSFER_OUT", {item.value["amount_role"] for item in amounts})

    async def test_final_amount_scope_is_preserved(self):
        result = await self.extract("여러 금액을 말했지만 최종적으로 100만원을 요구받았다고 한다")
        proposal = next(item for item in result.proposals if item.semantic_key == "transfer.requested.amount")
        self.assertEqual(proposal.value["amount_scope"], "FINAL")

    async def test_promised_return_amount_is_separate_from_actual_refund(self):
        result = await self.extract("3천만원 보내면 5천만원으로 돌려줄게요")
        proposal = next(item for item in result.proposals if item.semantic_key == "transfer.promised_return.amount")
        self.assertEqual(proposal.value["amount_krw"], 50_000_000)
        self.assertEqual(proposal.value["promise_status"], "PROMISED")

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

    async def test_remote_control_request_is_not_misclassified_as_installed(self):
        result = await self.extract("상대가 애니데스크 원격제어 앱을 설치하라고 요구했어요")
        proposal = next(item for item in result.proposals if item.semantic_key == "device.remote_control_app")
        self.assertEqual(proposal.value["status"], "REQUESTED")

    async def test_personal_information_requirement_and_supply_are_separate(self):
        asked = await self.extract("상대가 주민등록번호를 적으라고 요구했어요")
        self.assertNotIn("exposure.personal_information", {item.semantic_key for item in asked.proposals})
        self.assertIn("circumstance.demand", {item.semantic_key for item in asked.proposals})
        provided = await self.extract("주민등록번호를 상대에게 입력해서 보냈어요")
        self.assertIn("exposure.personal_information", {item.semantic_key for item in provided.proposals})

    async def test_staff_attestation_applies_to_explicitly_checked_exposure_and_device_outcomes(self):
        samples = (
            ("제가 확인해 보니 OTP를 상대에게 전달했어요", "exposure.authentication_information"),
            ("직접 확인해보니 주민등록번호를 입력해서 보냈어요", "exposure.personal_information"),
            ("제가 확인했는데 애니데스크 원격제어 앱이 설치됐어요", "device.remote_control_app"),
        )
        for text, semantic_key in samples:
            with self.subTest(semantic_key=semantic_key):
                result = await self.extract(text, "BANK_STAFF")
                proposal = next(item for item in result.proposals if item.semantic_key == semantic_key)
                self.assertEqual(proposal.value["staff_attestation"], "EXPLICIT_STAFF_CHECK")

    async def test_staff_checked_remote_app_denial_is_not_a_positive_installation(self):
        result = await self.extract("제가 확인했는데 애니데스크는 안 설치했어요", "BANK_STAFF")
        proposal = next(item for item in result.proposals if item.semantic_key == "device.remote_control_app")
        self.assertEqual(proposal.value["status"], "NOT_INSTALLED")
        self.assertEqual(proposal.value["staff_attestation"], "EXPLICIT_STAFF_CHECK")

    async def test_denied_disclosure_is_not_extracted_as_exposure(self):
        for text, semantic_key in (
            ("OTP 번호를 안 알려줬어요", "exposure.authentication_information"),
            ("개인정보를 상대에게 보내지 않았어요", "exposure.personal_information"),
        ):
            with self.subTest(semantic_key=semantic_key):
                result = await self.extract(text)
                matching = [item for item in result.proposals if item.semantic_key == semantic_key]
                self.assertEqual(len(matching), 1)
                self.assertEqual(matching[0].value['status'], 'NOT_EXPOSED')
                self.assertNotIn('staff_reported', matching[0].value)

    async def test_explicit_disclosure_correction_replaces_only_the_prior_outcome(self):
        result = await ContextFactExtractionService().extract(ContextFactExtractionInput(
            message=ContextFactExtractionMessage(
                message_id="correction-exposure", case_id="VP-1", actor_type="BANK_STAFF",
                content="OTP를 제공했다고 했는데 사실은 제공하지 않았어요. 정정합니다.",
            ),
            existing_facts=[ExistingContextFact(
                fact_id="old-exposure", semantic_key="exposure.authentication_information",
                value={"status": "EXPOSED"}, status="PROPOSED",
            )],
        ))
        current = next(item for item in result.proposals if item.semantic_key == "exposure.authentication_information")
        self.assertEqual(current.value["status"], "NOT_EXPOSED")
        self.assertEqual(current.supersedes_fact_id, "old-exposure")

    async def test_remote_app_correction_does_not_erase_installation_demand(self):
        result = await ContextFactExtractionService().extract(ContextFactExtractionInput(
            message=ContextFactExtractionMessage(
                message_id="correction-app", case_id="VP-1", actor_type="BANK_STAFF",
                content="사실은 애니데스크 원격제어 앱을 설치하지 않았어요. 정정합니다.",
            ),
            existing_facts=[
                ExistingContextFact(fact_id="old-installed", semantic_key="device.remote_control_app",
                                    value={"status": "INSTALLED"}, status="PROPOSED"),
                ExistingContextFact(fact_id="original-demand", semantic_key="device.remote_control_app",
                                    value={"status": "REQUESTED"}, status="PROPOSED"),
            ],
        ))
        current = next(item for item in result.proposals if item.semantic_key == "device.remote_control_app")
        self.assertEqual(current.value["status"], "NOT_INSTALLED")
        self.assertEqual(current.supersedes_fact_id, "old-installed")

    async def test_chat_correction_does_not_auto_supersede_reviewed_outcome(self):
        result = await ContextFactExtractionService().extract(ContextFactExtractionInput(
            message=ContextFactExtractionMessage(
                message_id="reviewed-app-correction", case_id="VP-1", actor_type="BANK_STAFF",
                content="사실은 애니데스크 원격제어 앱을 설치하지 않았어요. 정정합니다.",
            ),
            existing_facts=[ExistingContextFact(
                fact_id="reviewed-installed", semantic_key="device.remote_control_app",
                value={"status": "INSTALLED"}, status="CONFIRMED",
            )],
        ))
        current = next(item for item in result.proposals if item.semantic_key == "device.remote_control_app")
        self.assertEqual(current.value["status"], "NOT_INSTALLED")
        self.assertIsNone(current.supersedes_fact_id)

    async def test_unknown_domain_term_is_retained_as_review_observation(self):
        result = await self.extract("수수료를 먼저 납부하면 처리가 가능하다고 안내받았습니다.")
        self.assertEqual(len(result.unmapped_observations), 1)
        observation = result.unmapped_observations[0]
        self.assertEqual(observation.status, "UNMAPPED")
        self.assertIn("DOMAIN.FEE", observation.lexical_codes)
        self.assertEqual(observation.observed_terms[0]["surface_form"], "수수료")


if __name__ == "__main__":
    unittest.main()
