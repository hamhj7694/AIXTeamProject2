from __future__ import annotations

import unittest

from ai_api.app.domains.case_support.context_facts import StructuredCaseFacts
from ai_api.app.domains.case_support.context_narrative import ContextNarrativeBuilder


def evidence(text: str, *, source_ref: str | None = None) -> dict[str, str]:
    item = {"evidence_text": text}
    if source_ref is not None:
        item["source_ref"] = source_ref
    return item


def fact(value: str, source: str, *, source_ref: str | None = None) -> dict[str, object]:
    return {"value": value, "evidence": evidence(source, source_ref=source_ref)}


class ContextNarrativeBuilderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = ContextNarrativeBuilder()

    def test_n1_links_impersonation_claim_and_five_million_won_demand(self) -> None:
        result = self.builder.build(StructuredCaseFacts.model_validate({
            "impersonated_entities": [fact("검찰", "검찰 수사관입니다.")],
            "claims": [fact("계좌가 범죄에 연루됨", "계좌가 범죄에 연루됐습니다.")],
            "demands": [{"action": "송금", "amount_krw": 5_000_000,
                         "evidence": evidence("500만원을 송금하세요.")}],
        }))
        self.assertIn("검찰", result.narrative)
        self.assertIn("계좌가 범죄에 연루됨", result.narrative)
        self.assertIn("5,000,000원", result.narrative)
        self.assertNotIn("피해자", result.narrative)

    def test_n2_keeps_transfer_app_and_credential_requests(self) -> None:
        result = self.builder.build(StructuredCaseFacts.model_validate({
            "demands": [{"action": "송금", "evidence": evidence("돈을 보내세요.")}],
            "app_installation_requests": [fact("원격제어 앱 설치", "원격제어 앱을 설치하세요.")],
            "credential_requests": [fact("인증번호와 비밀번호 제공", "인증번호와 비밀번호를 알려주세요.")],
        }))
        self.assertIn("송금", result.narrative)
        self.assertIn("원격제어 앱 설치", result.narrative)
        self.assertIn("인증번호와 비밀번호 제공", result.narrative)

    def test_n3_does_not_invent_an_amount(self) -> None:
        result = self.builder.build(StructuredCaseFacts.model_validate({
            "demands": [{"action": "송금", "evidence": evidence("돈을 보내세요.")}],
        }))
        self.assertIn("송금", result.narrative)
        self.assertNotIn("원", result.narrative)

    def test_n4_does_not_invent_an_impersonated_entity(self) -> None:
        result = self.builder.build(StructuredCaseFacts.model_validate({
            "claims": [fact("문제가 발생함", "문제가 생겼습니다.")],
        }))
        self.assertIn("문제가 발생함", result.narrative)
        self.assertNotIn("검찰", result.narrative)
        self.assertNotIn("경찰", result.narrative)

    def test_n5_renders_each_claim_and_demand_in_separate_sentences(self) -> None:
        result = self.builder.build(StructuredCaseFacts.model_validate({
            "claims": [
                fact("계좌 범죄 연루", "계좌가 범죄에 연루됐습니다."),
                fact("신분증 도용", "신분증이 도용됐습니다."),
            ],
            "demands": [
                {"action": "송금", "evidence": evidence("100만원을 보내세요.")},
                {"action": "앱 설치", "evidence": evidence("앱도 설치하세요.")},
            ],
        }))
        for value in ("계좌 범죄 연루", "신분증 도용", "송금", "앱 설치"):
            self.assertIn(value, result.narrative)
        self.assertGreaterEqual(result.narrative.count("."), 3)

    def test_n6_mentions_only_declared_unresolved_items(self) -> None:
        result = self.builder.build(StructuredCaseFacts.model_validate({
            "unresolved_items": [{"description": "실제 송금 여부", "related_evidence": [evidence("송금 여부는 확인되지 않았습니다.")]}],
        }))
        self.assertIn("아직 확인되지 않은 사항", result.narrative)
        self.assertIn("실제 송금 여부", result.narrative)
        self.assertNotIn("확정", result.narrative)

    def test_n7_empty_facts_with_warnings_use_safe_fallback(self) -> None:
        result = self.builder.build(StructuredCaseFacts(warnings=["발췌문이 짧습니다."]))
        self.assertEqual(result.narrative, "현재 제공된 구조화 사실로는 사건 내용을 조립할 수 없습니다.")
        self.assertEqual(result.warnings, ["발췌문이 짧습니다."])
        self.assertEqual(result.evidence_refs, [])

    def test_n8_credential_request_is_not_rendered_as_credential_exposure(self) -> None:
        result = self.builder.build(StructuredCaseFacts.model_validate({
            "credential_requests": [fact("OTP 제공", "OTP를 알려주세요.")],
        }))
        self.assertIn("OTP 제공", result.narrative)
        self.assertIn("요청", result.narrative)
        self.assertNotIn("제공했습니다", result.narrative)

    def test_n9_app_installation_request_is_not_rendered_as_completed_installation(self) -> None:
        result = self.builder.build(StructuredCaseFacts.model_validate({
            "app_installation_requests": [fact("원격제어 앱 설치", "원격제어 앱을 설치하세요.")],
        }))
        self.assertIn("앱 설치 요청", result.narrative)
        self.assertNotIn("설치했습니다", result.narrative)

    def test_n10_renders_all_amounts_without_selecting_a_maximum(self) -> None:
        result = self.builder.build(StructuredCaseFacts.model_validate({
            "mentioned_amounts": [
                {"amount_krw": 1_000_000, "evidence": evidence("100만원")},
                {"amount_krw": 5_000_000, "evidence": evidence("500만원")},
            ],
        }))
        self.assertIn("1,000,000원", result.narrative)
        self.assertIn("5,000,000원", result.narrative)

    def test_n11_keeps_used_provenance_separate_from_narrative(self) -> None:
        result = self.builder.build(StructuredCaseFacts.model_validate({
            "claims": [fact("범죄 연루", "범죄에 연루됐습니다.", source_ref="excerpt-a")],
            "demands": [{"action": "송금", "evidence": evidence("송금하세요.", source_ref="excerpt-b")}],
        }))
        self.assertIn("범죄 연루", result.narrative)
        self.assertEqual([item.source_ref for item in result.evidence_refs], ["excerpt-a", "excerpt-b"])
        self.assertEqual(result.used_fact_types, ["claims", "demands"])

    def test_n12_does_not_add_names_organizations_or_actions_absent_from_facts(self) -> None:
        result = self.builder.build(StructuredCaseFacts.model_validate({
            "claims": [fact("계좌 확인 필요", "계좌 확인이 필요합니다.")],
        }))
        self.assertIn("계좌 확인 필요", result.narrative)
        self.assertNotIn("김민수", result.narrative)
        self.assertNotIn("은행", result.narrative)
        self.assertNotIn("신고", result.narrative)
