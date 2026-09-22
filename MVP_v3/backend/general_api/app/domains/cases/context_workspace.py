"""Read-only compatibility projection. Reading never migrates or approves data."""
from contracts.user_text import user_text
from .repository import normalize_target_field


_LEGACY_GAP_KEYS = {
    "transfer_status": "transfer.actual.status",
    "transfer_purpose": "transfer.purpose",
    "personal_information_exposure": "exposure.personal_information",
    "authentication_information_exposure": "exposure.authentication_information",
    "remote_control_app": "device.remote_control_app",
    "claimed_organization": "offender.claimed_organization",
    "incident_claim": "offender.incident_claim",
}


def legacy_gap_details(action):
    parts = action.get("action_type", "").split(":")
    field = normalize_target_field(parts[-1])
    priority = {"P0": "URGENT", "P1": "HIGH", "P2": "NORMAL"}.get(parts[1] if len(parts) > 2 else "", "HIGH")
    return {
        "semantic_key": _LEGACY_GAP_KEYS.get(field, f"legacy.gap.{field.replace('_', '.')}"),
        "title": user_text(field),
        "reason": user_text(action.get("note") or "담당자 확인이 필요한 기존 AI 항목입니다."),
        "priority": priority,
    }


def build_workspace(resources, actions, questions, gap_history=()):
    data = resources.model_dump(mode="json")
    reviewed = {s["dedupe_key"] for s in data["ai_suggestions"]}
    # Inference-first mode: every active Fact is usable context.  Legacy status
    # values remain in storage for compatibility but are not a workflow gate.
    active_facts = [f for f in data["facts"] if f.get("status") not in {"REJECTED", "SUPERSEDED"}]
    known = {normalize_target_field(f["semantic_key"]) for f in active_facts}
    by_field = {}
    for question in questions:
        by_field.setdefault(normalize_target_field(question.get("target_field") or ""), []).append(question)
    legacy_suggestions, legacy_records, legacy_gaps, legacy_archived = [], [], [], []
    seen = set()
    v2_gap_keys = {gap["semantic_key"] for gap in data["gaps"]}
    for action in actions:
        kind = action.get("action_type", "")
        if kind == "STAFF_JUDGMENT":
            legacy_records.append({"id": action["action_id"], "title": user_text(action.get("note") or "기존 직원 기록"), "status": action.get("status"), "created_at": action.get("created_at")})
        if not kind.startswith("AI_CHECKLIST:"):
            continue
        if action.get("status") in {"COMPLETED", "CANCELLED"}:
            legacy_archived.append({"id": action["action_id"], "title": user_text(action.get("note") or "기존 확인 항목"), "status": action.get("status")})
            continue
        details = legacy_gap_details(action)
        field = normalize_target_field(kind.split(":")[-1])
        if field in known:
            continue
        field_questions = by_field.get(field, [])
        status = "STAFF_REVIEW_REQUIRED" if any(q.get("status") == "ANSWERED" for q in field_questions) else "AWAITING_CUSTOMER" if any(q.get("status") == "ASKED" for q in field_questions) else "OPEN"
        if field not in seen and details["semantic_key"] not in v2_gap_keys:
            legacy_gaps.append({"id": action["action_id"], **details, "status": status, "version": 1})
            seen.add(field)
        if f"legacy-checklist:{action['action_id']}" not in reviewed:
            legacy_suggestions.append({"id": action["action_id"], "title": user_text(action.get("note") or "검토가 필요한 확인 항목"), "status": status})
    return {
        "case_id": data["case_id"], "context_revision": data["context_revision"],
        # Keep the old response fields for API compatibility. New clients use
        # context_facts and do not branch on PROPOSED/CONFIRMED.
        "context_facts": active_facts,
        "confirmed_facts": [],
        "proposed_facts": active_facts,
        "open_gaps": [g for g in data["gaps"] if g["status"] not in {"RESOLVED", "DISMISSED"}],
        "archived_gaps": [g for g in data["gaps"] if g["status"] in {"RESOLVED", "DISMISSED"}],
        "gap_history": [{**item, "before": item.get("before").model_dump(mode="json") if hasattr(item.get("before"), "model_dump") else item.get("before"), "after": item.get("after").model_dump(mode="json") if hasattr(item.get("after"), "model_dump") else item.get("after"), "created_at": item.get("created_at").isoformat() if hasattr(item.get("created_at"), "isoformat") else item.get("created_at")} for item in gap_history if item.get("operation") in {"EDIT", "SET_DISMISSED", "SET_RESOLVED"}],
        "ai_suggestions": [s for s in data["ai_suggestions"] if s["status"] == "PROPOSED"],
        "reviewed_suggestions": [s for s in data["ai_suggestions"] if s["status"] != "PROPOSED"],
        "active_tasks": [t for t in data["tasks"] if t["status"] not in {"COMPLETED", "CANCELLED"}],
        "archived_tasks": [t for t in data["tasks"] if t["status"] in {"COMPLETED", "CANCELLED"}],
        "recent_decisions": sorted(data["decisions"], key=lambda d: d["created_at"], reverse=True),
        "legacy_suggestions": legacy_suggestions,
        "legacy_gaps": legacy_gaps, "legacy_records": legacy_records,
        "legacy_archived_suggestions": legacy_archived,
    }
