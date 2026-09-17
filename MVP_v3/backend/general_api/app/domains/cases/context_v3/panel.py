from __future__ import annotations

import re
from typing import Any

from contracts.public_api.case_context_v2 import (
    PublicCaseContextResourcesV2,
    PublicContextPanelItemV3,
    PublicContextPanelSectionV3,
    PublicContextPanelV3,
    PublicStructuredAtomV3,
    PublicStructuredContextV3,
    PublicStructuredRelationV3,
    PublicStructuredSignalV3,
)

from .semantic_keys import SENSITIVE_KEYS, mask_sensitive_text, section_for_key
from .grounded import grounded_fact_item, validate_grounded_fact

ACTION_LABELS = {
    "PAYMENT_HOLD_REVIEW": "지급정지 검토", "ACCOUNT_REPORT_GUIDANCE": "기관 신고 안내",
    "EVIDENCE_PRESERVATION": "증거자료 보존", "DEVICE_SECURITY_GUIDANCE": "기기·계정 보호 안내",
    "CUSTOMER_CALLBACK": "고객 재확인", "OTHER": "기타 대응 업무",
}


def _item(**values: Any) -> PublicContextPanelItemV3:
    return PublicContextPanelItemV3(**values)


def _grounded_display(fact: Any, case: dict[str, Any] | None = None) -> str:
    """Render a persisted Fact and enforce its epistemic status before display."""
    plan = grounded_fact_item(fact, context=case)
    try:
        validate_grounded_fact(fact, plan["text"], case)
    except ValueError:
        # A historical or malformed proposal must not take down the entire
        # Context Panel. Keep the item visible as an explicitly unresolved
        # review item instead of exposing a semantically broadened sentence.
        return f"{fact.display_label}: 구조화 근거 불일치로 재검토 필요"
    return str(plan["text"])


def _projection_marker(fact: Any, target: str, display: str) -> tuple[str, str, str | None]:
    """Deduplicate retries, but keep distinct Atom-backed facts visible."""
    atom_id = next(
        (str(ref.get("id") if isinstance(ref, dict) else ref.id)
         for ref in (fact.evidence_refs or [])
         if str(ref.get("type") if isinstance(ref, dict) else ref.type) == "STRUCTURED_ATOM"
         and (ref.get("id") if isinstance(ref, dict) else ref.id)),
        None,
    )
    return target, display, atom_id


def _canonical_confirmed_facts(facts: list[Any]) -> list[Any]:
    """Collapse the confirmed view without discarding multi-event transfers.

    A Context Fact table is an audit-friendly history, not a ready-made
    sentence.  Summary text must therefore remove superseded/rejected rows,
    use the newest row for ordinary semantic slots, and retain distinct
    confirmed money events so the UI does not silently lose a real transfer.
    """
    active = [fact for fact in facts if fact.status == "CONFIRMED"]
    grouped: dict[str, list[Any]] = {}
    for fact in active:
        grouped.setdefault(str(fact.semantic_key), []).append(fact)
    result: list[Any] = []
    for semantic_key, group in grouped.items():
        ordered = sorted(group, key=lambda item: getattr(item, "updated_at", None), reverse=True)
        if semantic_key == "transfer.actual.amount":
            seen: set[str] = set()
            for fact in reversed(ordered):
                marker = str(fact.display_value)
                if marker not in seen:
                    seen.add(marker)
                    result.append(fact)
            continue
        result.append(ordered[0])
    return sorted(result, key=lambda item: getattr(item, "updated_at", None), reverse=True)


