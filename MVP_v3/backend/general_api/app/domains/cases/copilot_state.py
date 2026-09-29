"""One revision-consistent, bank-owned read model for chat and projections."""
from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .case_retrieval import merge_support_records
from .context_v3.panel import build_summary_projection
from contracts.working_facts import money_rollup


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


@dataclass
class OperationalState:
    revision: int
    case: dict
    resources: Any
    facts: list
    questions: list
    verifications: list
    actions: list
    tasks: list
    messages: list
    summary: str
    display_items: list

    def payload(self):
        return {"source_revision": self.revision, "summary": self.summary,
                "facts": self.facts, "tasks": self.tasks, "questions": self.questions,
                "verifications": self.verifications,
                "money_events": money_rollup(self.facts),
                "last_suggested_targets": next(((m.get('ai_metadata') or {}).get('recommended_actions', []) for m in reversed(self.messages) if m.get('actor_type') == 'BANK_AGENT' and m.get('visibility') == 'BANK_INTERNAL' and m.get('channel') == 'TEAM'), []),
                "display_overrides": [{"item_id": item.item_id, "section": item.section,
                    "text": item.effective_text, "is_display_only": True}
                    for item in self.display_items if not item.deleted_by and not item.permanently_hidden]}

    def guidance_key(self):
        # AI output, generated tasks and display-only changes cannot trigger themselves.
        return digest({"analysis": self.case.get("diagnosis"), "status": self.case.get("status"),
            "facts": self.facts,
            "questions": [q for q in self.questions if q.get("status") in {"ASKED", "ANSWERED"}],
            "verifications": self.verifications,
            "tasks": [t for t in self.tasks if t.get("source") != "AI_RECOMMENDED" or t.get("version", 1) > 1],
            "actions": [a for a in self.actions if a.get("action_type") != "STAFF_TASK"
                        and not a.get("action_type", "").startswith("AI_CHECKLIST:")]})


async def read_operational_state(repository, store, case_id: str, display_store=None) -> OperationalState:
    for _ in range(3):
        case = await repository.get(case_id)
        if case is None:
            raise KeyError(case_id)
        before = int(case.get("context_revision", 1))
        resources, questions, verifications, actions, messages = await asyncio.gather(
            store.list_resources(case_id), repository.list_customer_questions(case_id),
            repository.list_verifications(case_id), repository.list_actions(case_id), repository.list_messages(case_id))
        displays = await display_store.list_items(case_id, include_deleted=True) if display_store else []
        latest = await repository.get(case_id)
        if latest is None:
            raise KeyError(case_id)
        if before != int(latest.get("context_revision", 1)):
            continue
        facts, merged_actions = merge_support_records(resources, [], actions)
        tasks = [t.model_dump(mode="json") for t in resources.tasks]
        summary = build_summary_projection(latest, resources, verifications, actions, displays)["text"]
        return OperationalState(before, latest, resources, facts, questions, verifications, merged_actions,
                                tasks, messages, summary, displays)
    raise RuntimeError("CASE_CONTEXT_SOURCE_CHANGED")
