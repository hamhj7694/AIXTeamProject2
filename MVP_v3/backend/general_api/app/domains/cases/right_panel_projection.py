"""Build the bank-facing Right Panel read model from attributed case data.

This is a presentation projection only. It never changes fact lifecycle state,
creates bank transactions, or treats a conversation amount as a bank record.
"""
from __future__ import annotations

import hashlib
import re
from collections import OrderedDict
from typing import Any
from urllib.parse import urlparse


SIGNAL_CATEGORIES = (
    ("identity", "신분·관계"),
    ("claim", "상황·사건 주장"),
    ("demand", "요구 행동"),
    ("pressure", "압박·연락 통제"),
    ("money", "금전 관련 정황"),
    ("exposure", "고객 피해·노출"),
)

_GENERIC = {
    "특정 행동을 요구한 정황", "기관 또는 다른 사람의 신분을 내세운 정황",
    "금전 이동을 요구하거나 언급한 정황", "추가 확인이 필요한 통화 정황",
}


def _dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _key(section: str, value: str) -> str:
    return f"rp:{section.lower()}:{hashlib.sha256(value.encode('utf-8')).hexdigest()[:32]}"


def _storage_key(value: str) -> str:
    if len(value) <= 160:
        return value
    return f"key:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def _item(section: str, semantic_key: str, title: str, *, detail: str = "",
          source_badge: str | None = None, origin: str = "AI_ANALYSIS",
          status: str | None = None, occurred_at: Any = None,
          evidence_refs: list[str] | None = None, actor_id: Any = None,
          version: int | None = None) -> dict[str, Any]:
    return {
        "item_id": _key(section, semantic_key), "section": section,
        "semantic_key": _storage_key(semantic_key), "title": title[:500], "detail": detail[:1200],
        "source_badge": source_badge, "origin": origin, "status": status,
        "occurred_at": _clean(occurred_at) or None,
        "evidence_refs": list(dict.fromkeys(str(ref) for ref in (evidence_refs or []) if ref))[:20],
        "actor_id": _clean(actor_id) or None, "version": version,
    }


def _badge(status: str, speaker: str, actor: str, reported_by: str) -> str:
    roles = {speaker.upper(), actor.upper(), reported_by.upper()}
    if status == "CLAIMED" and "SUSPECTED_PARTY" in roles:
        return "상대방 주장"
    if status == "REQUESTED" and ("SUSPECTED_PARTY" in roles or "CUSTOMER" in roles):
        return "상대방 요구" if "SUSPECTED_PARTY" in roles else "분석 정황"
    if status == "DENIED" and "CUSTOMER" in roles:
        return "고객 부인"
    if status == "REPORTED" and "CUSTOMER" in roles:
        return "고객 진술"
    return "분석 정황"


def _answer_badge(answer: str) -> str:
    normalized = re.sub(r"\s+", "", answer).casefold()
    negative = ("아니", "않았", "안했", "제공하지", "송금하지", "설치하지", "미제공", "미송금", "not_transferred", "not_provided")
    if any(marker in normalized for marker in negative):
        return "고객 부인"
    unclear = ("모르", "기억나지", "확실하지", "확인필요", "잘모르", "unknown")
    return "미확인" if any(marker in normalized for marker in unclear) else "고객 진술"


def _has_official_source(record: dict[str, Any]) -> bool:
    url = _clean(record.get("evidence_url"))
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme.casefold() != "https":
        return False
    host = (parsed.hostname or "").casefold().rstrip(".")
    return any(host == domain or host.endswith("." + domain) for domain in ("go.kr", "gov", "gov.kr"))


