from __future__ import annotations

import json
import os
import re

from openai import AsyncOpenAI

from contracts.ai_internal.context_fact_extraction import ContextFactExtractionInput, ContextFactExtractionOutput, ContextFactProposal, ContextUnmappedObservation


_MONEY = re.compile(r"(?P<amount>\d[\d,]*(?:\.\d+)?)\s*(?P<unit>억|천만|백만|만|원)")


def _amount_krw(match: re.Match[str]) -> int:
    amount = float(match.group("amount").replace(",", ""))
    multiplier = {"억": 100_000_000, "천만": 10_000_000, "백만": 1_000_000, "만": 10_000, "원": 1}[match.group("unit")]
    return int(amount * multiplier)


class ContextFactExtractionService:
    """Legacy deterministic fixture extractor.

    This implementation is intentionally kept for unit fixtures only.  The
    production AI API endpoint uses ``ProviderContextFactExtractionService``
    below, so lexical/rule output cannot be persisted into the case panel.
    """

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
            # Keep each monetary mention as a distinct event, even when the
            # display amount is identical to another mention in this message.
            amount_event_id = f"{request.message.message_id}:amount:{money.start()}"
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
                add("transfer.promised_return.amount", {"amount_krw": amount, "currency": "KRW", "direction": "IN", "amount_role": "REFUND_IN", "amount_scope": scope, "promise_status": "PROMISED", "amount_event_id": amount_event_id}, f"{amount:,}원 반환 약속")
            elif returned:
                add("transfer.actual.amount", {"amount_krw": amount, "currency": "KRW", "direction": "IN", "amount_role": "REFUND_IN", "amount_scope": scope, "amount_event_id": amount_event_id}, f"{amount:,}원 반환")
            elif sent:
                add("transfer.actual.status", {"status": "TRANSFERRED"}, "이체함")
                add("transfer.actual.amount", {"amount_krw": amount, "currency": "KRW", "direction": "OUT", "amount_role": "TRANSFER_OUT", "amount_scope": scope, "amount_event_id": amount_event_id}, f"{amount:,}원 송금")
            elif requested:
                add("transfer.requested.amount", {"amount_krw": amount, "currency": "KRW", "direction": "REQUEST", "amount_role": "REQUESTED_AMOUNT", "amount_scope": scope, "amount_event_id": amount_event_id}, f"{amount:,}원 요구")
                add("circumstance.demand", {"kind": "TRANSFER", "text": text}, "금전 이체 요구")
        if any(term in compact for term in ("계좌가범죄", "명의도용", "수사중", "안전계좌", "보호계좌")):
            add("offender.incident_claim", {"text": text}, text[:1000], .8)
        if any(term in compact for term in ("지금당장", "전화끊지", "비밀로", "아무에게도말", "시간없", "협박", "위협", "체포", "구속", "처벌", "불이익")):
            threat_type = (
                "ARREST" if any(term in compact for term in ("체포", "구속")) else
                "PUNISHMENT" if "처벌" in compact else
                "THREAT" if any(term in compact for term in ("협박", "위협", "불이익")) else
                None
            )
            tactic_value = {"text": text}
            if threat_type:
                tactic_value["threat_type"] = threat_type
            add("circumstance.tactic", tactic_value, text[:1000], .82)
        for term, code in unknown_terms.items():
            known_refund = any(
                item.semantic_key in {"transfer.actual.amount", "transfer.promised_return.amount"}
                and item.value.get("amount_role") == "REFUND_IN"
                for item in proposals
            )
            if term in text and not (code in {"REFUND", "COMPENSATION"} and known_refund):
                add_unmapped(term, code)
        # Amount proposals are keyed by their event id; all other proposals
        # retain the original semantic/display dedupe behavior.
        amount_keys = {
            "transfer.actual.amount",
            "transfer.requested.amount",
            "transfer.promised_return.amount",
        }
        unique = {}
        for item in proposals:
            event_id = item.value.get("amount_event_id") if item.semantic_key in amount_keys else None
            key = (item.semantic_key, item.display_value, str(event_id) if event_id else None)
            unique[key] = item
        unique_unmapped = {item.observation_id: item for item in unmapped}
        return ContextFactExtractionOutput(
            proposals=list(unique.values()), unmapped_observations=list(unique_unmapped.values())
        )