def _preferred_atom_id(
    semantic_key: str | None, display_value: str, atoms: list[dict[str, Any]],
) -> str | None:
    text = display_value.casefold()
    for atom in atoms:
        predicate = str(atom.get("predicate") or "").upper()
        cues = {str(cue).upper() for cue in atom.get("lexical_cues", [])}
        if semantic_key == "offender.incident_claim" and predicate.startswith("CLAIMS_"):
            return str(atom.get("atom_id"))
        if semantic_key == "exposure.authentication_information" and (
            atom.get("auth_secret_type") or predicate in {"DISCLOSE_OTP", "REQUEST_AUTH_INFO"}
        ):
            return str(atom.get("atom_id"))
        if semantic_key == "exposure.personal_information" and ("PERSONAL" in predicate or "SENSITIVE_INFO" in cues):
            return str(atom.get("atom_id"))
        if semantic_key == "device.remote_control_app" and (
            "DEVICE" in predicate or "DEVICE_CONTROL" in cues or "REMOTE" in predicate
        ):
            return str(atom.get("atom_id"))
        if semantic_key == "circumstance.demand":
            if ("송금" in text or "이체" in text) and ("TRANSFER" in predicate or "TRANSFER" in cues):
                return str(atom.get("atom_id"))
            if ("통화" in text or "외부" in text) and (
                atom.get("communication_control") or predicate in {"AVOID_EXTERNAL_CONTACT", "KEEP_CALL"}
            ):
                return str(atom.get("atom_id"))
        if semantic_key == "circumstance.tactic":
            if ("고립" in text or "연락" in text) and (
                atom.get("communication_control") or atom.get("isolation_pressure")
            ):
                return str(atom.get("atom_id"))
            if ("긴급" in text or "압박" in text) and atom.get("urgency"):
                if atom.get("urgency") not in {None, "NONE", "UNKNOWN", "UNKNOWN_DEADLINE"}:
                    return str(atom.get("atom_id"))
            if ("불안" in text or "공포" in text) and (atom.get("fear_pressure") not in {None, "NONE"} or atom.get("threat_type")):
                return str(atom.get("atom_id"))
    return None


def _structured_atom_summary(
    semantic_key: str | None, display_value: str, atom: dict[str, Any],
) -> str:
    text = display_value.casefold()
    if semantic_key == "offender.incident_claim":
        phrase = "상대방이 기관·사건을 내세운 주장"
    elif semantic_key == "exposure.authentication_information":
        phrase = "인증정보 제공 요구"
    elif semantic_key == "exposure.personal_information":
        phrase = "개인정보 제공 요구"
    elif semantic_key == "device.remote_control_app":
        phrase = "원격제어 앱 설치 요구"
    elif semantic_key == "transfer.requested.amount":
        phrase = f"{display_value} 금액 요구"
    elif semantic_key == "circumstance.demand" and ("송금" in text or "이체" in text):
        phrase = "송금·이체 요구 정황"
    elif semantic_key == "circumstance.demand" and ("통화" in text or "외부" in text):
        phrase = "외부 확인·연락 제한 요구 정황"
    elif semantic_key == "circumstance.tactic" and ("고립" in text or "연락" in text):
        phrase = "외부 연락을 제한한 정황"
    elif semantic_key == "circumstance.tactic" and ("긴급" in text or "압박" in text):
        phrase = "긴급 처리를 요구한 정황"
    elif semantic_key == "circumstance.tactic" and ("불안" in text or "공포" in text):
        phrase = "불안·공포를 유발한 정황"
    else:
        phrase = "관련 구조화 분석 정황"
    return f"분석 근거 · {phrase}"


