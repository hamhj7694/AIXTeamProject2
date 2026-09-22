"""Internal compatibility adapter for the retired ``case_facts`` contract.

The public ``/facts`` route is retired with HTTP 410.  These conversion
helpers remain only for old in-memory fixtures and repository methods during
the final cleanup window; production reads, writes, AI input, and frontend
contracts use ``case_context_facts_v2`` directly.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

LEGACY_FIELD_TO_SEMANTIC = {
    "authentication_information_exposure": "exposure.authentication_information",
    "personal_information_exposure": "exposure.personal_information",
    "transfer_status": "transfer.actual.status",
    "requested_amount_krw": "transfer.requested.amount",
    "transfer_purpose": "transfer.purpose",
    "remote_control_app": "device.remote_control_app",
    "claimed_organization": "offender.claimed_organization",
    "incident_claim": "offender.incident_claim",
}
SEMANTIC_TO_LEGACY_FIELD = {value: key for key, value in LEGACY_FIELD_TO_SEMANTIC.items()}

LEGACY_SOURCE_TO_V2 = {
    "AI_EXTRACTED": "AI_EXTRACTION",
    "HUMAN_CONFIRMED": "STAFF_OBSERVATION",
    "VERIFIED": "OFFICIAL_VERIFICATION",
    "UNRESOLVED": "STAFF_OBSERVATION",
}
V2_SOURCE_TO_LEGACY = {value: key for key, value in LEGACY_SOURCE_TO_V2.items()}
V2_SOURCE_TO_LEGACY["CUSTOMER_STATEMENT"] = "UNRESOLVED"
V2_STATUS_TO_LEGACY = {"PROPOSED": "PROPOSED", "CONFIRMED": "CONFIRMED", "REJECTED": "UNRESOLVED", "SUPERSEDED": "UNRESOLVED"}

DISPLAY_LABELS = {
    "exposure.authentication_information": "인증정보 노출 여부",
    "exposure.personal_information": "개인정보 노출 여부",
    "transfer.actual.status": "실제 송금 여부",
    "transfer.requested.amount": "요구 금액",
    "transfer.purpose": "송금 목적",
    "device.remote_control_app": "원격제어 앱 설치 여부",
    "offender.claimed_organization": "상대방이 주장한 기관",
    "offender.incident_claim": "상대방이 주장한 사건",
}


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def legacy_field_for_semantic(semantic_key: str) -> str | None:
    mapped = SEMANTIC_TO_LEGACY_FIELD.get(semantic_key)
    if mapped:
        return mapped
    if semantic_key.startswith("legacy."):
        return semantic_key.removeprefix("legacy.")
    # Keep the compatibility route lossless for newer V2 semantics. The
    # frontend no longer consumes this route, so this is not a display label.
    return semantic_key


def semantic_for_legacy_field(field: str) -> str | None:
    mapped = LEGACY_FIELD_TO_SEMANTIC.get(field)
    if mapped:
        return mapped
    # Custom question targets are still valid V2 facts; namespace them so
    # they cannot collide with the reviewed semantic-key allowlist.
    normalized = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in field.strip().lower())
    return f"legacy.{normalized}" if normalized else None


def source_kind_for_legacy(source: str) -> str:
    try:
        return LEGACY_SOURCE_TO_V2[source]
    except KeyError as exc:
        raise ValueError(f"Unsupported legacy fact source: {source}") from exc


def legacy_row_from_v2(row: dict[str, Any]) -> dict[str, Any]:
    """Convert a V2 DB/public row to the old response shape."""
    field = legacy_field_for_semantic(str(row.get("semantic_key", "")))
    if field is None:
        raise ValueError(f"Unmapped V2 semantic key: {row.get('semantic_key')}")
    source = V2_SOURCE_TO_LEGACY.get(str(row.get("source_kind", "")), "UNRESOLVED")
    status = V2_STATUS_TO_LEGACY.get(str(row.get("status", "")), "UNRESOLVED")
    display_value = row.get("display_value")
    if display_value is None:
        value = row.get("value_json") or row.get("value") or ""
        display_value = value if isinstance(value, str) else str(value)
    confidence = row.get("confidence")
    return {
        "fact_id": row["fact_id"],
        "case_id": row["case_id"],
        "field": field,
        "value": display_value,
        "source": source,
        "status": status,
        "confidence": float(confidence) if confidence is not None else 0.0,
        "evidence_message_id": _first_evidence_id(row.get("evidence_refs_json") or row.get("evidence_refs"), "MESSAGE"),
        "source_question_id": _first_evidence_id(row.get("evidence_refs_json") or row.get("evidence_refs"), "QUESTION_ANSWER"),
        "confirmed_by": row.get("confirmed_by"),
        "confirmed_at": _iso(row.get("confirmed_at")),
        "created_at": _iso(row.get("created_at")),
    }


def _first_evidence_id(value: Any, kind: str) -> str | None:
    if isinstance(value, str):
        import json
        try:
            value = json.loads(value)
        except ValueError:
            return None
    if not isinstance(value, list):
        return None
    for item in value:
        if isinstance(item, dict) and item.get("type") == kind and item.get("id"):
            return str(item["id"])
    return None


def v2_payload_from_legacy(*, field: str, value: str, source: str, status: str = "PROPOSED", confidence: float | None = 0.7,
                           evidence_message_id: str | None = None, source_question_id: str | None = None,
                           fact_id: str | None = None) -> dict[str, Any]:
    semantic_key = semantic_for_legacy_field(field)
    if semantic_key is None:
        raise ValueError(f"Unsupported legacy fact field: {field}")
    if status not in {"PROPOSED", "CONFIRMED"}:
        raise ValueError(f"Unsupported legacy fact status: {status}")
    refs = []
    if evidence_message_id:
        refs.append({"type": "MESSAGE", "id": evidence_message_id})
    if source_question_id:
        refs.append({"type": "QUESTION_ANSWER", "id": source_question_id})
    return {
        "fact_id": fact_id,
        "semantic_key": semantic_key,
        "display_label": DISPLAY_LABELS.get(semantic_key, field),
        "value": {"legacy_value": value, "legacy_field": field},
        "display_value": value,
        "source_kind": source_kind_for_legacy(source),
        "status": status,
        "confidence": confidence,
        "evidence_refs": refs,
    }