def _signal_category(code: str, sentence: str, status: str = "") -> str:
    """Assign a narrative using its action meaning before its entity vocabulary."""
    code = code.upper()
    text = sentence
    # Explicit manipulative tactics take precedence over the action they support.
    if any(part in code for part in ("TACTIC", "ISOLAT", "FEAR", "URGENCY", "PRESSURE", "SECRET", "CONTROL")):
        return "pressure"
    # A request to transfer money is still a request, not a completed money event.
    if status.upper() == "REQUESTED" or any(part in code for part in ("REQUEST", "DEMAND", "INSTRUCT", "TRANSFER")):
        return "demand"
    if any(part in code for part in ("ROLE", "IDENTITY", "ORGANIZATION", "PERSON", "RELATION")):
        return "identity"
    if any(part in code for part in ("CLAIM", "INCIDENT", "CASE", "CRIME", "ARREST")):
        return "claim"
    if any(part in code for part in ("EXPOSURE", "CUSTOMER", "LEAK", "LOSS")):
        return "exposure"
    if any(part in code for part in ("MONEY", "AMOUNT", "REFUND", "ACCOUNT")):
        return "money"
    if any(token in text for token in ("압박", "연락하지", "알리지", "통제", "재촉", "불안을 조성")):
        return "pressure"
    if any(token in text for token in ("요구", "지시", "제공하도록", "설치하도록", "송금하도록", "이체하도록")):
        return "demand"
    if any(token in text for token in ("사칭", "역할로 제시", "신분을 내세")):
        return "identity"
    if any(token in text for token in ("송금", "이체", "계좌", "금액", "환급")):
        return "money"
    return "claim"


def _signal_title(code: str, sentence: str) -> str:
    """Turn generated narrative prose into a short, source-attributed row label."""
    code = code.upper()
    if "REQUEST_PERSONAL_INFO" in code:
        return "개인정보·민감정보 제공 요구"
    if "REQUEST" in code and any(token in sentence for token in ("인증번호", "인증정보", "OTP", "비밀번호")):
        return "인증정보 제공 요구"
    if code in {"ROLE_PROSECUTION", "ROLE_INVESTIGATOR"}:
        return "수사기관 관계자를 사칭해 범죄 연루·조사 주장"
    text = _clean(sentence)
    text = re.sub(r"^(?:보이스피싱 의심 인물이|보이스피싱 의심 인인은|보이스피싱 의심 인인이|상대방이)\s*", "", text)
    text = text.replace("개인 정보", "개인정보").replace("민감 정보", "민감정보")
    text = text.replace("고객 또는 고객 계좌가", "고객 계좌가")
    text = text.replace("김인수라는 인물과", "김인수와")
    text = text.replace("제공하도록 요구함", "제공 요구")
    text = text.replace("송금하도록 요구함", "송금 요구")
    text = text.replace("이체하도록 요구함", "이체 요구")
    text = text.replace("정황이 확인됨", "정황")
    return text.rstrip(" .。")


def _normalize(value: str) -> str:
    return re.sub(r"[\s\W_]+", "", value.casefold(), flags=re.UNICODE)


def _amount_text(amount: Any) -> str:
    try:
        amount_value = int(float(amount))
    except (TypeError, ValueError):
        return "금액"
    if amount_value >= 10_000 and amount_value % 10_000 == 0:
        return f"{amount_value // 10_000:,}만원"
    return f"{amount_value:,}원"


def _amount_from_text(text: str) -> str | None:
    match = re.search(r"(\d[\d,]*(?:\.\d+)?)(\s*만원|\s*원)?", text)
    if not match:
        return None
    try:
        value = float(match.group(1).replace(",", ""))
        unit = (match.group(2) or "").strip()
        return _amount_text(value * 10_000 if unit == "만원" else value)
    except (TypeError, ValueError):
        return None


