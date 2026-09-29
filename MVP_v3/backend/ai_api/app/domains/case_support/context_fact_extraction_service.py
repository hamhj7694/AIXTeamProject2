from __future__ import annotations

import re

from contracts.ai_internal.context_fact_extraction import ContextFactExtractionInput, ContextFactExtractionOutput, ContextFactProposal, ContextUnmappedObservation


_MONEY = re.compile(r"(?P<amount>\d[\d,]*(?:\.\d+)?)\s*(?P<unit>억|천만|백만|만|원)")


def _amount_krw(match: re.Match[str]) -> int:
    amount = float(match.group("amount").replace(",", ""))
    multiplier = {"억": 100_000_000, "천만": 10_000_000, "백만": 1_000_000, "만": 10_000, "원": 1}[match.group("unit")]
    return int(amount * multiplier)


class ContextFactExtractionService:
    """Extract source-linked case updates from each committed human message."""

    async def extract(self, request: ContextFactExtractionInput) -> ContextFactExtractionOutput:
        text = _expand_unambiguous_correction(request)
        compact = re.sub(r"\s+", "", text)
        proposals: list[ContextFactProposal] = []
        unmapped: list[ContextUnmappedObservation] = []
        labels = {
            "transfer.actual.status": "실제 이체 여부", "transfer.requested.amount": "요구 금액",
            "transfer.actual.amount": "실제 이체 금액", "transfer.promised_return.amount": "반환 약속 금액", "exposure.authentication_information": "인증정보 노출",
            "exposure.identity_or_card": "신분증·카드정보 노출", "exposure.personal_information": "개인정보 노출",
            "device.remote_control_app": "원격제어 앱",
            "offender.claimed_organization": "사칭 기관", "offender.claimed_person_or_role": "사칭 인물·역할",
            "offender.incident_claim": "상대방 주장", "circumstance.demand": "상대방 요구",
            "circumstance.tactic": "압박·조작 수법",
        }

        def add(key: str, value: dict, display: str, confidence: float = .88, *, staff_attested: bool = False,
                supersedes_fact_id: str | None = None) -> None:
            # Explicit staff-reported checks are a strong internal working
            # signal, not a ledger record or a lifecycle review. Keep the
            # distinction in the existing JSON value; no schema migration.
            if staff_attested and request.message.actor_type == "BANK_STAFF":
                value = {**value, "staff_attestation": "EXPLICIT_STAFF_CHECK"}
            if request.message.actor_type == 'BANK_STAFF' and (key.startswith('transfer.actual.') or key.startswith('exposure.') or key == 'device.remote_control_app') and value.get('status') not in {'UNKNOWN', 'REQUESTED', 'PLANNED'}:
                value = {**value, 'staff_reported': True}
            proposals.append(ContextFactProposal(
                semantic_key=key, display_label=labels[key], value=value, display_value=display,
                confidence=confidence, evidence_message_id=request.message.message_id,
                supersedes_fact_id=supersedes_fact_id,
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

        uncertain = bool(re.search(r"[?？]|했는지|됐는지|했을지|모르|불확실|확실하지|여부.*확인(?:필요|해야)", compact))
        supplied = _was_supplied(compact) and not uncertain
        denied_supply = r"(?:제공|전달|입력|기재|전송)(?:은|는|을|를)?(?:안했|안함|하지않|하지못|안됐)|알려주지않|안알려줬|보내지않"
        not_supplied = not uncertain and bool(re.search(denied_supply, compact))
        if supplied and not_supplied and any(cue in compact for cue in ("정정", "잘못", "아니라", "사실은", "실제로는", "알고보니")):
            positive_index = max(compact.rfind(action) for action in (
                "알려줬", "알려주었", "전달했", "제공했", "보냈어", "보냈습니다", "입력했", "기재했",
                "말해줬", "보여줬", "전송했",
            ))
            negative_index = max(match.start() for match in re.finditer(denied_supply, compact))
            if negative_index > positive_index:
                supplied = False
            else:
                not_supplied = False
        staff_check = request.message.actor_type == "BANK_STAFF" and _explicit_staff_check(compact)
        demanded = any(term in compact for term in (
            "알려달", "보내라", "보내라고", "요구했", "요청했", "입력하라", "제공하라고",
            "말하라고", "적으라고", "기재하라고", "전송하라고", "설치하라고", "설치해달라고", "깔라고",
        ))
        if "OTP" in text.upper() or any(term in text for term in ("인증번호", "보안코드", "인증정보", "비밀번호")):
            if supplied:
                add("exposure.authentication_information", {"status": "EXPOSED", "types": ["OTP_OR_AUTH_CODE"]}, "OTP·인증정보를 전달함", staff_attested=staff_check,
                    supersedes_fact_id=_status_correction_target(request, "exposure.authentication_information", "EXPOSED"))
            elif not_supplied:
                add("exposure.authentication_information", {"status": "NOT_EXPOSED"}, "인증정보를 제공하지 않음", staff_attested=staff_check,
                    supersedes_fact_id=_status_correction_target(request, "exposure.authentication_information", "NOT_EXPOSED"))
            if demanded:
                add("circumstance.demand", {"kind": "AUTHENTICATION_INFORMATION", "text": text}, "OTP·인증정보 제공 요구")
        if any(term in compact for term in ("개인정보", "주민등록번호", "주민등록증", "신분증", "주소", "생년월일", "전화번호", "휴대전화번호")):
            if supplied:
                add("exposure.personal_information", {"status": "EXPOSED"}, "개인정보를 제공함", staff_attested=staff_check,
                    supersedes_fact_id=_status_correction_target(request, "exposure.personal_information", "EXPOSED"))
            elif not_supplied:
                add("exposure.personal_information", {"status": "NOT_EXPOSED"}, "개인정보를 제공하지 않음", staff_attested=staff_check,
                    supersedes_fact_id=_status_correction_target(request, "exposure.personal_information", "NOT_EXPOSED"))
            if demanded:
                add("circumstance.demand", {"kind": "PERSONAL_INFORMATION", "text": "개인정보 제공 요구"}, "개인정보 제공 요구")
        if supplied and any(term in compact for term in ("카드번호", "신분증", "주민등록증")):
            kinds = (["CARD_INFORMATION"] if "카드" in text else []) + (["IDENTITY_DOCUMENT"] if "신분증" in text or "주민등록증" in text else [])
            add("exposure.identity_or_card", {"status": "EXPOSED", "types": kinds}, "신분증·카드정보를 전달함", staff_attested=staff_check)
        if any(term in compact for term in ("원격제어앱", "원격앱", "애니데스크", "팀뷰어", "화면공유")):
            not_installed = any(term in compact for term in (
                "설치안했", "설치하지않", "설치안함", "안설치했", "안깔았", "깔지않", "설치한적없", "깔은적없",
            ))
            installed = not not_installed and any(term in compact for term in (
                "설치했", "깔았", "설치함", "설치됐", "설치됨", "이미설치",
            ))
            requested_app = any(term in compact for term in ("설치하라고", "설치해달라고", "설치해라", "깔라고", "설치요구", "설치하라"))
            if (installed or not_installed) and not uncertain:
                status = "NOT_INSTALLED" if not_installed else "INSTALLED"
                add("device.remote_control_app", {"status": status}, "원격제어 앱을 설치하지 않음" if not_installed else "원격제어 앱을 설치함", staff_attested=staff_check,
                    supersedes_fact_id=_status_correction_target(request, "device.remote_control_app", status))
            elif requested_app:
                add("device.remote_control_app", {"status": "REQUESTED"}, "원격제어 앱 설치 요구")
        if any(term in compact for term in ("검찰", "검사라고", "경찰", "금감원", "금융감독원", "은행직원")):
            organization = next((name for name in ("금융감독원", "검찰", "경찰", "은행") if name in text), "기관")
            add("offender.claimed_organization", {"name": organization, "claimed": True}, f"{organization} 사칭")
            role = next((name for name in ("검사", "수사관", "경찰관", "은행 직원") if name.replace(" ", "") in compact), None)
            if role:
                add("offender.claimed_person_or_role", {"role": role}, role)
            if any(term in compact for term in ("이라고", "라며", "라고말")):
                add("offender.incident_claim", {"text": text}, text[:1000], .82)
        transfer_denied = bool(re.search(r"(?:송금|이체)(?:은|는|을|를)?(?:안했|안함|하지않|하지못)|보내지않|안보냈", compact))
        if transfer_denied and not uncertain:
            add("transfer.actual.status", {"status": "NOT_TRANSFERRED"}, "송금하지 않음", staff_attested=staff_check)
        for money in _MONEY.finditer(text):
            amount = _amount_krw(money)
            if _is_corrected_away_amount(text, money):
                continue
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
            sent = any(term in after for term in (
                "보냈", "송금했", "송금하고", "송금했다", "송금함", "송금했대", "송금했데",
                "이체했", "이체하고", "이체했대", "이체했데", "입금했", "입금하고",
            ))
            reported_completed = _completed_transfer_claim(after) or (request.message.actor_type == 'BANK_STAFF' and bool(re.search(r'(?:송금|이체)(?:을|이)?확인(?:됨|했|완료)', after)))
            local_text = compact[max(0, money.start() - 30):min(len(compact), money.end() + 36)]
            attested_transfer = (
                request.message.actor_type == "BANK_STAFF"
                and _explicit_staff_check(local_text)
                and reported_completed
            )
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
            elif not uncertain and not transfer_denied and (sent or reported_completed or (request.message.actor_type == 'BANK_STAFF' and any(f.semantic_key == 'transfer.actual.amount' for f in request.existing_facts) and
                any(c in compact for c in ('추가', '아니라', '아니고', '정정')) and not requested and not any(c in compact for c in ('요구', '예정', '할까', '?')))):
                corrected_amount_fact = _correction_target(
                    request, "transfer.actual.amount", amount, text[:money.start()],
                )
                corrected_status_fact = _correction_target(
                    request, "transfer.actual.status", None, text[:money.start()],
                ) if corrected_amount_fact else None
                add("transfer.actual.status", {"status": "TRANSFERRED"}, "송금했음", staff_attested=attested_transfer,
                    supersedes_fact_id=corrected_status_fact)
                previous = [f for f in request.existing_facts if f.semantic_key == 'transfer.actual.amount' and f.status not in {'REJECTED', 'SUPERSEDED'}]
                corrected = next((f for f in previous if f.fact_id == corrected_amount_fact), None)
                repeated = next((f for f in previous if f.value.get('amount_krw') == amount and f.value.get('direction') == 'OUT'), None)
                is_additional = any(c in compact for c in ('추가', '두번째', '세번째', '또송금', '더송금'))
                event_id = (corrected.value.get('event_id') or corrected.fact_id) if corrected else (repeated.value.get('event_id') or repeated.fact_id) if repeated and not is_additional else f"{request.message.message_id}:{money.start()}"
                add("transfer.actual.amount", {"amount_krw": amount, "currency": "KRW", "direction": "OUT", "amount_role": "TRANSFER_OUT", "amount_scope": scope, "event_id": event_id}, f"{amount:,}원 송금", staff_attested=attested_transfer,
                    supersedes_fact_id=corrected_amount_fact)
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
        unique = {(item.semantic_key, item.display_value, item.value.get('event_id')): item for item in proposals}
        unique_unmapped = {item.observation_id: item for item in unmapped}
        return ContextFactExtractionOutput(
            proposals=list(unique.values()), unmapped_observations=list(unique_unmapped.values())
        )


def _explicit_staff_check(compact: str) -> bool:
    """Recognize a reported completed check, not a request or future intention."""
    if any(term in compact for term in (
        "확인필요", "확인부탁", "확인해주세요", "확인해야", "확인할예정", "확인해보겠습니다",
        "확인해보도록", "확인안했", "확인못했", "확인하지않", "조회안했", "조회못했",
    )):
        return False
    return bool(re.search(
        r"(?:내가|제가|직접)?(?:확인(?:해?보니|해?보니까|해?봤더니|했(?:어|습니다|다)?|됨|됐|되었|완료)"
        r"|조회(?:해?보니|해?보니까|해?봤더니|했(?:어|습니다|다)?|됨|됐|완료))",
        compact,
    ))


def _correction_target(request: ContextFactExtractionInput, semantic_key: str, new_amount: int | None,
                      earlier_text: str) -> str | None:
    compact = re.sub(r"\s+", "", request.message.content)
    correction_cues = ("정정", "수정", "잘못", "아니라", "아니고", "앞서말한", "아까말한")
    if not any(cue in compact for cue in correction_cues):
        return None
    candidates = [fact for fact in request.existing_facts
                  if fact.semantic_key == semantic_key and fact.status not in {"REJECTED", "SUPERSEDED"}]
    if not candidates:
        return None
    if new_amount is not None:
        prior_amounts = {_amount_krw(match) for match in _MONEY.finditer(earlier_text)}
        matched = [fact for fact in candidates
                   if isinstance(fact.value.get("amount_krw"), int)
                   and fact.value["amount_krw"] in prior_amounts]
        if matched:
            return matched[-1].fact_id
    return candidates[-1].fact_id


def _status_correction_target(request: ContextFactExtractionInput, semantic_key: str, new_status: str) -> str | None:
    """Replace only one clearly contradicted outcome, never a separate demand."""
    if not any(cue in re.sub(r"\s+", "", request.message.content) for cue in
               ("정정", "수정", "잘못", "아니라", "아니고", "사실은", "실제로는", "알고보니")):
        return None
    opposites = {
        "EXPOSED": "NOT_EXPOSED", "NOT_EXPOSED": "EXPOSED",
        "INSTALLED": "NOT_INSTALLED", "NOT_INSTALLED": "INSTALLED",
    }
    prior_status = opposites.get(new_status)
    if prior_status is None:
        return None
    candidates = [fact for fact in request.existing_facts
                  if fact.semantic_key == semantic_key and fact.status == "PROPOSED"
                  and fact.value.get("status") == prior_status]
    return candidates[0].fact_id if len(candidates) == 1 else None


def _is_corrected_away_amount(text: str, money: re.Match[str]) -> bool:
    tail = re.sub(r"\s+", "", text[money.end():money.end() + 60])
    return bool(re.search(
        r"(?:아니라|아니고|대신|잘못(?:말|적|기록)|정정(?:하면|해서|하여)).{0,35}\d[\d,]*(?:\.\d+)?\s*(?:억|천만|백만|만|원)",
        tail,
    ))


def _expand_unambiguous_correction(request: ContextFactExtractionInput) -> str:
    """Infer an omitted unit only from a uniquely matching existing transfer."""
    text = request.message.content.strip()
    if request.message.actor_type != 'BANK_STAFF' or _MONEY.search(text):
        return text
    match = re.fullmatch(r"\s*(\d[\d,]*)\s*(?:이|가)?\s*아니라\s*(\d[\d,]*)\s*(?:이야|야|로\s*정정)?[.!]?\s*", text)
    if not match:
        return text
    old, new = (int(value.replace(',', '')) for value in match.groups())
    candidates = [f for f in request.existing_facts if f.semantic_key == 'transfer.actual.amount'
                  and f.status not in {'REJECTED', 'SUPERSEDED'} and f.value.get('direction') == 'OUT'
                  and f.value.get('amount_krw') in {old, old * 10000}]
    event_ids = {f.value.get('event_id', f.fact_id) for f in candidates}
    if old <= 0 or len(event_ids) != 1:
        return text
    factor = candidates[0].value['amount_krw'] // old
    return f'{old * factor}원이 아니라 {new * factor}원 송금했어'


def _was_supplied(compact: str) -> bool:
    """Recognize affirmative disclosure language without matching a nearby negation."""
    actions = (
        "알려줬", "알려주었", "전달했", "제공했", "보냈어", "보냈습니다", "입력했", "기재했",
        "말해줬", "보여줬", "전송했",
    )
    for action in actions:
        start = 0
        while (index := compact.find(action, start)) >= 0:
            prefix = compact[max(0, index - 8):index]
            suffix = compact[index + len(action):index + len(action) + 5]
            # Korean spacing is already removed. A disclosure preceded by 안/못 or
            # followed by 지않 is a denial, not evidence of provision.
            if not prefix.endswith(("안", "못", "아직")) and not suffix.startswith(("지않", "지못")):
                return True
            start = index + len(action)
    return False


def _completed_transfer_claim(compact: str) -> bool:
    """Detect a completed-transfer assertion while excluding demands/plans."""
    if any(term in compact for term in (
        "송금하라고", "송금하라", "송금해달라", "송금요구", "이체하라고", "이체하라",
        "송금할예정", "송금하려", "이체할예정", "이체하려",
    )):
        return False
    # A denial must not be stored as a completed transfer. Staff often type
    # colloquial forms such as "송금 안 했대" or "보내지 않았다고".
    if re.search(
        r"(?:송금|이체|입금|보내)(?:은|는|을|를|이|가)?(?:안|못|하지않|하지못|한적없|한건아니|아니라)",
        compact,
    ):
        return False
    return bool(re.search(
        r"(?:송금|이체|입금)(?:이|가|은|을)?(?:됐|되었|됨|완료|했(?:어|어요|습니다|다|대|데|음|다고|다니까|다는)?|한(?:것|상태))"
        r"|(?:보냈(?:어|어요|습니다|다|대|데|음|다고|다니까)?|보냄|이체함|송금함)", compact,
    ))
