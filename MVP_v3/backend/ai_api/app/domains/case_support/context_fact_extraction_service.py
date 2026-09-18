from __future__ import annotations

import re

from contracts.ai_internal.context_fact_extraction import ContextFactExtractionInput, ContextFactExtractionOutput, ContextFactProposal, ContextUnmappedObservation


_MONEY = re.compile(r"(?P<amount>\d[\d,]*(?:\.\d+)?)\s*(?P<unit>억|천만|백만|만|원)")


def _amount_krw(match: re.Match[str]) -> int:
    amount = float(match.group("amount").replace(",", ""))
    multiplier = {"억": 100_000_000, "천만": 10_000_000, "백만": 1_000_000, "만": 10_000, "원": 1}[match.group("unit")]
    return int(amount * multiplier)


class ContextFactExtractionService:
    """Bounded extractor. All outputs remain PROPOSED until a staff review."""

    async def extract(self, request: ContextFactExtractionInput) -> ContextFactExtractionOutput:
        text = request.message.content.strip()
        compact = re.sub(r"\s+", "", text)
        proposals: list[ContextFactProposal] = []
        unmapped: list[ContextUnmappedObservation] = []
        labels = {
            "transfer.actual.status": "실제 이체 여부", "transfer.requested.amount": "요구 금액",
            "transfer.actual.amount": "실제 이체 금액", "transfer.promised_return.amount": "반환 약속 금액", "exposure.authentication_information": "인증정보 노출",
            "exposure.identity_or_card": "신분증·카드정보 노출", "device.remote_control_app": "원격제어 앱",
            "offender.claimed_organization": "사칭 기관", "offender.claimed_person_or_role": "사칭 인물·역할",
            "offender.incident_claim": "상대방 주장", "circumstance.demand": "상대방 요구",
            "circumstance.tactic": "압박·조작 수법",
        }

        def add(key: str, value: dict, display: str, confidence: float = .88) -> None:
            proposals.append(ContextFactProposal(
                semantic_key=key, display_label=labels[key], value=value, display_value=display,
                confidence=confidence, evidence_message_id=request.message.message_id,
            ))

        # Open-world safety net: keep only allowlisted lexical features when a
        # domain term has no canonical semantic key yet. Never persist a call
        # transcript or an arbitrary sentence in this extension envelope.
        unknown_terms = {
            "수수료": "FEE", "세금": "TAX", "대출": "LOAN", "가상자산": "CRYPTO",
            "택배": "DELIVERY", "채용": "RECRUITMENT", "구독": "SUBSCRIPTION",
            "환불": "REFUND", "보상": "COMPENSATION", "대리": "IMPERSONATION_PROXY",
        }

        def add_unmapped(term: str, code: str) -> None:
            unmapped.append(ContextUnmappedObservation(
                observation_id=f"obs-{request.message.message_id}-{code.lower()}",
                observation_type="UNCLASSIFIED_DOMAIN_TERM",
                candidate_categories=[code], lexical_codes=[f"DOMAIN.{code}"],
                observed_terms=[{"surface_form": term, "normalized_code": f"DOMAIN.{code}"}],
                source_turn_id=1, confidence=.55,
            ))

        supplied = any(term in compact for term in ("알려줬", "알려주었", "전달했", "제공했", "보냈어", "보냈습니다"))
        demanded = any(term in compact for term in ("알려달", "보내라", "보내라고", "요구했", "요청했", "입력하라"))
        if "OTP" in text.upper() or "인증번호" in text or "보안코드" in text:
            if supplied:
                add("exposure.authentication_information", {"status": "EXPOSED", "types": ["OTP_OR_AUTH_CODE"]}, "OTP·인증정보를 전달함")
            if demanded:
                add("circumstance.demand", {"kind": "AUTHENTICATION_INFORMATION", "text": text}, "OTP·인증정보 제공 요구")
        if supplied and any(term in compact for term in ("카드번호", "신분증", "주민등록증")):
            kinds = (["CARD_INFORMATION"] if "카드" in text else []) + (["IDENTITY_DOCUMENT"] if "신분증" in text or "주민등록증" in text else [])
            add("exposure.identity_or_card", {"status": "EXPOSED", "types": kinds}, "신분증·카드정보를 전달함")
        if any(term in compact for term in ("원격제어앱", "원격앱", "애니데스크", "팀뷰어")):
            status = "INSTALLED" if any(term in compact for term in ("설치했", "깔았", "설치함")) else "REQUESTED"
            add("device.remote_control_app", {"status": status, "text": text}, "원격제어 앱 설치" if status == "INSTALLED" else "원격제어 앱 설치 요구")
        if any(term in compact for term in ("검찰", "검사라고", "경찰", "금감원", "금융감독원", "은행직원")):
            organization = next((name for name in ("금융감독원", "검찰", "경찰", "은행") if name in text), "기관")
            add("offender.claimed_organization", {"name": organization, "claimed": True}, f"{organization} 사칭")
            role = next((name for name in ("검사", "수사관", "경찰관", "은행 직원") if name.replace(" ", "") in compact), None)
            if role:
                add("offender.claimed_person_or_role", {"role": role}, role)
            if any(term in compact for term in ("이라고", "라며", "라고말")):
                add("offender.incident_claim", {"text": text}, text[:1000], .82)
        for money in _MONEY.finditer(text):
            amount = _amount_krw(money)
            before = re.sub(r"\s+", "", text[max(0, money.start() - 12):money.start()])
            after = re.sub(r"\s+", "", text[money.end():money.end() + 22])
            # Classify each amount as a money event.  Do not require the
            # literal word '송금': Korean reports often say "300만원
            # 요구받았다" or "20만원 돌려받았다".
            returned = any(term in after for term in ("돌려받", "반환받", "환급받", "되돌려받", "돌려줬", "돌려주었"))
            # A sentence such as "3천만원 보내면 5천만원으로 돌려줄게요"
            # contains two amounts; only the amount immediately before the
            # promise is the promised return, not the conditional transfer.
            promised_return = any(term in after for term in ("돌려줄", "돌려드릴", "보상", "환급해줄", "되돌려줄")) and not _MONEY.search(after)
            sent = any(term in after for term in ("보냈", "송금했", "송금하고", "송금했다", "송금함", "이체했", "이체하고", "입금했", "입금하고"))
            requested = any(term in after for term in ("보내라고", "보내면", "송금하라", "이체하라", "입금하라", "요구했", "요구받", "요청받", "달라고", "마련하라", "지불하라"))
            scope = (
                "FINAL" if any(marker in text for marker in ("최종", "결과적으로", "마지막으로")) else
                "CUMULATIVE" if any(marker in text for marker in ("총합", "누적", "합계", "전체")) else
                "EVENT"
            )
            if promised_return:
                add("transfer.promised_return.amount", {"amount_krw": amount, "currency": "KRW", "direction": "IN", "amount_role": "REFUND_IN", "amount_scope": scope, "promise_status": "PROMISED"}, f"{amount:,}원 반환 약속")
            elif returned:
                add("transfer.actual.amount", {"amount_krw": amount, "currency": "KRW", "direction": "IN", "amount_role": "REFUND_IN", "amount_scope": scope}, f"{amount:,}원 반환")
            elif sent:
                add("transfer.actual.status", {"status": "TRANSFERRED"}, "이체함")
                add("transfer.actual.amount", {"amount_krw": amount, "currency": "KRW", "direction": "OUT", "amount_role": "TRANSFER_OUT", "amount_scope": scope}, f"{amount:,}원 송금")
            elif requested:
                add("transfer.requested.amount", {"amount_krw": amount, "currency": "KRW", "direction": "REQUEST", "amount_role": "REQUESTED_AMOUNT", "amount_scope": scope}, f"{amount:,}원 요구")
                add("circumstance.demand", {"kind": "TRANSFER", "text": text}, "금전 이체 요구")
        if any(term in compact for term in ("계좌가범죄", "명의도용", "수사중", "안전계좌", "보호계좌")):
            add("offender.incident_claim", {"text": text}, text[:1000], .8)
        if any(term in compact for term in ("지금당장", "전화끊지", "비밀로", "아무에게도말", "시간없")):
            add("circumstance.tactic", {"text": text}, text[:1000], .82)
        for term, code in unknown_terms.items():
            known_refund = any(
                item.semantic_key in {"transfer.actual.amount", "transfer.promised_return.amount"}
                and item.value.get("amount_role") == "REFUND_IN"
                for item in proposals
            )
            if term in text and not (code in {"REFUND", "COMPENSATION"} and known_refund):
                add_unmapped(term, code)
        unique = {(item.semantic_key, item.display_value): item for item in proposals}
        unique_unmapped = {item.observation_id: item for item in unmapped}
        return ContextFactExtractionOutput(
            proposals=list(unique.values()), unmapped_observations=list(unique_unmapped.values())
        )