def _demand_items(case: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
    diagnosis = _dict(case.get("diagnosis"))
    diagnosis_context = _dict(diagnosis.get("context"))
    narratives = [_dict(item) for item in _list(diagnosis_context.get("feature_narratives"))]
    sources: list[tuple[str, list[str]]] = []
    for narrative in narratives:
        if str(narrative.get("status") or "").upper() != "REQUESTED":
            continue
        text = _clean(narrative.get("sentence"))
        if text:
            sources.append((text, [str(ref) for ref in _list(narrative.get("atom_ids")) if ref]))
    # This compatibility field is specifically the alleged offender's demands.
    for text in _list(context.get("offender_demands")):
        clean = _clean(text)
        if clean:
            sources.append((clean, []))
    for text in _list(diagnosis_context.get("demands")):
        clean = _clean(text)
        if clean:
            sources.append((clean, []))

    features = _dict(diagnosis.get("features"))
    requested_amount = _amount_text(features.get("requested_amount_max")) if features.get("requested_amount_max") else None
    rows: list[dict[str, Any]] = []
    for text, evidence in sources:
        normalized = text.casefold()
        request_items: list[tuple[str, str]] = []
        is_transfer = any(token in normalized for token in ("송금", "이체", "자금 이동", "안전계좌"))
        if is_transfer:
            amount = _amount_from_text(text) or requested_amount
            title = f"{amount} 송금 요구" if amount else "송금 요구"
            request_items.append((title, f"상대방이 이체를 요구한 내용 · 실제 송금 여부는 별도 확인"))
        if any(token in normalized for token in ("개인정보", "개인 정보", "민감정보", "민감 정보")):
            request_items.append(("개인정보 제공 요구", "실제 제공 여부는 별도 확인"))
        if any(token in normalized for token in ("인증정보", "인증 정보", "인증번호", "otp", "비밀번호")):
            request_items.append(("인증정보 제공 요구", "실제 제공 여부는 별도 확인"))
        if any(token in normalized for token in ("원격 제어", "원격제어", "화면 공유", "앱 설치")):
            request_items.append(("원격제어 앱 설치 요구", "실제 설치 여부는 별도 확인"))
        for title, detail in request_items:
            rows.append(_item(
                "EXPOSURE", f"demand:{_normalize(title)}", title, detail=detail,
                source_badge="상대방 요구", origin="AI_ANALYSIS", evidence_refs=evidence,
            ))
    return _dedupe(rows)


def _exposure(case: dict[str, Any], context: dict[str, Any], questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = _demand_items(case, context)
    question_fields = OrderedDict([
        ("transfer_status", "실제 송금"),
        ("personal_information_exposure", "실제 개인정보 제공"),
        ("authentication_information_exposure", "실제 인증정보 제공"),
        ("remote_control_app", "원격제어 앱 설치"),
    ])
    for field, label in question_fields.items():
        relevant = [q for q in questions if str(q.get("target_field", "")).casefold() == field]
        answered = next((q for q in reversed(relevant) if q.get("status") == "ANSWERED" and _clean(q.get("answer_text"))), None)
        unresolved_values = [_clean(value).casefold() for value in _list(context.get("unresolved_items"))]
        unresolved = any(
            field in value or (field == "transfer_status" and "송금" in value)
            or (field == "personal_information_exposure" and "개인정보" in value)
            or (field == "authentication_information_exposure" and "인증정보" in value)
            or (field == "remote_control_app" and ("원격" in value or "앱 설치" in value))
            for value in unresolved_values
        )
        answer = _clean(answered.get("answer_text")) if answered else ""
        if answer:
            badge = _answer_badge(answer)
            detail = f"답변: {answer}"
            if badge == "미확인" or unresolved:
                detail += " · 실행 여부 추가 확인 필요"
            items.append(_item("EXPOSURE", f"answer:{field}:{answered.get('question_id')}", label,
                               detail=detail, source_badge=badge, origin="CUSTOMER_ANSWER",
                               occurred_at=answered.get("answered_at"), evidence_refs=[str(answered.get("question_id"))]))
        else:
            case_transfer = str(case.get("victim_transfer_status") or "UNKNOWN").upper() if field == "transfer_status" else "UNKNOWN"
            if field == "transfer_status" and case_transfer in {"YES", "NO"}:
                description = "송금했다고 설명함" if case_transfer == "YES" else "송금하지 않았다고 설명함"
                items.append(_item("EXPOSURE", f"case-answer:{field}", label, detail=description,
                                   source_badge="고객 진술" if case_transfer == "YES" else "고객 부인",
                                   origin="CUSTOMER_ANSWER"))
            else:
                items.append(_item("EXPOSURE", f"unknown:{field}", label,
                                   detail="확인 정보 없음 · 추가 확인 필요", source_badge="미확인"))

    return _dedupe(items)


def _dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result = []
    for item in items:
        normalized = _normalize(item["title"] + item.get("detail", ""))
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(item)
    return result


def _is_internal_code(value: str) -> bool:
    normalized = value.strip()
    return bool(re.fullmatch(r"[A-Z][A-Z0-9_]{1,}", normalized)) or normalized.upper() in {
        "UNKNOWN", "BANK", "COURT", "INVESTIGATOR", "BANK_EMPLOYEE", "SUSPECTED_PARTY",
        "TODAY", "IMMEDIATE", "CASE_NUMBER", "PARTIAL_FUNDS", "ALL_FUNDS",
    }


def _role_display(value: str) -> str | None:
    normalized = _normalize(value)
    if normalized in {"용의자", "suspect", "suspectedparty", "범죄연루자"}:
        return "용의자로 지목"
    if normalized in {"investigator", "수사관", "수사관역할"}:
        return "수사관으로 소개"
    if normalized in {"bankemployee", "은행직원", "은행담당자"}:
        return "은행 직원으로 언급"
    if normalized in {"검찰", "검찰관계자", "prosecution"}:
        return "검찰 관계자로 소개"
    return None


def _placeholder_record(*values: Any) -> bool:
    return any(re.search(r"(?:^|\s)(?:테스트|test|dummy|sample|예시)(?:\s|$)", _clean(value), re.IGNORECASE)
               for value in values)


_CHECKLIST_WORK_LABELS = {
    "transfer_status": "실제 송금 여부 확인",
    "personal_information_exposure": "개인정보 제공 여부 확인",
    "authentication_information_exposure": "인증정보 제공 여부 확인",
    "remote_control_app": "원격제어 앱 설치 여부 확인",
    "transfer_purpose": "송금 요구 목적 확인",
    "claimed_organization": "기관·소속 공식 여부 확인",
    "incident_claim": "사건 주장 확인",
}


def _checklist_work_label(action_type: str) -> str | None:
    parts = action_type.split(":")
    if len(parts) != 3 or parts[0] != "AI_CHECKLIST":
        return None
    return _CHECKLIST_WORK_LABELS.get(parts[2])


def build_right_panel_projection(*, case: dict[str, Any] | None, case_context: dict[str, Any] | None,
                                 questions: list[dict[str, Any]] | None = None,
                                 verifications: list[dict[str, Any]] | None = None,
                                 actions: list[dict[str, Any]] | None = None,
                                 tasks: list[dict[str, Any]] | None = None,
                                 source_revision: int | None = None) -> dict[str, Any]:
    case = _dict(case)
    diagnosis = _dict(case.get("diagnosis"))
    diagnosis_context = _dict(diagnosis.get("context"))
    case_context = _dict(case_context)
    questions = [_dict(item) for item in (questions or [])]
    verifications = [_dict(item) for item in (verifications or [])]
    actions = [_dict(item) for item in (actions or [])]
    tasks = [_dict(item) for item in (tasks or [])]
    signal_groups: OrderedDict[str, list[dict[str, Any]]] = OrderedDict((key, []) for key, _ in SIGNAL_CATEGORIES)
    narratives = [_dict(item) for item in _list(diagnosis_context.get("feature_narratives"))]
    for narrative in sorted(narratives, key=lambda item: min(_list(item.get("source_turns")) or [10**9])):
        text = _clean(narrative.get("sentence"))
        if not text:
            continue
        status = str(narrative.get("status") or "").upper()
        code = str(narrative.get("code") or "")
        category = _signal_category(code, text, status)
        evidence = [str(ref) for ref in _list(narrative.get("atom_ids")) if ref]
        title = _signal_title(code, text)
        source_key = "narrative:" + code + ":" + ":".join(evidence or [_normalize(text)])
        signal_groups[category].append(_item(
            "SIGNAL", source_key, title, source_badge=_badge(status, str(narrative.get("speaker_role") or ""),
            str(narrative.get("actor_role") or ""), str(narrative.get("reported_by_role") or "")),
            evidence_refs=evidence,
        ))
    if not narratives:
        fallbacks = (
            ("identity", "offender_claims"), ("claim", "key_signals"),
            ("demand", "offender_demands"), ("pressure", "manipulation_tactics"),
        )
        for category, field in fallbacks:
            for text in _list(case_context.get(field)):
                clean = _clean(text)
                if clean and clean not in _GENERIC:
                    signal_groups[category].append(_item("SIGNAL", f"fallback:{category}:{_normalize(clean)}", clean, source_badge="분석 정황"))

    # Money-specific details live in exposure; avoid duplicating the same row in signals.
    signal_groups["money"] = [item for item in signal_groups["money"] if not any(
        _normalize(item["title"]) == _normalize(row["title"]) for row in _exposure(case, case_context, questions)
    )]
    fraud_signals = []
    for key, label in SIGNAL_CATEGORIES:
        values = _dedupe(signal_groups[key])
        if values and any(_normalize(item["title"]) not in {_normalize(generic) for generic in _GENERIC} for item in values):
            values = [item for item in values if _normalize(item["title"]) not in {_normalize(generic) for generic in _GENERIC}]
        fraud_signals.append({"key": key, "label": label, "items": values})

    # Only literal people, institutions, organizations and places are exposed.
    # Ontology values such as BANK / INVESTIGATOR are used to add a grounded role
    # to a named person, never rendered as if they were names.
    mentions = [_dict(item) for item in _list(diagnosis.get("semantic_mentions"))]
    mention_by_value = {_normalize(_clean(item.get("normalized_value"))): item for item in mentions
                        if _clean(item.get("normalized_value"))}
    person_values = {
        _normalize(_clean(item.get("normalized_value")))
        for item in mentions if str(item.get("mention_type") or "").upper() == "PERSON_NAME"
        and _clean(item.get("normalized_value")) and not _is_internal_code(_clean(item.get("normalized_value")))
    }
    relations: dict[str, set[str]] = {}
    for narrative in narratives:
        names = [_clean(value) for value in _list(narrative.get("entity_names")) if _clean(value)]
        people = {_normalize(value) for value in names if _normalize(value) in person_values}
        if len(people) != 1:
            continue
        person = next(iter(people))
        role_values = [value for value in names if _role_display(value)]
        role_values.extend(
            _clean(mention.get("normalized_value")) for mention in mentions
            if str(mention.get("mention_type") or "").upper() in {"ROLE", "RELATIONSHIP"}
            and int(mention.get("source_turn_id") or -1) in set(_list(narrative.get("source_turns")))
        )
        labels = {_role_display(value) for value in role_values}
        labels.discard(None)
        # A named suspect remains the relationship shown for that person; the
        # investigator/bank role can describe the caller in the same narrative.
        if "용의자로 지목" in labels:
            labels = {"용의자로 지목"}
        relations.setdefault(person, set()).update(label for label in labels if label)
    role_mentions_by_turn: dict[int, set[str]] = {}
    for mention in mentions:
        if str(mention.get("mention_type") or "").upper() not in {"ROLE", "RELATIONSHIP"}:
            continue
        turn = mention.get("source_turn_id")
        label = _role_display(_clean(mention.get("normalized_value")))
        if isinstance(turn, int) and label:
            role_mentions_by_turn.setdefault(turn, set()).add(label)
    for mention in mentions:
        if str(mention.get("mention_type") or "").upper() != "PERSON_NAME":
            continue
        normalized = _normalize(_clean(mention.get("normalized_value")))
        turn = mention.get("source_turn_id")
        if normalized in person_values and isinstance(turn, int):
            relations.setdefault(normalized, set()).update(role_mentions_by_turn.get(turn, set()))

    grouped_entities: dict[str, dict[str, Any]] = {}
    for mention in sorted(mentions, key=lambda item: int(item.get("sequence_index") or 10**9)):
        kind = str(mention.get("mention_type") or "").upper()
        if kind not in {"PERSON_NAME", "INSTITUTION", "ORGANIZATION", "LOCATION", "CONTACT"}:
            continue
        value = _clean(mention.get("normalized_value"))
        normalized = _normalize(value)
        if not value or not normalized or _is_internal_code(value):
            continue
        mention_id = _clean(mention.get("mention_id")) or f"{kind}:{normalized}"
        speaker = str(mention.get("speaker_role") or "").upper()
        badge = "상대방 주장" if speaker == "SUSPECTED_PARTY" else "고객 진술" if speaker == "CUSTOMER" else "분석 정황"
        entry = grouped_entities.setdefault(normalized, {
            "value": value, "kind": kind, "badge": badge, "refs": [],
        })
        entry["value"] = value
        entry["kind"] = kind
        entry["badge"] = badge
        entry["refs"].append(mention_id)
    entity_items = []
    for normalized, entry in grouped_entities.items():
        detail = " · ".join(sorted(relations.get(normalized, set())))
        entity_items.append(_item(
            "CONTACT", f"entity:{entry['kind'].lower()}:{normalized}", entry["value"],
            detail=detail, source_badge=entry["badge"], evidence_refs=entry["refs"],
        ))

    verification_rows = []
    for record in verifications:
        target = _clean(record.get("target") or record.get("claim"))
        status = str(record.get("status") or "PENDING").upper()
        result = _clean(record.get("result_summary"))
        if not target or _placeholder_record(target, record.get("claim")):
            continue
        official_evidence = _has_official_source(record)
        badge = "공식 확인" if status == "COMPLETED" and result and official_evidence else "직원 기록" if result else "미확인"
        detail = result or ("회신 결과를 기록하지 않았습니다." if status == "COMPLETED" else "확인 결과 대기 중")
        verification_rows.append(_item(
            "VERIFICATION", f"verification:{record.get('verification_task_id') or target}", target,
            detail=detail, source_badge=badge, origin="VERIFICATION",
            status=_verification_status(status), occurred_at=record.get("updated_at") or record.get("created_at"),
            evidence_refs=[str(record.get("verification_task_id"))] if record.get("verification_task_id") else [],
        ))

    incomplete_work, completed_work = [], []
    work_titles: set[str] = set()
    for task in tasks:
        title = _clean(task.get("title"))
        if not title or str(task.get("status") or "").upper() == "CANCELLED":
            continue
        status = str(task.get("status") or "TODO").upper()
        target = completed_work if status == "COMPLETED" else incomplete_work
        task_id = _clean(task.get('task_id'))
        work_titles.add(_normalize(title))
        target.append(_item("WORK", f"task:{task_id or task.get('client_request_id') or title}", title,
                            detail=_clean(task.get("description")), origin="TASK", status=status,
                            occurred_at=task.get("completed_at") or task.get("updated_at") or task.get("created_at"),
                            actor_id=task.get("completed_by"),
                            evidence_refs=[f"task:{task_id}"] if task_id else [],
                            version=int(task.get("version")) if task.get("version") is not None else None))

    for action in actions:
        action_type = _clean(action.get("action_type"))
        title = _checklist_work_label(action_type)
        status = str(action.get("status") or "REQUESTED").upper()
        if not title or status in {"CANCELLED", "FAILED"} or _normalize(title) in work_titles:
            continue
        target = completed_work if status == "COMPLETED" else incomplete_work
        action_id = _clean(action.get("action_id"))
        work_titles.add(_normalize(title))
        target.append(_item(
            "WORK", f"action:{action_id or action_type}", title,
            origin="STAFF_ACTION", status="COMPLETED" if status == "COMPLETED" else "TODO",
            occurred_at=action.get("updated_at") if status == "COMPLETED" else action.get("created_at"),
            evidence_refs=[f"action:{action_id}"] if action_id else [],
            version=int(action.get("version")) if action.get("version") is not None else None,
        ))

    activity = []
    for action in actions:
        action_type = _clean(action.get("action_type"))
        note = _clean(action.get("note"))
        status = str(action.get("status") or "").upper()
        if not action_type or status in {"CANCELLED", "FAILED"}:
            continue

        checklist_label = _checklist_work_label(action_type)
        if checklist_label:
            # Open AI checklist items are follow-up work, not historical events.
            if status != "COMPLETED" or not action.get("updated_at"):
                continue
            action_title = f"업무 완료: {checklist_label}"
            occurred_at = action.get("updated_at")
        elif action_type.startswith("AI_CHECKLIST") or action_type == "STAFF_TASK":
            # Recommendation, gap and compatibility task rows are not activity.
            continue
        elif action_type == "STAFF_JUDGMENT":
            if not note:
                continue
            action_title = note
            occurred_at = action.get("created_at")
        else:
            title = _clean(action.get("title") or note)
            if not title or _is_internal_code(title):
                continue
            action_title = title
            occurred_at = action.get("updated_at") if status == "COMPLETED" else action.get("created_at")
        if not occurred_at:
            continue
        activity.append(_item("ACTIVITY", f"action:{action.get('action_id') or action_type}:{occurred_at}",
                              action_title, detail="업무 완료" if status == "COMPLETED" else "직원 기록",
                              source_badge="직원 기록", origin="STAFF_ACTION", status=status,
                              occurred_at=occurred_at,
                              evidence_refs=[str(action.get("action_id"))] if action.get("action_id") else []))

    for task in tasks:
        title = _clean(task.get("title"))
        completed_at = task.get("completed_at")
        if str(task.get("status") or "").upper() != "COMPLETED" or not title or not completed_at:
            continue
        task_id = _clean(task.get("task_id"))
        activity.append(_item(
            "ACTIVITY", f"task-completed:{task_id or _normalize(title)}:{completed_at}",
            f"업무 완료: {title}", detail=_clean(task.get("result_summary")),
            source_badge="직원 기록", origin="TASK", status="COMPLETED", occurred_at=completed_at,
            evidence_refs=[f"task:{task_id}"] if task_id else [],
        ))

    for record in verifications:
        target = _clean(record.get("target") or record.get("claim"))
        if not target or _placeholder_record(target, record.get("claim")):
            continue
        task_id = _clean(record.get("verification_task_id")) or target
        status = str(record.get("status") or "PENDING").upper()
        created_at = record.get("created_at")
        updated_at = record.get("updated_at")
        if created_at:
            activity.append(_item("ACTIVITY", f"verification-request:{task_id}",
                                  f"기관 확인 요청 기록: {target}", detail="확인 요청 등록",
                                  source_badge="직원 기록", origin="VERIFICATION", occurred_at=created_at,
                                  evidence_refs=[task_id]))
        result = _clean(record.get("result_summary"))
        if status == "COMPLETED" and result and updated_at:
            activity.append(_item("ACTIVITY", f"verification-result:{task_id}",
                                  f"기관 확인 결과 기록: {target}", detail=result,
                                  source_badge="공식 확인" if _has_official_source(record) else "직원 기록",
                                  origin="VERIFICATION", status=status, occurred_at=updated_at,
                                  evidence_refs=[task_id]))
    activity.sort(key=lambda item: item.get("occurred_at") or "", reverse=True)

    summary = _clean(case_context.get("situation_summary"))
    if not summary:
        summary = _clean(case_context.get("summary") or diagnosis_context.get("summary") or case.get("initial_brief"))
    return {
        "schema_version": "right-panel.v1", "current_case_summary": summary,
        "exposure": _exposure(case, case_context, questions), "contact_information": entity_items,
        "fraud_signals": fraud_signals, "verification": verification_rows,
        "incomplete_work": incomplete_work, "completed_work": completed_work,
        "activity": activity, "source_revision": source_revision,
    }


def _verification_status(status: str) -> str:
    return {"PENDING": "대기", "IN_PROGRESS": "진행 중", "COMPLETED": "완료", "FAILED": "실패", "ON_HOLD": "보류"}.get(status, "확인 필요")
