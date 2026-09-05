"""Read-only compatibility projection. Reading never migrates or approves data."""
from contracts.user_text import user_text
from .repository import normalize_target_field


def build_workspace(resources, facts, actions, questions):
    data = resources.model_dump(mode="json")
    reviewed = {s["dedupe_key"] for s in data["ai_suggestions"]}
    known = {normalize_target_field(f["field"]) for f in facts if f.get("status") == "CONFIRMED"}
    by_field = {}
    for question in questions:
        by_field.setdefault(normalize_target_field(question.get("target_field") or ""), []).append(question)
    legacy_suggestions, legacy_records, legacy_gaps, legacy_archived = [], [], [], []
    seen = set()
    for action in actions:
        kind = action.get("action_type", "")
        if kind == "STAFF_JUDGMENT":
            legacy_records.append({"id": action["action_id"], "title": user_text(action.get("note") or "기존 직원 기록"), "status": action.get("status"), "created_at": action.get("created_at")})
        if not kind.startswith("AI_CHECKLIST:"):
            continue
        if action.get("status") in {"COMPLETED", "CANCELLED"}:
            legacy_archived.append({"id": action["action_id"], "title": user_text(action.get("note") or "기존 확인 항목"), "status": action.get("status")})
            continue
        parts = kind.split(":")
        field = normalize_target_field(parts[-1])
        if field in known:
            continue
        field_questions = by_field.get(field, [])
        status = "STAFF_REVIEW_REQUIRED" if any(q.get("status") == "ANSWERED" for q in field_questions) else "AWAITING_CUSTOMER" if any(q.get("status") == "ASKED" for q in field_questions) else "OPEN"
        if field not in seen:
            legacy_gaps.append({"id": action["action_id"], "title": user_text(field), "status": status})
            seen.add(field)
        if f"legacy-checklist:{action['action_id']}" not in reviewed:
            legacy_suggestions.append({"id": action["action_id"], "title": user_text(action.get("note") or "검토가 필요한 확인 항목"), "status": status})
    legacy_facts = [{"id": f["fact_id"], "title": user_text(f["field"]), "value": user_text(str(f.get("value", ""))), "status": f.get("status"), "confirmed_at": f.get("confirmed_at")} for f in facts]
    return {
        "case_id": data["case_id"], "context_revision": data["context_revision"],
        "confirmed_facts": [f for f in data["facts"] if f["status"] == "CONFIRMED"],
        "proposed_facts": [f for f in data["facts"] if f["status"] == "PROPOSED"],
        "open_gaps": [g for g in data["gaps"] if g["status"] not in {"RESOLVED", "DISMISSED"}],
        "archived_gaps": [g for g in data["gaps"] if g["status"] in {"RESOLVED", "DISMISSED"}],
        "ai_suggestions": [s for s in data["ai_suggestions"] if s["status"] == "PROPOSED"],
        "reviewed_suggestions": [s for s in data["ai_suggestions"] if s["status"] != "PROPOSED"],
        "active_tasks": [t for t in data["tasks"] if t["status"] not in {"COMPLETED", "CANCELLED"}],
        "archived_tasks": [t for t in data["tasks"] if t["status"] in {"COMPLETED", "CANCELLED"}],
        "recent_decisions": sorted(data["decisions"], key=lambda d: d["created_at"], reverse=True),
        "legacy_facts": legacy_facts, "legacy_suggestions": legacy_suggestions,
        "legacy_gaps": legacy_gaps, "legacy_records": legacy_records,
        "legacy_archived_suggestions": legacy_archived,
    }