def _enrich_evidence_refs(
    refs: list[dict[str, Any]], *, case: dict[str, Any], messages: list[dict[str, Any]], view: str,
    semantic_key: str | None = None, display_value: str = "",
) -> list[dict[str, Any]]:
    """Keep the evidence toggle, but give staff a useful, privacy-safe lineage summary."""
    if view != "bank":
        return []
    diagnosis = case.get("diagnosis") or {}
    signals = {
        str(signal.get("signal_id")): str(signal.get("signal_code") or "구조화 신호")
        for signal in diagnosis.get("context_signals", [])
    }
    atoms = {
        str(atom.get("atom_id")): str(atom.get("predicate") or atom.get("atom_class") or "구조화 Atom")
        for atom in diagnosis.get("semantic_atoms", [])
    }
    atom_rows_by_id = {
        str(atom.get("atom_id")): atom for atom in diagnosis.get("semantic_atoms", [])
    }
    atom_rows = diagnosis.get("semantic_atoms", [])
    preferred_atom_id = _preferred_atom_id(semantic_key, display_value, atom_rows)
    message_by_id = {str(message.get("message_id")): message for message in messages}
    enriched: list[dict[str, Any]] = []
    for raw_ref in refs or []:
        ref = dict(raw_ref)
        if ref.get("summary"):
            enriched.append(ref)
            continue
        ref_type = str(ref.get("type", ""))
        ref_id = str(ref.get("id", ""))
        if preferred_atom_id and ref_type in {"STRUCTURED_SIGNAL", "STRUCTURED_ATOM"} and ref_id != preferred_atom_id:
            ref_type = "STRUCTURED_ATOM"
            ref_id = preferred_atom_id
            ref["type"] = ref_type
            ref["id"] = ref_id
        summary = ""
        if ref_type == "MESSAGE":
            message = message_by_id.get(ref_id)
            content = re.sub(r"\s+", " ", str((message or {}).get("content", ""))).strip()
            if content:
                suffix = "…" if len(content) > 96 else ""
                summary = f'대화 기록 · "{mask_sensitive_text(content[:96])}{suffix}"'
            else:
                summary = "대화 기록 · 연결된 메시지"
        elif ref_type == "STRUCTURED_SIGNAL":
            if ref_id in signals:
                summary = f"구조화 Signal · {signals[ref_id]}"
            elif ref_id in atoms:
                # Compatibility for facts created before Atom/Signal lineage
                # was separated in the persistence contract.
                summary = _structured_atom_summary(semantic_key, display_value, atom_rows_by_id[ref_id])
            else:
                summary = f"구조화 Signal · {ref_id}"
        elif ref_type == "STRUCTURED_ATOM":
            atom = atom_rows_by_id.get(ref_id)
            summary = _structured_atom_summary(semantic_key, display_value, atom) if atom else f"분석 근거 · 연결된 구조화 정황"
        else:
            labels = {
                "QUESTION_ANSWER": "고객 답변", "BANK_TRANSACTION": "거래 기록",
                "VERIFICATION_RESULT": "기관 확인 결과", "ATTACHMENT": "첨부 자료",
                "STAFF_RECORD": "담당자 기록",
            }
            summary = f"{labels.get(ref_type, '기타 근거')} · 연결된 기록"
        ref["summary"] = summary[:300]
        enriched.append(ref)
    return enriched


def _structured_context(case: dict[str, Any], *, view: str) -> PublicStructuredContextV3 | None:
    """Project the persisted A-part result without exposing source utterances."""
    if view != "bank":
        return None
    diagnosis = case.get("diagnosis") or {}
    atoms = [
        PublicStructuredAtomV3(
            atom_id=str(atom["atom_id"]), atom_class=str(atom["atom_class"]),
            predicate=str(atom["predicate"]), action_state=atom.get("action_state"),
            modality=atom.get("modality"), claim_status=str(atom.get("claim_status", "UNVERIFIED")),
            source_turn_id=int(atom["source_turn_id"]),
        )
        for atom in diagnosis.get("semantic_atoms", [])
    ]
    relations = [
        PublicStructuredRelationV3(
            relation_id=str(relation["relation_id"]), relation_type=str(relation["relation_type"]),
            source_atom_id=str(relation["source_atom_id"]), target_atom_id=str(relation["target_atom_id"]),
            confidence=float(relation["confidence"]),
        )
        for relation in diagnosis.get("semantic_relations", [])
    ]
    signals = [
        PublicStructuredSignalV3(
            signal_id=str(signal["signal_id"]), signal_code=str(signal["signal_code"]),
            severity=str(signal["severity"]), confidence=float(signal["confidence"]),
            claim_status=str(signal["claim_status"]), atom_ids=[str(atom_id) for atom_id in signal.get("atom_ids", [])],
        )
        for signal in diagnosis.get("context_signals", [])
    ]
    context_features = diagnosis.get("case_context_features") or {}
    feature_keys = (
        "claimed_actor_types", "claim_codes", "requested_action_codes",
        "manipulation_tactic_codes", "exposure_risk_codes", "unknown_fields",
    )
    feature_codes = {
        key: [str(value) for value in context_features.get(key, [])]
        for key in feature_keys
        if context_features.get(key)
    }
    return PublicStructuredContextV3(
        source_revision=max(1, int(case.get("context_revision", 1))),
        atoms=atoms, relations=relations, signals=signals, feature_codes=feature_codes,
    )

