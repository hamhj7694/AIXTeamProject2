from __future__ import annotations

import hashlib
import json
import re
from typing import Any


SEMANTIC_LABELS = {
    "transfer.actual.status": "실제 이체 여부", "transfer.requested.amount": "요구 금액",
    "transfer.actual.amount": "실제 이체 금액", "transfer.promised_return.amount": "반환 약속 금액", "exposure.personal_information": "개인정보 노출",
    "exposure.account_information": "계좌정보 노출", "exposure.authentication_information": "인증정보 노출",
    "exposure.identity_or_card": "신분증·카드정보 노출", "exposure.occurred_at": "노출 시점",
    "device.remote_control_app": "원격제어 앱", "offender.claimed_organization": "사칭 기관",
    "offender.claimed_person_or_role": "사칭 인물·역할", "offender.requested_account": "요구 계좌",
    "offender.contact": "상대방 연락처", "offender.incident_claim": "상대방 주장",
    "circumstance.demand": "상대방 요구", "circumstance.tactic": "압박·조작 수법",
}
ALLOWED_SEMANTIC_KEYS = frozenset(SEMANTIC_LABELS)
SENSITIVE_KEYS = frozenset({"offender.requested_account", "offender.contact"})


def normalized_value(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def proposal_dedupe_key(message_id: str, semantic_key: str, value: dict[str, Any]) -> str:
    digest = hashlib.sha256(f"{message_id}|{semantic_key}|{normalized_value(value)}".encode()).hexdigest()
    return f"msgfact-{digest[:48]}"


def mask_sensitive_text(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", match.group(0))
        return match.group(0) if len(digits) < 7 else f"***-****-{digits[-4:]}"
    return re.sub(r"(?<!\d)(?:\d[ -]?){7,20}(?!\d)", replace, value)


def section_for_key(key: str) -> str:
    if key.startswith(("exposure.", "transfer.", "device.")):
        return "EXPOSURE"
    if key.startswith("offender.") and key != "offender.incident_claim":
        return "IMPERSONATION_CONTACT"
    if key in {"offender.incident_claim", "circumstance.demand", "circumstance.tactic"}:
        return "FRAUD_CIRCUMSTANCES"
    return "FACT_VERIFICATION"

