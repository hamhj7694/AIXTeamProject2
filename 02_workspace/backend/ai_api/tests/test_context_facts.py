from __future__ import annotations

import unittest

from ai_api.app.domains.case_support.context_fact_extraction import (
    ContextFactsValidationError,
    StructuredCaseFactsParser,
)
from ai_api.app.domains.case_support.context_facts import FactStatus


def evidence(text: str) -> dict[str, str]:
    return {"evidence_text": text}


class StructuredCaseFactsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = StructuredCaseFactsParser()

    def test_case_a_impersonation_claim_and_five_million_won_demand(self) -> None:
        raw = "검찰 수사관입니다. 당신 계좌가 범죄에 연루됐습니다. 안전 계좌로 500만원을 송금하세요."
        facts = self.parser.parse(raw, {
            "impersonated_entities": [{"value": "검찰 수사관", "evidence": evidence("검찰 수사관입니다.")}],
            "claims": [{"value": "계좌가 범죄에 연루됨", "evidence": evidence("계좌가 범죄에 연루됐습니다.")}],
            "demands": [{"action": "송금", "reason": "안전 계좌", "amount_krw": 5_000_000,
                         "target": "안전 계좌", "evidence": evidence("안전 계좌로 500만원을 송금하세요.")}],
            "mentioned_amounts": [{"amount_krw": 5_000_000, "evidence": evidence("500만원")}],
        })
        self.assertEqual(facts.demands[0].amount_krw, 5_000_000)
        self.assertEqual(facts.mentioned_amounts[0].amount_krw, 5_000_000)

    def test_case_b_transfer_remote_app_and_credential_requests_coexist(self) -> None:
        raw = "지금 돈을 보내세요. 원격제어 앱을 설치하세요. 인증번호와 비밀번호를 알려주세요."
        facts = self.parser.parse(raw, {
            "demands": [{"action": "송금", "evidence": evidence("지금 돈을 보내세요.")}],
            "app_installation_requests": [{"value": "원격제어 앱 설치", "evidence": evidence("원격제어 앱을 설치하세요.")}],
            "credential_requests": [{"value": "인증번호와 비밀번호", "evidence": evidence("인증번호와 비밀번호를 알려주세요.")}],
        })
        self.assertEqual(len(facts.demands), 1)
        self.assertEqual(len(facts.app_installation_requests), 1)
        self.assertEqual(len(facts.credential_requests), 1)

    def test_case_c_absent_amount_is_an_empty_list_not_a_guess(self) -> None:
        facts = self.parser.parse("돈을 보내세요.", {
            "demands": [{"action": "송금", "evidence": evidence("돈을 보내세요.")}],
        })
        self.assertEqual(facts.mentioned_amounts, [])
        self.assertIsNone(facts.demands[0].amount_krw)

    def test_case_d_unknown_impersonator_stays_empty_and_can_be_unresolved(self) -> None:
        raw = "당신은 문제가 생겼습니다. 지금 확인하세요."
        facts = self.parser.parse(raw, {
            "unresolved_items": [{"description": "사칭 주체가 명확하지 않음", "related_evidence": [evidence("문제가 생겼습니다.")]}],
        })
        self.assertEqual(facts.impersonated_entities, [])
        self.assertEqual(len(facts.unresolved_items), 1)

    def test_case_e_rejects_a_fact_whose_evidence_is_not_in_the_source(self) -> None:
        with self.assertRaisesRegex(ContextFactsValidationError, "unsupported fact"):
            self.parser.parse("검찰이라고만 말했습니다.", {
                "demands": [{"action": "송금", "evidence": evidence("500만원을 송금하세요.")}],
            })

    def test_case_f_allows_multiple_claims_and_demands(self) -> None:
        raw = "계좌가 범죄에 연루됐습니다. 신분증이 도용됐습니다. 100만원을 보내세요. 앱도 설치하세요."
        facts = self.parser.parse(raw, {
            "claims": [
                {"value": "계좌 범죄 연루", "evidence": evidence("계좌가 범죄에 연루됐습니다.")},
                {"value": "신분증 도용", "evidence": evidence("신분증이 도용됐습니다.")},
            ],
            "demands": [
                {"action": "송금", "amount_krw": 1_000_000, "evidence": evidence("100만원을 보내세요.")},
                {"action": "앱 설치", "evidence": evidence("앱도 설치하세요.")},
            ],
        })
        self.assertEqual(len(facts.claims), 2)
        self.assertEqual(len(facts.demands), 2)

    def test_case_g_excerpt_does_not_accept_invented_turn_order(self) -> None:
        with self.assertRaisesRegex(ContextFactsValidationError, "turn is not available"):
            self.parser.parse("먼저 보낸 발췌문입니다. 나중 발화 여부는 알 수 없습니다.", {
                "claims": [{"value": "발췌문", "evidence": {"evidence_text": "보낸 발췌문입니다.", "turn": 2}}],
            })

    def test_source_ref_is_assigned_by_the_input_boundary(self) -> None:
        facts = self.parser.parse("앱을 설치하세요.", {
            "app_installation_requests": [{"value": "앱 설치", "evidence": evidence("앱을 설치하세요.")}],
        }, source_ref="stt_excerpt_42")
        self.assertEqual(facts.app_installation_requests[0].evidence.source_ref, "stt_excerpt_42")

    def test_p0_t1_rejects_whitespace_only_evidence(self) -> None:
        with self.assertRaisesRegex(ContextFactsValidationError, "non-whitespace"):
            self.parser.parse("검찰입니다.", {
                "impersonated_entities": [{"value": "검찰", "evidence": evidence("   ")}],
            })

    def test_p0_t2_rejects_transfer_demand_when_evidence_says_do_not_transfer(self) -> None:
        facts = self.parser.parse("500만원은 절대로 송금하지 마세요.", {
            "demands": [{"action": "송금", "amount_krw": 5_000_000,
                         "evidence": evidence("500만원은 절대로 송금하지 마세요.")}],
        })
        self.assertEqual(facts.demands, [])
        self.assertTrue(any("explicitly negates a transfer" in warning for warning in facts.warnings))

    def test_p0_t3_rejects_impersonation_when_evidence_explicitly_denies_entity(self) -> None:
        facts = self.parser.parse("검찰이 아니라 은행 직원입니다.", {
            "impersonated_entities": [{"value": "검찰", "evidence": evidence("검찰이 아니라 은행 직원입니다.")}],
        })
        self.assertEqual(facts.impersonated_entities, [])

    def test_p0_t4_rejects_app_installation_fact_when_evidence_denies_installation(self) -> None:
        facts = self.parser.parse("앱을 설치하지 않았습니다.", {
            "app_installation_requests": [{"value": "앱 설치", "evidence": evidence("앱을 설치하지 않았습니다.")}],
        })
        self.assertEqual(facts.app_installation_requests, [])

    def test_p0_t5_rejects_credential_fact_when_evidence_denies_sharing(self) -> None:
        facts = self.parser.parse("OTP 번호는 알려주지 않았습니다.", {
            "credential_requests": [{"value": "OTP 제공", "evidence": evidence("OTP 번호는 알려주지 않았습니다.")}],
        })
        self.assertEqual(facts.credential_requests, [])

    def test_p0_t6_rejects_amount_absent_from_evidence(self) -> None:
        facts = self.parser.parse("100만원과 500만원 이야기가 나왔습니다.", {
            "demands": [{"action": "송금", "amount_krw": 10_000_000,
                         "evidence": evidence("100만원과 500만원")}],
            "mentioned_amounts": [{"amount_krw": 10_000_000, "evidence": evidence("100만원과 500만원")}],
        })
        self.assertIsNone(facts.demands[0].amount_krw)
        self.assertEqual(facts.mentioned_amounts, [])
        self.assertTrue(any("demand amount_krw was removed" in warning for warning in facts.warnings))
        self.assertTrue(any("mentioned amount was rejected" in warning for warning in facts.warnings))

    def test_p0_t7_accepts_amount_present_in_evidence(self) -> None:
        facts = self.parser.parse("500만원을 보내라고 했습니다.", {
            "mentioned_amounts": [{"amount_krw": 5_000_000, "evidence": evidence("500만원을 보내라고 했습니다.")}],
        })
        self.assertEqual(facts.mentioned_amounts[0].amount_krw, 5_000_000)

    def test_p0_t8_parser_marks_new_facts_as_ai_extracted(self) -> None:
        facts = self.parser.parse("검찰 수사관입니다.", {
            "impersonated_entities": [{"value": "검찰", "evidence": evidence("검찰 수사관입니다.")}],
        })
        self.assertIs(facts.impersonated_entities[0].status, FactStatus.AI_EXTRACTED)

    def test_p0_t9_parser_does_not_trust_llm_human_or_verified_status(self) -> None:
        for proposed_status in ("human_confirmed", "verified"):
            with self.subTest(proposed_status=proposed_status):
                facts = self.parser.parse("검찰 수사관입니다.", {
                    "impersonated_entities": [{
                        "value": "검찰",
                        "status": proposed_status,
                        "evidence": evidence("검찰 수사관입니다."),
                    }],
                })
                self.assertIs(facts.impersonated_entities[0].status, FactStatus.AI_EXTRACTED)
                self.assertTrue(any("status was normalized" in warning for warning in facts.warnings))

    def test_r1_keeps_app_installation_request_when_customer_did_not_install(self) -> None:
        facts = self.parser.parse("상대방이 원격제어 앱을 설치하라고 했지만 저는 설치하지 않았습니다.", {
            "app_installation_requests": [{
                "value": "원격제어 앱 설치",
                "evidence": evidence("원격제어 앱을 설치하라고 했지만 저는 설치하지 않았습니다."),
            }],
        })
        self.assertEqual(len(facts.app_installation_requests), 1)
        self.assertNotIn("app_installed", facts.model_dump())

    def test_r2_keeps_credential_request_when_customer_did_not_share(self) -> None:
        facts = self.parser.parse("OTP 번호를 알려달라고 했지만 알려주지 않았습니다.", {
            "credential_requests": [{
                "value": "OTP 번호 제공",
                "evidence": evidence("OTP 번호를 알려달라고 했지만 알려주지 않았습니다."),
            }],
        })
        self.assertEqual(len(facts.credential_requests), 1)
        self.assertNotIn("credential_exposure", facts.model_dump())

    def test_r3_keeps_transfer_demand_and_evidence_backed_amount_when_not_transferred(self) -> None:
        facts = self.parser.parse("500만원을 보내라고 했지만 송금하지 않았습니다.", {
            "demands": [{
                "action": "송금",
                "amount_krw": 5_000_000,
                "evidence": evidence("500만원을 보내라고 했지만 송금하지 않았습니다."),
            }],
        })
        self.assertEqual(len(facts.demands), 1)
        self.assertEqual(facts.demands[0].amount_krw, 5_000_000)
        self.assertNotIn("money_transferred", facts.model_dump())

    def test_r4_keeps_personal_information_request_when_not_provided(self) -> None:
        facts = self.parser.parse("주민등록번호를 말해달라고 했지만 제공하지 않았습니다.", {
            "personal_information_requests": [{
                "value": "주민등록번호 제공",
                "evidence": evidence("주민등록번호를 말해달라고 했지만 제공하지 않았습니다."),
            }],
        })
        self.assertEqual(len(facts.personal_information_requests), 1)
        self.assertNotIn("personal_information_exposure", facts.model_dump())

    def test_r5_rejects_app_installation_request_from_safety_guidance(self) -> None:
        facts = self.parser.parse("은행 직원이 원격제어 앱을 설치하지 말라고 안내했습니다.", {
            "app_installation_requests": [{
                "value": "원격제어 앱 설치",
                "evidence": evidence("은행 직원이 원격제어 앱을 설치하지 말라고 안내했습니다."),
            }],
        })
        self.assertEqual(facts.app_installation_requests, [])

    def test_r6_rejects_credential_request_from_safety_guidance(self) -> None:
        facts = self.parser.parse("OTP 번호는 누구에게도 알려주지 마세요.", {
            "credential_requests": [{
                "value": "OTP 번호 제공",
                "evidence": evidence("OTP 번호는 누구에게도 알려주지 마세요."),
            }],
        })
        self.assertEqual(facts.credential_requests, [])
