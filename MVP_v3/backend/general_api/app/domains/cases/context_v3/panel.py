from __future__ import annotations

from typing import Any

from contracts.public_api.case_context_v2 import (
    PublicCaseContextResourcesV2,
    PublicContextPanelItemV3,
    PublicContextPanelSectionV3,
    PublicContextPanelV3,
)

from .semantic_keys import SENSITIVE_KEYS, mask_sensitive_text, section_for_key

ACTION_LABELS = {
    "PAYMENT_HOLD_REVIEW": "지급정지 검토", "ACCOUNT_REPORT_GUIDANCE": "기관 신고 안내",
    "EVIDENCE_PRESERVATION": "증거자료 보존", "DEVICE_SECURITY_GUIDANCE": "기기·계정 보호 안내",
    "CUSTOMER_CALLBACK": "고객 재확인", "OTHER": "기타 대응 업무",
}


def _item(**values: Any) -> PublicContextPanelItemV3:
    return PublicContextPanelItemV3(**values)


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
    confirmed_count = sum(1 for fact in resources.facts if fact.status == "CONFIRMED")
    proposed_count = sum(1 for fact in resources.facts if fact.status == "PROPOSED")
    summary_lines.append(f"확정 사실 {confirmed_count}건 · 검토 대기 {proposed_count}건")
    for index, text in enumerate(summary_lines[:5]):
        sections["SUMMARY"].items.append(_item(
            item_id=f"summary-{index}", semantic_key=f"summary.bullet_{index + 1}", label="요약",
            display_value=text, value={"text": text}, source_kind="STAFF_OVERRIDE" if summary_override and index < len(str(summary_override.staff_text).splitlines()) else "DETERMINISTIC_PROJECTION", status="CURRENT",
        ))

    if view == "bank":
        # Legacy 조치 기록은 actions journal에 저장되므로 Context V3의 담당자 조치에도 투영한다.
        for action in actions:
            if action.get("actor_type") not in {None, "BANK_STAFF"} or str(action.get("action_type", "")).startswith("CUSTOMER_PROGRESS:"):
                continue
            status = str(action.get("status", "REQUESTED"))
            status = {"REQUESTED": "TODO", "IN_PROGRESS": "IN_PROGRESS", "COMPLETED": "COMPLETED", "CANCELLED": "CANCELLED"}.get(status, status)
            action_type = str(action.get("action_type") or "OTHER")
            sections["STAFF_ACTIONS"].groups.setdefault("completed" if status in {"COMPLETED", "CANCELLED"} else "active", []).append(_item(
                item_id=str(action["action_id"]), semantic_key=f"action.{str(action.get('action_type', 'record')).lower()}",
                label=ACTION_LABELS.get(action_type, "담당자 조치"), display_value=str(action.get("note") or ""),
                value={}, source_kind="ACTION_RECORD", status=status, visibility="BANK_INTERNAL", version=1,
            ))
        for fact in resources.facts:
            if fact.status == "REJECTED":
                target = section_for_key(fact.semantic_key)
                masked = fact.semantic_key in SENSITIVE_KEYS
                display = mask_sensitive_text(fact.display_value) if masked else fact.display_value
                sections[target].groups.setdefault("archived", []).append(_item(
                    item_id=fact.fact_id, semantic_key=fact.semantic_key, label=fact.display_label,
                    display_value=display, value=fact.value, source_kind=fact.source_kind, status=fact.status,
                    confidence=fact.confidence, evidence_refs=fact.evidence_refs, visibility=fact.visibility,
                    masked=masked, version=fact.version,
                ))
                continue
            if fact.status == "SUPERSEDED":
                continue
            masked = fact.semantic_key in SENSITIVE_KEYS
            display = mask_sensitive_text(fact.display_value) if masked else fact.display_value
            target = section_for_key(fact.semantic_key)
            panel_item = _item(
                item_id=fact.fact_id, semantic_key=fact.semantic_key, label=fact.display_label,
                display_value=display, value=fact.value, source_kind=fact.source_kind, status=fact.status,
                confidence=fact.confidence, evidence_refs=fact.evidence_refs, visibility=fact.visibility,
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
                evidence_refs=gap.evidence_refs, version=gap.version,
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
                source_kind=task.source, status=task.status, evidence_refs=task.evidence_refs, version=task.version,
            ))
        for suggestion in resources.ai_suggestions:
            if suggestion.status == "PROPOSED":
                sections["STAFF_ACTIONS"].groups.setdefault("suggestions", []).append(_item(
                    item_id=suggestion.suggestion_id, semantic_key=f"suggestion.{suggestion.suggestion_type.lower()}",
                    label=suggestion.title, display_value=suggestion.rationale, value={"priority": suggestion.priority},
                    source_kind="AI_SUGGESTION", status=suggestion.status, evidence_refs=suggestion.evidence_refs,
                    version=suggestion.version,
                ))

    shared: list[PublicContextPanelItemV3] = []
    for fact in resources.facts:
        if fact.status == "CONFIRMED" and fact.visibility == "CUSTOMER_SHARED":
            shared.append(_item(item_id=fact.fact_id, semantic_key=fact.semantic_key, label=fact.display_label,
                                display_value=fact.display_value, value=fact.value, source_kind=fact.source_kind,
                                status=fact.status, evidence_refs=fact.evidence_refs, visibility=fact.visibility, version=fact.version))
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
        sections=[sections[key] for key in order],
    )