class ProviderContextFactExtractionService:
    """Extract reviewable facts with the configured LLM provider only.

    There is deliberately no deterministic fallback here.  If the provider
    is unavailable, the request fails and the General API leaves the
    extraction job failed; no fact is written to the panel.
    """

    MODEL_VERSION_FALLBACK = "gpt-4o-mini"
    PROMPT_VERSION = "context-fact-openai-v1"

    async def extract(self, request: ContextFactExtractionInput) -> ContextFactExtractionOutput:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY가 없어 실제 LLM 맥락 추출을 시작할 수 없습니다.")

        model = os.getenv("OPENAI_CONTEXT_MODEL", self.MODEL_VERSION_FALLBACK)
        max_output_tokens = int(os.getenv("OPENAI_CONTEXT_FACT_MAX_OUTPUT_TOKENS", "1400"))
        instructions = (
            "너는 CSR 사건 맥락의 사실 제안 추출기다. 반드시 입력 메시지에 명시된 내용만 "
            "검토 가능한 제안(PROPOSED)으로 반환한다. 원문에 없는 기관명·역할·금액·완료 여부를 "
            "추론하거나 기존 사실을 복사해 새 사실로 만들지 않는다. 요청/지시와 실제 수행/완료를 "
            "절대 혼동하지 않는다. 같은 메시지 안의 서로 다른 금액 언급은 각각 별도 사건으로 보존한다. "
            "각 proposal의 evidence_message_id는 입력 message.message_id와 정확히 같아야 한다. "
            "display_label과 display_value는 한국어로 짧고 사실적으로 작성한다. 확신이 없거나 계약의 "
            "semantic_key로 표현할 수 없는 내용은 proposals에 넣지 말고 unmapped_observations에도 "
            "민감한 원문 전체를 복사하지 않는다. 기존 사실은 중복 방지와 맥락 참고용일 뿐, 입력에 "
            "없는 사실을 생성하는 근거가 아니다. 결과는 제공된 JSON schema만 따른다."
        )
        # Replace the legacy prompt above with a plain-text provider contract.
        # The old source text was mojibake and did not reliably explain the
        # police/organization mapping to the model.
        instructions = (
            "You extract reviewable case facts from exactly one Korean message. "
            "Use only information explicitly supported by that message; never infer a concrete "
            "organization, role, amount, password, code disclosure, app installation, or completion. "
            "Keep requested/instructed separate from completed/reported. Every proposal must use "
            "the input message_id as evidence. Use Korean display_label and display_value when possible. "
            "display_value must be a complete, natural Korean sentence that explains the fact; never "
            "return a bare enum, variable name, or organization code as the display value. "
            "If the message says '경찰이라고 사칭했대' or explicitly says the other person claimed "
            "to be police, emit offender.claimed_organization with value containing "
            "organization='경찰', organization_code='POLICE_SERVICE', claimed=true. "
            "If a fact is not explicit, put it in unmapped_observations or omit it. "
            "source_turn_id is always 1 because there is one input message. Return JSON only and "
            "follow the supplied schema."
        )
        instructions += (
            " The Korean lexical marker \uacbd\ucc30 means police and \uc0ac\uce6d means impersonation. "
            "When those markers occur together in the input content, create exactly one "
            "offender.claimed_organization proposal with organization='\uacbd\ucc30', "
            "organization_code='POLICE_SERVICE', and claimed=true; do not leave that explicit fact unmapped."
            " The input content may instead be a JSON INITIAL_CASE_CONTEXT_SNAPSHOT containing "
            "provider-generated semantic_atoms, relations, signals, and context_features. In that "
            "case, treat those fields as the complete evidence set, collapse duplicate observations, "
            "prefer the most concrete observed value, and emit one representative proposal per "
            "distinct semantic fact. Never emit OTHER or UNKNOWN when a concrete code or observed "
            "term exists."
        )
        payload = {
            "message": request.message.model_dump(mode="json"),
            "existing_facts": [item.model_dump(mode="json") for item in request.existing_facts],
        }
        async with AsyncOpenAI(api_key=api_key, timeout=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "20")), max_retries=0) as client:
            response = await client.responses.create(
                model=model,
                instructions=instructions,
                input=json.dumps(payload, ensure_ascii=False),
                max_output_tokens=max_output_tokens,
                store=False,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "context_fact_proposals_v1",
                        "schema": ContextFactExtractionOutput.model_json_schema(),
                        # ``value`` is an intentionally typed envelope whose
                        # keys vary by semantic_key (amount/status/name/text,
                        # etc.).  OpenAI strict Structured Outputs rejects
                        # that open-world dict schema because it requires
                        # ``additionalProperties: false`` on every nested
                        # object.  Keep the outer response schema and validate
                        # the complete payload with Pydantic below, while
                        # allowing the provider to emit the bounded value map.
                        "strict": False,
                    }
                },
            )

        # The provider schema is intentionally non-strict because semantic
        # values are an open envelope.  Normalize only provenance fields that
        # the server can determine without interpreting the user's content:
        # this request contains exactly one source message (turn 1), and the
        # evidence id must be the committed message id, never a model guess.
        raw_output = json.loads(response.output_text)
        raw_output = {
            key: raw_output[key]
            for key in ("schema_version", "proposals", "unmapped_observations", "model_version", "prompt_version")
            if key in raw_output
        }
        for proposal in raw_output.get("proposals", []):
            for key in list(proposal):
                if key not in {"semantic_key", "display_label", "value", "display_value", "confidence", "evidence_message_id"}:
                    proposal.pop(key, None)
            proposal["evidence_message_id"] = request.message.message_id
        for observation in raw_output.get("unmapped_observations", []):
            allowed_observation_keys = {
                "observation_id", "observation_type", "candidate_categories", "lexical_codes",
                "observed_terms", "speech_act", "action_state", "polarity", "modality",
                "amount_role", "amount_value_krw", "source_turn_id", "source_event_id",
                "confidence", "status",
            }
            for key in list(observation):
                if key not in allowed_observation_keys:
                    observation.pop(key, None)
            observation.setdefault("observation_id", f"obs-{request.message.message_id}")
            observation.setdefault("observation_type", "UNKNOWN")
            for list_key in ("candidate_categories", "lexical_codes", "observed_terms"):
                if observation.get(list_key) is None:
                    observation[list_key] = []
            observation["polarity"] = observation.get("polarity") or "UNKNOWN"
            observation["confidence"] = observation.get("confidence") if observation.get("confidence") is not None else 0.0
            observation["status"] = observation.get("status") or "UNMAPPED"
            observation["source_turn_id"] = 1
        output = ContextFactExtractionOutput.model_validate(raw_output)
        # The provider identity is assigned by the server, not trusted from
        # model-generated JSON.  This is used by downstream guards to reject
        # any accidental deterministic/local response.
        return output.model_copy(update={"model_version": model, "prompt_version": self.PROMPT_VERSION})