def _build_summary_lines(
    case: dict[str, Any],
    resources: PublicCaseContextResourcesV2,
    verifications: list[dict[str, Any]],
    actions: list[dict[str, Any]],
    summary_override: Any | None,
) -> list[str]:
    """Build the deterministic Summary projection from current Case state."""
    if summary_override is not None:
        lines = str(summary_override.staff_text).splitlines()
    else:
        lines = [str(case.get("initial_brief") or "사건 초기 내용이 등록되었습니다.")]

    lines.append(
        f"위험도 {case.get('risk_level', case.get('risk', '확인 중'))} · "
        f"진행 상태 {case.get('status', 'TRIAGE')}"
    )

    active_facts = []
    seen_fact_markers: set[tuple[str, str, str | None]] = set()
    for fact in resources.facts:
        if fact.status not in {"CONFIRMED", "PROPOSED"}:
            continue
        marker = _projection_marker(fact, section_for_key(fact.semantic_key), _grounded_display(fact, case))
        if marker in seen_fact_markers:
            continue
        seen_fact_markers.add(marker)
        active_facts.append(fact)
    confirmed_facts = _canonical_confirmed_facts(active_facts)
    proposed_count = sum(1 for fact in active_facts if fact.status == "PROPOSED")
    lines.append(f"확정 사실 {len(confirmed_facts)}건 · 검토 대기 {proposed_count}건")

    fact_parts: list[str] = []
    actual_amounts = [fact for fact in confirmed_facts if fact.semantic_key == "transfer.actual.amount"]
    if actual_amounts:
        values = [
            mask_sensitive_text(fact.display_value) if fact.semantic_key in SENSITIVE_KEYS else fact.display_value
            for fact in actual_amounts
        ]
        total = sum(
            int(fact.value.get("amount_krw") or 0)
            for fact in actual_amounts
            if isinstance(fact.value, dict) and str(fact.value.get("amount_krw", "")).lstrip("-").isdigit()
        )
        fact_parts.append(
            f"실제 이체 {len(values)}건 · 합계 {total:,}원: " + ", ".join(values)
        )
    for fact in [fact for fact in confirmed_facts if fact.semantic_key != "transfer.actual.amount"][:2]:
        value = mask_sensitive_text(fact.display_value) if fact.semantic_key in SENSITIVE_KEYS else fact.display_value
        fact_parts.append(f"{fact.display_label}: {value}")
    if fact_parts:
        lines.append("확인된 사실 · " + " / ".join(fact_parts))

    completed_verifications = [
        verification for verification in verifications
        if verification.get("status") == "COMPLETED"
    ]
    if completed_verifications:
        lines.append(f"확인 완료 {len(completed_verifications)}건")
        verification_parts = [
            str(
                verification.get("result_summary")
                or verification.get("claim")
                or verification.get("target")
                or "확인 완료"
            )
            for verification in completed_verifications[:2]
        ]
        lines.append("확인 결과 · " + " / ".join(verification_parts))

    action_parts: list[str] = []
    action_status_labels = {
        "REQUESTED": "진행 중 조치",
        "IN_PROGRESS": "진행 중 조치",
        "COMPLETED": "완료된 조치",
    }
    for action in actions:
        if action.get("actor_type") not in {None, "BANK_STAFF"}:
            continue
        action_type = str(action.get("action_type") or "OTHER")
        if action_type.startswith("CUSTOMER_PROGRESS:"):
            continue
        status = str(action.get("status") or "REQUESTED")
        status_label = action_status_labels.get(status)
        if status_label is None:
            continue
        title = str(action.get("title") or ACTION_LABELS.get(action_type, "담당자 조치"))
        note = str(action.get("note") or "").strip()
        action_parts.append(f"{title} ({status_label})" + (f": {note}" if note else ""))
        if len(action_parts) >= 2:
            break
    if action_parts:
        lines.append("직원 조치 · " + " / ".join(action_parts))

    return lines


def build_summary_projection(
    case: dict[str, Any],
    resources: PublicCaseContextResourcesV2,
    verifications: list[dict[str, Any]],
    actions: list[dict[str, Any]],
    display_items: list[Any] | None = None,
) -> dict[str, Any]:
    """Return the current deterministic Summary and its source revision.

    Final Report preparation can reuse this read-only projection without
    recreating an older ``initial_brief``-only input.  No persistence occurs.
    """
    revision = max(1, int(case.get("context_revision", 1)))
    override = next(
        (
            item for item in (display_items or [])
            if item.section == "SUMMARY"
            and item.semantic_key == "display"
            and item.deleted_by is None
            and item.staff_text
            and item.base_projection_revision == revision
        ),
        None,
    )
    lines = _build_summary_lines(case, resources, verifications, actions, override)
    return {
        "text": "\n".join(lines),
        "lines": lines,
        "source_revision": revision,
        "override_applied": override is not None,
        "override": override,
    }


def build_context_panel_v3(
    case: dict[str, Any], resources: PublicCaseContextResourcesV2, *, view: str,
    verifications: list[dict[str, Any]], actions: list[dict[str, Any]],
    messages: list[dict[str, Any]], progress: list[Any],
    display_items: list[Any] | None = None,
) -> PublicContextPanelV3:
    sections: dict[str, PublicContextPanelSectionV3] = {
        "SUMMARY": PublicContextPanelSectionV3(section_id="SUMMARY", title="현재 사건 요약"),
        "EXPOSURE": PublicContextPanelSectionV3(section_id="EXPOSURE", title="피해·노출"),
        "IMPERSONATION_CONTACT": PublicContextPanelSectionV3(section_id="IMPERSONATION_CONTACT", title="사칭·접촉 정보"),
        "FRAUD_CIRCUMSTANCES": PublicContextPanelSectionV3(section_id="FRAUD_CIRCUMSTANCES", title="사기 정황"),
        "FACT_VERIFICATION": PublicContextPanelSectionV3(section_id="FACT_VERIFICATION", title="사실·확인 현황"),
        "STAFF_ACTIONS": PublicContextPanelSectionV3(section_id="STAFF_ACTIONS", title="직원 조치·결과"),
        "CUSTOMER_SHARE": PublicContextPanelSectionV3(section_id="CUSTOMER_SHARE", title="고객 공유"),
    }

    revision = max(1, int(case.get("context_revision", 1)))
    summary_override = next((item for item in (display_items or []) if item.section == "SUMMARY" and item.semantic_key == "display" and item.deleted_by is None and item.staff_text and item.base_projection_revision == revision), None)
    summary_lines = str(summary_override.staff_text).splitlines() if summary_override else [str(case.get("initial_brief") or "사건 초기 내용이 등록되었습니다.")]
    summary_lines.append(f"위험도 {case.get('risk_level', case.get('risk', '확인 중'))} · 진행 상태 {case.get('status', 'TRIAGE')}")
    projected_fact_statuses: dict[tuple[str, str, str | None], str] = {}
    fact_status_order = {"CONFIRMED": 0, "PROPOSED": 1, "REJECTED": 2, "SUPERSEDED": 3}
    for fact in sorted(resources.facts, key=lambda item: fact_status_order.get(item.status, 9)):
        if fact.status in {"REJECTED", "SUPERSEDED"}:
            continue
        marker = _projection_marker(fact, section_for_key(fact.semantic_key), _grounded_display(fact, case))
        projected_fact_statuses.setdefault(marker, fact.status)
    confirmed_count = sum(status == "CONFIRMED" for status in projected_fact_statuses.values())
    proposed_count = sum(status == "PROPOSED" for status in projected_fact_statuses.values())
    summary_lines.append(f"확정 사실 {confirmed_count}건 · 검토 대기 {proposed_count}건")
    summary_projection = build_summary_projection(case, resources, verifications, actions, display_items)
    revision = summary_projection["source_revision"]
    summary_override = summary_projection["override"]
    summary_lines = summary_projection["lines"]

    override_line_count = len(str(summary_override.staff_text).splitlines()) if summary_override else 0
    for index, text in enumerate(summary_lines[:8]):
        sections["SUMMARY"].items.append(_item(
            item_id=f"summary-{index}", semantic_key=f"summary.bullet_{index + 1}", label="요약",
            display_value=text, value={"text": text},
            source_kind="STAFF_OVERRIDE" if summary_override and index < override_line_count else "DETERMINISTIC_PROJECTION",
            status="CURRENT",
        ))

    if view == "bank":
        # Legacy 조치 기록은 actions journal에 저장되므로 Context V3의 담당자 조치에도 투영한다.
        for action in actions:
            if action.get("actor_type") not in {None, "BANK_STAFF"} or str(action.get("action_type", "")).startswith("CUSTOMER_PROGRESS:"):
                continue
            status = str(action.get("status", "REQUESTED"))
            status = {"REQUESTED": "TODO", "IN_PROGRESS": "IN_PROGRESS", "COMPLETED": "COMPLETED", "CANCELLED": "CANCELLED"}.get(status, status)
            action_type = str(action.get("action_type") or "OTHER")
            title = str(action.get("title") or ACTION_LABELS.get(action_type, "담당자 조치"))
            sections["STAFF_ACTIONS"].groups.setdefault("completed" if status in {"COMPLETED", "CANCELLED"} else "active", []).append(_item(
                item_id=str(action["action_id"]), semantic_key=f"action.{str(action.get('action_type', 'record')).lower()}",
                label=title, display_value=str(action.get("note") or ""),
                value={}, source_kind="ACTION_RECORD", status=status,
                visibility=str(action.get("visibility") or "BANK_INTERNAL"), version=int(action.get("version", 1)),
            ))
        seen_fact_projections: set[tuple[str, str, str | None]] = set()
        for fact in sorted(resources.facts, key=lambda item: fact_status_order.get(item.status, 9)):
            if fact.status == "REJECTED":
                target = section_for_key(fact.semantic_key)
                masked = fact.semantic_key in SENSITIVE_KEYS
                display = mask_sensitive_text(_grounded_display(fact, case))
                marker = _projection_marker(fact, target, display)
                if marker in seen_fact_projections:
                    continue
                seen_fact_projections.add(marker)
                sections[target].groups.setdefault("archived", []).append(_item(
                    item_id=fact.fact_id, semantic_key=fact.semantic_key, label=fact.display_label,
                    display_value=display, value=fact.value, source_kind=fact.source_kind, status=fact.status,
                    confidence=fact.confidence, evidence_refs=_enrich_evidence_refs(fact.evidence_refs, case=case, messages=messages, view=view, semantic_key=fact.semantic_key, display_value=fact.display_value), visibility=fact.visibility,
                    masked=masked, version=fact.version,
                ))
                continue
            if fact.status == "SUPERSEDED":
                continue
            masked = fact.semantic_key in SENSITIVE_KEYS
            display = mask_sensitive_text(_grounded_display(fact, case))
            target = section_for_key(fact.semantic_key)
            marker = _projection_marker(fact, target, display)
            if marker in seen_fact_projections:
                continue
            seen_fact_projections.add(marker)
            panel_item = _item(
                item_id=fact.fact_id, semantic_key=fact.semantic_key, label=fact.display_label,
                display_value=display, value=fact.value, source_kind=fact.source_kind, status=fact.status,
                confidence=fact.confidence, evidence_refs=_enrich_evidence_refs(fact.evidence_refs, case=case, messages=messages, view=view, semantic_key=fact.semantic_key, display_value=fact.display_value), visibility=fact.visibility,
                masked=masked, version=fact.version,
            )
            if target == "FRAUD_CIRCUMSTANCES":
                group = "claims" if fact.semantic_key == "offender.incident_claim" else "demands" if fact.semantic_key == "circumstance.demand" else "tactics"
                sections[target].groups.setdefault(group, []).append(panel_item)
            else:
                sections[target].items.append(panel_item)

        for gap in resources.gaps:
            if gap.status in {"RESOLVED", "DISMISSED"}:
                continue
            sections["FACT_VERIFICATION"].groups.setdefault("needs_attention", []).append(_item(
                item_id=gap.gap_id, semantic_key=gap.semantic_key, label=gap.title, display_value=gap.reason,
                value={"priority": gap.priority}, source_kind=gap.source, status=gap.status,
                evidence_refs=_enrich_evidence_refs(gap.evidence_refs, case=case, messages=messages, view=view), version=gap.version,
            ))
        for verification in verifications:
            group = "confirmed" if verification.get("status") == "COMPLETED" else "failed" if verification.get("status") == "FAILED" else "in_progress"
            sections["FACT_VERIFICATION"].groups.setdefault(group, []).append(_item(
                item_id=str(verification["verification_task_id"]), semantic_key="verification.institution",
                label=str(verification.get("target") or "기관 확인"),
                display_value=str(verification.get("result_summary") or verification.get("claim") or "확인 중"),
                value={"method": verification.get("method")}, source_kind="OFFICIAL_VERIFICATION",
                status=str(verification.get("status", "PENDING")), version=int(verification.get("version", 1)),
            ))
        for task in resources.tasks:
            group = "completed" if task.status in {"COMPLETED", "CANCELLED"} else "active"
            sections["STAFF_ACTIONS"].groups.setdefault(group, []).append(_item(
                item_id=task.task_id, semantic_key=f"task.{task.task_type.lower()}", label=task.title,
                display_value=task.result_summary or task.description, value={"priority": task.priority},
                source_kind=task.source, status=task.status, evidence_refs=_enrich_evidence_refs(task.evidence_refs, case=case, messages=messages, view=view), version=task.version,
            ))
        for suggestion in resources.ai_suggestions:
            if suggestion.status == "PROPOSED":
                sections["STAFF_ACTIONS"].groups.setdefault("suggestions", []).append(_item(
                    item_id=suggestion.suggestion_id, semantic_key=f"suggestion.{suggestion.suggestion_type.lower()}",
                    label=suggestion.title, display_value=suggestion.rationale, value={"priority": suggestion.priority},
                    source_kind="AI_SUGGESTION", status=suggestion.status, evidence_refs=_enrich_evidence_refs(suggestion.evidence_refs, case=case, messages=messages, view=view),
                    version=suggestion.version,
                ))

    shared: list[PublicContextPanelItemV3] = []
    for fact in resources.facts:
        if fact.status == "CONFIRMED" and fact.visibility == "CUSTOMER_SHARED":
            shared.append(_item(item_id=fact.fact_id, semantic_key=fact.semantic_key, label=fact.display_label,
                                display_value=_grounded_display(fact, case), value=fact.value, source_kind=fact.source_kind,
                                status=fact.status, evidence_refs=_enrich_evidence_refs(fact.evidence_refs, case=case, messages=messages, view=view, semantic_key=fact.semantic_key, display_value=fact.display_value), visibility=fact.visibility, version=fact.version))
    for verification in verifications:
        if verification.get("status") == "COMPLETED" and verification.get("customer_visible"):
            shared.append(_item(item_id=str(verification["verification_task_id"]), semantic_key="customer.verification_result",
                                label=str(verification.get("target") or "기관 확인 결과"), display_value=str(verification.get("result_summary") or "확인 완료"),
                                value={}, source_kind="OFFICIAL_VERIFICATION", status="PUBLISHED"))
    for task in resources.tasks:
        if task.status == "COMPLETED" and task.customer_visibility == "RESULT_PUBLISHED":
            shared.append(_item(item_id=task.task_id, semantic_key="customer.task_result", label=task.title,
                                display_value=task.result_summary or "완료", value={}, source_kind="STAFF_RECORD", status="PUBLISHED"))
    for item in progress:
        status = getattr(item, "status", "UNKNOWN")
        if status == "UNKNOWN":
            continue
        summary = getattr(item, "summary", "") or getattr(item, "status_label", status)
        next_action = getattr(item, "next_action", "")
        shared.append(_item(item_id=f"progress-{getattr(item, 'step', 'unknown')}", semantic_key="customer.progress",
                            label=getattr(item, "label", "처리 진행 상황"), display_value=f"{summary}{f' · 다음: {next_action}' if next_action else ''}",
                            value={"status": status}, source_kind="CUSTOMER_PROGRESS", status=status,
                            version=max(1, int(getattr(item, "revision", 0) or 1)), visibility="CUSTOMER_SHARED"))
    for message in messages:
        if message.get("visibility") != "CUSTOMER" or message.get("actor_type") not in {"BANK_STAFF", "CUSTOMER_AGENT"}:
            continue
        shared.append(_item(item_id=str(message["message_id"]), semantic_key="customer.shared_message", label="고객 안내",
                            display_value=str(message.get("content", "")), value={}, source_kind="PUBLIC_MESSAGE", status="PUBLISHED",
                            visibility="CUSTOMER_SHARED"))
    sections["CUSTOMER_SHARE"].items = shared

    if view == "customer":
        for key, section in sections.items():
            if key != "CUSTOMER_SHARE":
                section.items = []
                section.groups = {}

    order = ["SUMMARY", "EXPOSURE", "IMPERSONATION_CONTACT", "FRAUD_CIRCUMSTANCES", "FACT_VERIFICATION", "STAFF_ACTIONS", "CUSTOMER_SHARE"]
    return PublicContextPanelV3(
        case_id=str(case["case_id"]), view=view, source_revision=revision,
        updated_at=case.get("updated_at"),
        structured_context=_structured_context(case, view=view),
        sections=[sections[key] for key in order],
    )
