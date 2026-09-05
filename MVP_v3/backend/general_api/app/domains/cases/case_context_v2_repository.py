"""Storage and state transitions for the approved Case Context v2 contract.

AI-created data remains a proposal. Only an authorised bank actor can confirm a
fact, accept a suggestion, complete a task, or append a decision record.
"""
from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import aiomysql

from contracts.public_api.case_context_v2 import (
    PublicAiSuggestionV2,
    PublicCaseContextResourcesV2,
    PublicCaseFactV2,
    PublicCaseGapV2,
    PublicCaseTaskV2,
    PublicDecisionRecordV2,
)


class ContextV2ConflictError(Exception):
    def __init__(self, current_version: int) -> None:
        self.current_version = current_version
        super().__init__(f"Context resource version conflict: {current_version}")


class ContextV2TransitionError(ValueError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return _iso(value if value.tzinfo else value.replace(tzinfo=timezone.utc))
    raise TypeError(f"Unsupported JSON value: {type(value)!r}")


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=_json_default)


def _json_load(value: Any, default: Any) -> Any:
    if value is None:
        return deepcopy(default)
    if isinstance(value, (dict, list)):
        return deepcopy(value)
    return json.loads(value)


def _aware(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _naive_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value


def _public_row(row: dict[str, Any], *internal_columns: str) -> dict[str, Any]:
    blocked = set(internal_columns)
    return {key: value for key, value in row.items() if key not in blocked}


def _fact(row: dict[str, Any]) -> PublicCaseFactV2:
    return PublicCaseFactV2.model_validate({
        **_public_row(row, "value_json", "evidence_refs_json", "client_request_id"),
        "value": _json_load(row.get("value_json"), {}),
        "evidence_refs": _json_load(row.get("evidence_refs_json"), []),
        "created_at": _aware(row.get("created_at")),
        "updated_at": _aware(row.get("updated_at")),
        "confirmed_at": _aware(row.get("confirmed_at")),
    })


def _gap(row: dict[str, Any]) -> PublicCaseGapV2:
    return PublicCaseGapV2.model_validate({
        **_public_row(
            row, "evidence_refs_json", "related_question_ids_json", "related_verification_ids_json",
            "client_request_id", "active_semantic_key",
        ),
        "evidence_refs": _json_load(row.get("evidence_refs_json"), []),
        "related_question_ids": _json_load(row.get("related_question_ids_json"), []),
        "related_verification_ids": _json_load(row.get("related_verification_ids_json"), []),
        "created_at": _aware(row.get("created_at")),
        "updated_at": _aware(row.get("updated_at")),
    })


def _suggestion(row: dict[str, Any]) -> PublicAiSuggestionV2:
    return PublicAiSuggestionV2.model_validate({
        **_public_row(row, "related_gap_ids_json", "evidence_refs_json", "active_dedupe_key"),
        "related_gap_ids": _json_load(row.get("related_gap_ids_json"), []),
        "evidence_refs": _json_load(row.get("evidence_refs_json"), []),
        "reviewed_at": _aware(row.get("reviewed_at")),
        "created_at": _aware(row.get("created_at")),
        "updated_at": _aware(row.get("updated_at")),
    })


def _task(row: dict[str, Any]) -> PublicCaseTaskV2:
    return PublicCaseTaskV2.model_validate({
        **_public_row(
            row, "related_gap_ids_json", "related_verification_ids_json", "evidence_refs_json",
            "client_request_id",
        ),
        "related_gap_ids": _json_load(row.get("related_gap_ids_json"), []),
        "related_verification_ids": _json_load(row.get("related_verification_ids_json"), []),
        "evidence_refs": _json_load(row.get("evidence_refs_json"), []),
        "due_at": _aware(row.get("due_at")),
        "completed_at": _aware(row.get("completed_at")),
        "created_at": _aware(row.get("created_at")),
        "updated_at": _aware(row.get("updated_at")),
    })


def _decision(row: dict[str, Any]) -> PublicDecisionRecordV2:
    return PublicDecisionRecordV2.model_validate({
        **_public_row(row, "client_request_id"), "created_at": _aware(row.get("created_at")),
    })


def _model_json(model: Any) -> str:
    return _json_dump(model.model_dump(mode="json"))


_SUGGESTION_TASK_TYPE = {
    "CUSTOMER_QUESTION": "CUSTOMER_CONTACT",
    "INSTITUTION_VERIFICATION": "INSTITUTION_VERIFICATION",
    "TRANSACTION_REVIEW": "TRANSACTION_REVIEW",
    "PROTECTIVE_ACTION": "PROTECTIVE_ACTION",
    "DOCUMENT_REQUEST": "DOCUMENT_REVIEW",
    "STAFF_REVIEW": "OTHER",
}


class InMemoryCaseContextV2Repository:
    """Transactional test implementation stored with the owning Case repository."""

    def __init__(self, cases: Any) -> None:
        self.cases = cases
        for name in ("_context_v2_facts", "_context_v2_gaps", "_context_v2_suggestions", "_context_v2_tasks", "_context_v2_decisions", "_context_v2_requests", "_context_v2_history"):
            if not hasattr(cases, name):
                setattr(cases, name, {}) if name != "_context_v2_history" else setattr(cases, name, [])

    async def _case(self, case_id: str) -> dict[str, Any]:
        case = await self.cases.get(case_id)
        if case is None:
            raise KeyError(case_id)
        return case

    def _touch(self, case_id: str, now: datetime) -> None:
        if hasattr(self.cases, "_touch_case"):
            self.cases._touch_case(case_id, _iso(now))

    def _history(self, case_id: str, entity_type: str, entity_id: str, version: int, operation: str, actor: str, before: Any, after: Any) -> None:
        self.cases._context_v2_history.append({
            "case_id": case_id, "entity_type": entity_type, "entity_id": entity_id,
            "entity_version": version, "operation": operation, "actor_user_id": actor,
            "before": deepcopy(before), "after": deepcopy(after),
        })

    async def list_resources(self, case_id: str) -> PublicCaseContextResourcesV2:
        case = await self._case(case_id)
        return PublicCaseContextResourcesV2(
            case_id=case_id, context_revision=max(1, int(case.get("context_revision", 1))),
            facts=[deepcopy(v) for (cid, _), v in self.cases._context_v2_facts.items() if cid == case_id],
            gaps=[deepcopy(v) for (cid, _), v in self.cases._context_v2_gaps.items() if cid == case_id],
            ai_suggestions=[deepcopy(v) for (cid, _), v in self.cases._context_v2_suggestions.items() if cid == case_id],
            tasks=[deepcopy(v) for (cid, _), v in self.cases._context_v2_tasks.items() if cid == case_id],
            decisions=[deepcopy(v) for (cid, _), v in self.cases._context_v2_decisions.items() if cid == case_id],
        )

    async def create_fact(self, case_id: str, data: dict[str, Any], actor: str, *, source_kind: str = "STAFF_OBSERVATION") -> PublicCaseFactV2:
        await self._case(case_id)
        async with self.cases._lock:
            existing_id = self.cases._context_v2_requests.get((case_id, "FACT", data.get("client_request_id")))
            existing = self.cases._context_v2_facts.get((case_id, existing_id)) if existing_id else None
            if existing:
                return deepcopy(existing)
            now = _now()
            item = PublicCaseFactV2(
                fact_id=f"fact-{uuid4().hex}", case_id=case_id, semantic_key=data["semantic_key"],
                display_label=data["display_label"], value=data["value"], display_value=data["display_value"],
                source_kind=source_kind, status="PROPOSED", evidence_refs=data.get("evidence_refs", []),
                visibility=data.get("visibility", "BANK_INTERNAL"), version=1, created_at=now, updated_at=now,
            )
            self.cases._context_v2_facts[(case_id, item.fact_id)] = item
            self.cases._context_v2_requests[(case_id, "FACT", data.get("client_request_id"))] = item.fact_id
            self._history(case_id, "FACT", item.fact_id, 1, "CREATE_PROPOSAL", actor, None, item)
            self._touch(case_id, now)
            return deepcopy(item)

    async def review_fact(self, case_id: str, fact_id: str, expected_version: int, decision: str, reason: str, actor: str) -> PublicCaseFactV2:
        async with self.cases._lock:
            before = self.cases._context_v2_facts.get((case_id, fact_id))
            if before is None:
                raise KeyError(fact_id)
            if before.version != expected_version:
                raise ContextV2ConflictError(before.version)
            if before.status != "PROPOSED":
                raise ContextV2TransitionError("검토 대기 중인 사실만 확정하거나 제외할 수 있습니다.")
            now = _now()
            update = {"version": before.version + 1, "updated_at": now}
            if decision == "CONFIRM":
                update.update(status="CONFIRMED", confirmed_by=actor, confirmed_at=now)
            else:
                update.update(status="REJECTED", rejection_reason=reason)
            after = before.model_copy(update=update)
            self.cases._context_v2_facts[(case_id, fact_id)] = after
            self._history(case_id, "FACT", fact_id, after.version, decision, actor, before, after)
            self._touch(case_id, now)
            return deepcopy(after)

    async def create_gap(self, case_id: str, data: dict[str, Any], actor: str, *, source: str = "BANK_STAFF") -> PublicCaseGapV2:
        case = await self._case(case_id)
        async with self.cases._lock:
            existing_id = self.cases._context_v2_requests.get((case_id, "GAP", data.get("client_request_id")))
            existing = self.cases._context_v2_gaps.get((case_id, existing_id)) if existing_id else None
            if existing:
                return deepcopy(existing)
            if any(v.semantic_key == data["semantic_key"] and v.status in {"OPEN", "AWAITING_CUSTOMER", "AWAITING_INSTITUTION", "STAFF_REVIEW_REQUIRED"} for (cid, _), v in self.cases._context_v2_gaps.items() if cid == case_id):
                raise ContextV2TransitionError("동일한 확인 항목이 이미 열려 있습니다.")
            now = _now()
            item = PublicCaseGapV2(
                gap_id=f"gap-{uuid4().hex}", case_id=case_id, semantic_key=data["semantic_key"],
                title=data["title"], reason=data["reason"], priority=data["priority"], status="OPEN",
                source=source, evidence_refs=data.get("evidence_refs", []), source_revision=max(1, int(case.get("context_revision", 1))),
                version=1, created_at=now, updated_at=now,
            )
            self.cases._context_v2_gaps[(case_id, item.gap_id)] = item
            self.cases._context_v2_requests[(case_id, "GAP", data.get("client_request_id"))] = item.gap_id
            self._history(case_id, "GAP", item.gap_id, 1, "CREATE", actor, None, item)
            self._touch(case_id, now)
            return deepcopy(item)

    async def update_gap(self, case_id: str, gap_id: str, expected_version: int, status: str, reason: str | None, resolution_fact_id: str | None, actor: str) -> PublicCaseGapV2:
        async with self.cases._lock:
            before = self.cases._context_v2_gaps.get((case_id, gap_id))
            if before is None:
                raise KeyError(gap_id)
            if before.version != expected_version:
                raise ContextV2ConflictError(before.version)
            if before.status in {"RESOLVED", "DISMISSED"}:
                raise ContextV2TransitionError("종료된 확인 항목은 다시 변경할 수 없습니다.")
            if status == "RESOLVED":
                fact = self.cases._context_v2_facts.get((case_id, resolution_fact_id))
                if fact is None or fact.status != "CONFIRMED" or fact.semantic_key != before.semantic_key:
                    raise ContextV2TransitionError("확정된 사실을 연결해야 확인 항목을 완료할 수 있습니다.")
            now = _now()
            after = before.model_copy(update={
                "status": status, "resolution_fact_id": resolution_fact_id if status == "RESOLVED" else None,
                "dismissal_reason": reason if status == "DISMISSED" else None,
                "version": before.version + 1, "updated_at": now,
            })
            self.cases._context_v2_gaps[(case_id, gap_id)] = after
            self._history(case_id, "GAP", gap_id, after.version, f"SET_{status}", actor, before, after)
            self._touch(case_id, now)
            return deepcopy(after)

    async def propose_suggestion(self, case_id: str, data: dict[str, Any], actor: str = "system:context-ai") -> PublicAiSuggestionV2:
        case = await self._case(case_id)
        async with self.cases._lock:
            existing = next((v for (cid, _), v in self.cases._context_v2_suggestions.items() if cid == case_id and (v.status == "PROPOSED" or data["dedupe_key"].startswith("legacy-checklist:")) and v.dedupe_key == data["dedupe_key"]), None)
            if existing:
                return deepcopy(existing)
            now = _now()
            item = PublicAiSuggestionV2(
                suggestion_id=f"suggestion-{uuid4().hex}", case_id=case_id,
                suggestion_type=data["suggestion_type"], title=data["title"], rationale=data["rationale"],
                priority=data["priority"], status="PROPOSED", related_gap_ids=data.get("related_gap_ids", []),
                evidence_refs=data.get("evidence_refs", []), dedupe_key=data["dedupe_key"],
                execution_mode=data.get("execution_mode", "HUMAN_REVIEW_REQUIRED"),
                source_revision=max(1, int(data.get("source_revision") or case.get("context_revision", 1))),
                model_version=data.get("model_version"), prompt_version=data.get("prompt_version"),
                version=1, created_at=now, updated_at=now,
            )
            self.cases._context_v2_suggestions[(case_id, item.suggestion_id)] = item
            self._history(case_id, "SUGGESTION", item.suggestion_id, 1, "AI_PROPOSE", actor, None, item)
            self._touch(case_id, now)
            return deepcopy(item)

    async def review_suggestion(self, case_id: str, suggestion_id: str, data: dict[str, Any], actor: str) -> tuple[PublicAiSuggestionV2, PublicCaseTaskV2 | None]:
        async with self.cases._lock:
            before = self.cases._context_v2_suggestions.get((case_id, suggestion_id))
            if before is None:
                raise KeyError(suggestion_id)
            if before.version != data["expected_version"]:
                raise ContextV2ConflictError(before.version)
            if before.status != "PROPOSED":
                raise ContextV2TransitionError("검토 대기 중인 AI 제안만 처리할 수 있습니다.")
            now, task = _now(), None
            if data["decision"] == "ACCEPT":
                task = PublicCaseTaskV2(
                    task_id=f"task-{uuid4().hex}", case_id=case_id, source="AI_SUGGESTION_ACCEPTED",
                    source_suggestion_id=suggestion_id, task_type=_SUGGESTION_TASK_TYPE[before.suggestion_type],
                    title=data.get("edited_title") or before.title,
                    description=data.get("edited_description") or before.rationale,
                    priority=before.priority, status="TODO", related_gap_ids=before.related_gap_ids,
                    version=1, created_by=actor, created_at=now, updated_at=now,
                )
                self.cases._context_v2_tasks[(case_id, task.task_id)] = task
                after = before.model_copy(update={"status": "ACCEPTED", "accepted_task_id": task.task_id, "reviewed_by": actor, "reviewed_at": now, "version": before.version + 1, "updated_at": now})
                self._history(case_id, "TASK", task.task_id, 1, "CREATE_FROM_SUGGESTION", actor, None, task)
            else:
                after = before.model_copy(update={"status": "DISMISSED", "dismissal_reason": data["reason"], "reviewed_by": actor, "reviewed_at": now, "version": before.version + 1, "updated_at": now})
            self.cases._context_v2_suggestions[(case_id, suggestion_id)] = after
            self._history(case_id, "SUGGESTION", suggestion_id, after.version, data["decision"], actor, before, after)
            self._touch(case_id, now)
            return deepcopy(after), deepcopy(task)

    async def create_task(self, case_id: str, data: dict[str, Any], actor: str) -> PublicCaseTaskV2:
        await self._case(case_id)
        async with self.cases._lock:
            existing_id = self.cases._context_v2_requests.get((case_id, "TASK", data.get("client_request_id")))
            existing = self.cases._context_v2_tasks.get((case_id, existing_id)) if existing_id else None
            if existing:
                return deepcopy(existing)
            now = _now()
            item = PublicCaseTaskV2(
                task_id=f"task-{uuid4().hex}", case_id=case_id, source="STAFF_CREATED",
                task_type=data["task_type"], title=data["title"], description=data["description"],
                priority=data["priority"], status="TODO", assignee_user_id=data.get("assignee_user_id"),
                due_at=data.get("due_at"), related_gap_ids=data.get("related_gap_ids", []),
                version=1, created_by=actor, created_at=now, updated_at=now,
            )
            self.cases._context_v2_tasks[(case_id, item.task_id)] = item
            self.cases._context_v2_requests[(case_id, "TASK", data.get("client_request_id"))] = item.task_id
            self._history(case_id, "TASK", item.task_id, 1, "CREATE", actor, None, item)
            self._touch(case_id, now)
            return deepcopy(item)

    async def update_task(self, case_id: str, task_id: str, data: dict[str, Any], actor: str) -> PublicCaseTaskV2:
        async with self.cases._lock:
            before = self.cases._context_v2_tasks.get((case_id, task_id))
            if before is None:
                raise KeyError(task_id)
            if before.version != data["expected_version"]:
                raise ContextV2ConflictError(before.version)
            reopening = before.status in {"COMPLETED", "CANCELLED"} and data.get("status") == "TODO"
            if before.status in {"COMPLETED", "CANCELLED"} and not reopening:
                raise ContextV2TransitionError("종료된 업무는 수정할 수 없습니다.")
            changes = {key: value for key, value in data.items() if key != "expected_version" and value is not None}
            if reopening:
                changes.update(completed_by=None, completed_at=None, cancellation_reason=None, result_summary=None, result_code=None)
            now = _now()
            changes.update(version=before.version + 1, updated_at=now)
            after = before.model_copy(update=changes)
            self.cases._context_v2_tasks[(case_id, task_id)] = after
            self._history(case_id, "TASK", task_id, after.version, "UPDATE", actor, before, after)
            self._touch(case_id, now)
            return deepcopy(after)

    async def complete_task(self, case_id: str, task_id: str, data: dict[str, Any], actor: str) -> PublicCaseTaskV2:
        return await self._finish_task(case_id, task_id, data, actor, "COMPLETED")

    async def cancel_task(self, case_id: str, task_id: str, data: dict[str, Any], actor: str) -> PublicCaseTaskV2:
        return await self._finish_task(case_id, task_id, data, actor, "CANCELLED")

    async def _finish_task(self, case_id: str, task_id: str, data: dict[str, Any], actor: str, status: str) -> PublicCaseTaskV2:
        async with self.cases._lock:
            before = self.cases._context_v2_tasks.get((case_id, task_id))
            if before is None:
                raise KeyError(task_id)
            if before.version != data["expected_version"]:
                raise ContextV2ConflictError(before.version)
            if before.status in {"COMPLETED", "CANCELLED"}:
                raise ContextV2TransitionError("이미 종료된 업무입니다.")
            now = _now()
            changes = {"status": status, "version": before.version + 1, "updated_at": now}
            if status == "COMPLETED":
                changes.update(result_code=data.get("result_code"), result_summary=data["result_summary"], evidence_refs=data.get("evidence_refs", []), completed_by=actor, completed_at=now)
            else:
                changes["cancellation_reason"] = data["reason"]
            after = before.model_copy(update=changes)
            self.cases._context_v2_tasks[(case_id, task_id)] = after
            self._history(case_id, "TASK", task_id, after.version, status, actor, before, after)
            self._touch(case_id, now)
            return deepcopy(after)

    async def create_decision(self, case_id: str, data: dict[str, Any], actor: str) -> PublicDecisionRecordV2:
        await self._case(case_id)
        async with self.cases._lock:
            existing_id = self.cases._context_v2_requests.get((case_id, "DECISION", data.get("client_request_id")))
            existing = self.cases._context_v2_decisions.get((case_id, existing_id)) if existing_id else None
            if existing:
                return deepcopy(existing)
            now = _now()
            item = PublicDecisionRecordV2(
                decision_id=f"decision-{uuid4().hex}", case_id=case_id,
                decision_type=data["decision_type"], title=data["title"], rationale=data["rationale"],
                related_entity_type=data["related_entity_type"], related_entity_id=data["related_entity_id"],
                visibility=data.get("visibility", "BANK_INTERNAL"), actor_user_id=actor,
                supersedes_decision_id=data.get("supersedes_decision_id"), created_at=now,
            )
            self.cases._context_v2_decisions[(case_id, item.decision_id)] = item
            self.cases._context_v2_requests[(case_id, "DECISION", data.get("client_request_id"))] = item.decision_id
            self._history(case_id, "DECISION", item.decision_id, 1, "APPEND", actor, None, item)
            self._touch(case_id, now)
            return deepcopy(item)


class MySqlCaseContextV2Repository:
    """MySQL implementation sharing the current Case repository connection pool."""

    def __init__(self, cases: Any) -> None:
        self.cases = cases

    async def _one(self, cursor: Any, table: str, id_column: str, case_id: str, entity_id: str, *, lock: bool = False) -> dict[str, Any] | None:
        suffix = " FOR UPDATE" if lock else ""
        await cursor.execute(f"SELECT * FROM {table} WHERE case_id=%s AND {id_column}=%s{suffix}", (case_id, entity_id))
        return await cursor.fetchone()

    @staticmethod
    async def _case_revision(cursor: Any, case_id: str, *, lock: bool = False) -> int:
        await cursor.execute(f"SELECT context_revision FROM cases WHERE case_id=%s{' FOR UPDATE' if lock else ''}", (case_id,))
        row = await cursor.fetchone()
        if not row:
            raise KeyError(case_id)
        return max(1, int(row["context_revision"]))

    @staticmethod
    async def _history(cursor: Any, case_id: str, entity_type: str, entity_id: str, version: int, operation: str, actor: str, before: Any, after: Any) -> None:
        await cursor.execute(
            """INSERT INTO case_context_v2_history
               (case_id,entity_type,entity_id,entity_version,operation,actor_user_id,before_json,after_json)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (case_id, entity_type, entity_id, version, operation, actor,
             _model_json(before) if before else None, _model_json(after)),
        )

    async def list_resources(self, case_id: str) -> PublicCaseContextResourcesV2:
        pool = await self.cases._get_pool()
        async with pool.acquire() as connection, connection.cursor(aiomysql.DictCursor) as cursor:
            revision = await self._case_revision(cursor, case_id)
            await cursor.execute("SELECT * FROM case_context_facts_v2 WHERE case_id=%s ORDER BY created_at,fact_id", (case_id,))
            facts = [_fact(row) for row in await cursor.fetchall()]
            await cursor.execute("SELECT * FROM case_gaps WHERE case_id=%s ORDER BY created_at,gap_id", (case_id,))
            gaps = [_gap(row) for row in await cursor.fetchall()]
            await cursor.execute("SELECT * FROM case_ai_suggestions WHERE case_id=%s ORDER BY created_at,suggestion_id", (case_id,))
            suggestions = [_suggestion(row) for row in await cursor.fetchall()]
            await cursor.execute("SELECT * FROM case_tasks WHERE case_id=%s ORDER BY created_at,task_id", (case_id,))
            tasks = [_task(row) for row in await cursor.fetchall()]
            await cursor.execute("SELECT * FROM case_decisions WHERE case_id=%s ORDER BY created_at,decision_id", (case_id,))
            decisions = [_decision(row) for row in await cursor.fetchall()]
            await connection.rollback()  # Release the read snapshot before returning to the pool.
        return PublicCaseContextResourcesV2(case_id=case_id, context_revision=revision, facts=facts, gaps=gaps, ai_suggestions=suggestions, tasks=tasks, decisions=decisions)

    async def create_fact(self, case_id: str, data: dict[str, Any], actor: str, *, source_kind: str = "STAFF_OBSERVATION") -> PublicCaseFactV2:
        pool = await self.cases._get_pool()
        async with pool.acquire() as connection:
            try:
                await connection.begin()
                async with connection.cursor(aiomysql.DictCursor) as cursor:
                    await self._case_revision(cursor, case_id, lock=True)
                    await cursor.execute("SELECT * FROM case_context_facts_v2 WHERE case_id=%s AND client_request_id=%s", (case_id, data["client_request_id"]))
                    row = await cursor.fetchone()
                    if row:
                        await connection.rollback()
                        return _fact(row)
                    now, fact_id = _now(), f"fact-{uuid4().hex}"
                    await cursor.execute(
                        """INSERT INTO case_context_facts_v2
                        (fact_id,case_id,semantic_key,display_label,value_json,display_value,source_kind,status,
                         evidence_refs_json,visibility,client_request_id,version,created_at,updated_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,'PROPOSED',%s,%s,%s,1,%s,%s)""",
                        (fact_id, case_id, data["semantic_key"], data["display_label"], _json_dump(data["value"]),
                         data["display_value"], source_kind, _json_dump(data.get("evidence_refs", [])),
                         data.get("visibility", "BANK_INTERNAL"), data["client_request_id"], _naive_utc(now), _naive_utc(now)),
                    )
                    row = await self._one(cursor, "case_context_facts_v2", "fact_id", case_id, fact_id)
                    item = _fact(row)
                    await self._history(cursor, case_id, "FACT", fact_id, 1, "CREATE_PROPOSAL", actor, None, item)
                await connection.commit()
                return item
            except BaseException:
                await connection.rollback()
                raise

    async def review_fact(self, case_id: str, fact_id: str, expected_version: int, decision: str, reason: str, actor: str) -> PublicCaseFactV2:
        pool = await self.cases._get_pool()
        async with pool.acquire() as connection:
            try:
                await connection.begin()
                async with connection.cursor(aiomysql.DictCursor) as cursor:
                    row = await self._one(cursor, "case_context_facts_v2", "fact_id", case_id, fact_id, lock=True)
                    if not row:
                        raise KeyError(fact_id)
                    before = _fact(row)
                    if before.version != expected_version:
                        raise ContextV2ConflictError(before.version)
                    if before.status != "PROPOSED":
                        raise ContextV2TransitionError("검토 대기 중인 사실만 확정하거나 제외할 수 있습니다.")
                    now = _now()
                    if decision == "CONFIRM":
                        await cursor.execute("UPDATE case_context_facts_v2 SET status='CONFIRMED',confirmed_by=%s,confirmed_at=%s,version=version+1,updated_at=%s WHERE fact_id=%s", (actor, _naive_utc(now), _naive_utc(now), fact_id))
                    else:
                        await cursor.execute("UPDATE case_context_facts_v2 SET status='REJECTED',rejection_reason=%s,version=version+1,updated_at=%s WHERE fact_id=%s", (reason, _naive_utc(now), fact_id))
                    after = _fact(await self._one(cursor, "case_context_facts_v2", "fact_id", case_id, fact_id))
                    await self._history(cursor, case_id, "FACT", fact_id, after.version, decision, actor, before, after)
                await connection.commit()
                return after
            except BaseException:
                await connection.rollback()
                raise

    async def create_gap(self, case_id: str, data: dict[str, Any], actor: str, *, source: str = "BANK_STAFF") -> PublicCaseGapV2:
        pool = await self.cases._get_pool()
        async with pool.acquire() as connection:
            try:
                await connection.begin()
                async with connection.cursor(aiomysql.DictCursor) as cursor:
                    revision = await self._case_revision(cursor, case_id, lock=True)
                    await cursor.execute("SELECT * FROM case_gaps WHERE case_id=%s AND client_request_id=%s", (case_id, data["client_request_id"]))
                    row = await cursor.fetchone()
                    if row:
                        await connection.rollback()
                        return _gap(row)
                    now, gap_id = _now(), f"gap-{uuid4().hex}"
                    await cursor.execute(
                        """INSERT INTO case_gaps
                        (gap_id,case_id,semantic_key,title,reason,priority,status,source,evidence_refs_json,
                         related_question_ids_json,related_verification_ids_json,visibility,source_revision,
                         client_request_id,version,created_at,updated_at)
                        VALUES (%s,%s,%s,%s,%s,%s,'OPEN',%s,%s,'[]','[]','BANK_INTERNAL',%s,%s,1,%s,%s)""",
                        (gap_id, case_id, data["semantic_key"], data["title"], data["reason"], data["priority"],
                         source, _json_dump(data.get("evidence_refs", [])), revision, data["client_request_id"], _naive_utc(now), _naive_utc(now)),
                    )
                    item = _gap(await self._one(cursor, "case_gaps", "gap_id", case_id, gap_id))
                    await self._history(cursor, case_id, "GAP", gap_id, 1, "CREATE", actor, None, item)
                await connection.commit()
                return item
            except BaseException:
                await connection.rollback()
                raise

    async def update_gap(self, case_id: str, gap_id: str, expected_version: int, status: str, reason: str | None, resolution_fact_id: str | None, actor: str) -> PublicCaseGapV2:
        pool = await self.cases._get_pool()
        async with pool.acquire() as connection:
            try:
                await connection.begin()
                async with connection.cursor(aiomysql.DictCursor) as cursor:
                    row = await self._one(cursor, "case_gaps", "gap_id", case_id, gap_id, lock=True)
                    if not row:
                        raise KeyError(gap_id)
                    before = _gap(row)
                    if before.version != expected_version:
                        raise ContextV2ConflictError(before.version)
                    if before.status in {"RESOLVED", "DISMISSED"}:
                        raise ContextV2TransitionError("종료된 확인 항목은 다시 변경할 수 없습니다.")
                    if status == "RESOLVED":
                        fact_row = await self._one(cursor, "case_context_facts_v2", "fact_id", case_id, resolution_fact_id or "", lock=True)
                    if not fact_row or fact_row["status"] != "CONFIRMED" or fact_row["semantic_key"] != before.semantic_key:
                            raise ContextV2TransitionError("확정된 사실을 연결해야 확인 항목을 완료할 수 있습니다.")
                    now = _now()
                    await cursor.execute(
                        "UPDATE case_gaps SET status=%s,resolution_fact_id=%s,dismissal_reason=%s,version=version+1,updated_at=%s WHERE gap_id=%s",
                        (status, resolution_fact_id if status == "RESOLVED" else None, reason if status == "DISMISSED" else None, _naive_utc(now), gap_id),
                    )
                    after = _gap(await self._one(cursor, "case_gaps", "gap_id", case_id, gap_id))
                    await self._history(cursor, case_id, "GAP", gap_id, after.version, f"SET_{status}", actor, before, after)
                await connection.commit()
                return after
            except BaseException:
                await connection.rollback()
                raise

    async def propose_suggestion(self, case_id: str, data: dict[str, Any], actor: str = "system:context-ai") -> PublicAiSuggestionV2:
        pool = await self.cases._get_pool()
        async with pool.acquire() as connection:
            try:
                await connection.begin()
                async with connection.cursor(aiomysql.DictCursor) as cursor:
                    revision = await self._case_revision(cursor, case_id, lock=True)
                    dedupe_column = "dedupe_key" if data["dedupe_key"].startswith("legacy-checklist:") else "active_dedupe_key"
                    await cursor.execute(f"SELECT * FROM case_ai_suggestions WHERE case_id=%s AND {dedupe_column}=%s", (case_id, data["dedupe_key"]))
                    row = await cursor.fetchone()
                    if row:
                        await connection.rollback()
                        return _suggestion(row)
                    now, suggestion_id = _now(), f"suggestion-{uuid4().hex}"
                    await cursor.execute(
                        """INSERT INTO case_ai_suggestions
                        (suggestion_id,case_id,suggestion_type,title,rationale,priority,status,related_gap_ids_json,
                         evidence_refs_json,dedupe_key,execution_mode,source_revision,model_version,prompt_version,
                         version,created_at,updated_at)
                        VALUES (%s,%s,%s,%s,%s,%s,'PROPOSED',%s,%s,%s,%s,%s,%s,%s,1,%s,%s)""",
                        (suggestion_id, case_id, data["suggestion_type"], data["title"], data["rationale"], data["priority"],
                         _json_dump(data.get("related_gap_ids", [])), _json_dump(data.get("evidence_refs", [])), data["dedupe_key"],
                         data.get("execution_mode", "HUMAN_REVIEW_REQUIRED"), data.get("source_revision") or revision,
                         data.get("model_version"), data.get("prompt_version"), _naive_utc(now), _naive_utc(now)),
                    )
                    item = _suggestion(await self._one(cursor, "case_ai_suggestions", "suggestion_id", case_id, suggestion_id))
                    await self._history(cursor, case_id, "SUGGESTION", suggestion_id, 1, "AI_PROPOSE", actor, None, item)
                await connection.commit()
                return item
            except BaseException:
                await connection.rollback()
                raise

    async def review_suggestion(self, case_id: str, suggestion_id: str, data: dict[str, Any], actor: str) -> tuple[PublicAiSuggestionV2, PublicCaseTaskV2 | None]:
        pool = await self.cases._get_pool()
        async with pool.acquire() as connection:
            try:
                await connection.begin()
                async with connection.cursor(aiomysql.DictCursor) as cursor:
                    row = await self._one(cursor, "case_ai_suggestions", "suggestion_id", case_id, suggestion_id, lock=True)
                    if not row:
                        raise KeyError(suggestion_id)
                    before = _suggestion(row)
                    if before.version != data["expected_version"]:
                        raise ContextV2ConflictError(before.version)
                    if before.status != "PROPOSED":
                        raise ContextV2TransitionError("검토 대기 중인 AI 제안만 처리할 수 있습니다.")
                    now, task = _now(), None
                    if data["decision"] == "ACCEPT":
                        task_id = f"task-{uuid4().hex}"
                        await cursor.execute(
                            """INSERT INTO case_tasks
                            (task_id,case_id,source,source_suggestion_id,task_type,title,description,priority,status,
                             related_gap_ids_json,related_verification_ids_json,evidence_refs_json,customer_visibility,
                             version,created_by,created_at,updated_at)
                            VALUES (%s,%s,'AI_SUGGESTION_ACCEPTED',%s,%s,%s,%s,%s,'TODO',%s,'[]',%s,
                                    'INTERNAL_ONLY',1,%s,%s,%s)""",
                            (task_id, case_id, suggestion_id, _SUGGESTION_TASK_TYPE[before.suggestion_type],
                             data.get("edited_title") or before.title, data.get("edited_description") or before.rationale,
                             before.priority, _json_dump(before.related_gap_ids), _json_dump(before.evidence_refs),
                             actor, _naive_utc(now), _naive_utc(now)),
                        )
                        await cursor.execute("UPDATE case_ai_suggestions SET status='ACCEPTED',accepted_task_id=%s,reviewed_by=%s,reviewed_at=%s,version=version+1,updated_at=%s WHERE suggestion_id=%s", (task_id, actor, _naive_utc(now), _naive_utc(now), suggestion_id))
                        task = _task(await self._one(cursor, "case_tasks", "task_id", case_id, task_id))
                        await self._history(cursor, case_id, "TASK", task_id, 1, "CREATE_FROM_SUGGESTION", actor, None, task)
                    else:
                        await cursor.execute("UPDATE case_ai_suggestions SET status='DISMISSED',dismissal_reason=%s,reviewed_by=%s,reviewed_at=%s,version=version+1,updated_at=%s WHERE suggestion_id=%s", (data["reason"], actor, _naive_utc(now), _naive_utc(now), suggestion_id))
                    after = _suggestion(await self._one(cursor, "case_ai_suggestions", "suggestion_id", case_id, suggestion_id))
                    await self._history(cursor, case_id, "SUGGESTION", suggestion_id, after.version, data["decision"], actor, before, after)
                await connection.commit()
                return after, task
            except BaseException:
                await connection.rollback()
                raise

    async def create_task(self, case_id: str, data: dict[str, Any], actor: str) -> PublicCaseTaskV2:
        pool = await self.cases._get_pool()
        async with pool.acquire() as connection:
            try:
                await connection.begin()
                async with connection.cursor(aiomysql.DictCursor) as cursor:
                    await self._case_revision(cursor, case_id, lock=True)
                    await cursor.execute("SELECT * FROM case_tasks WHERE case_id=%s AND client_request_id=%s", (case_id, data["client_request_id"]))
                    row = await cursor.fetchone()
                    if row:
                        await connection.rollback()
                        return _task(row)
                    now, task_id = _now(), f"task-{uuid4().hex}"
                    await cursor.execute(
                        """INSERT INTO case_tasks
                        (task_id,case_id,source,task_type,title,description,priority,status,assignee_user_id,due_at,
                         related_gap_ids_json,related_verification_ids_json,evidence_refs_json,customer_visibility,
                         client_request_id,version,created_by,created_at,updated_at)
                        VALUES (%s,%s,'STAFF_CREATED',%s,%s,%s,%s,'TODO',%s,%s,%s,'[]','[]','INTERNAL_ONLY',%s,1,%s,%s,%s)""",
                        (task_id, case_id, data["task_type"], data["title"], data["description"], data["priority"],
                         data.get("assignee_user_id"), _naive_utc(data.get("due_at")), _json_dump(data.get("related_gap_ids", [])),
                         data["client_request_id"], actor, _naive_utc(now), _naive_utc(now)),
                    )
                    item = _task(await self._one(cursor, "case_tasks", "task_id", case_id, task_id))
                    await self._history(cursor, case_id, "TASK", task_id, 1, "CREATE", actor, None, item)
                await connection.commit()
                return item
            except BaseException:
                await connection.rollback()
                raise

    async def update_task(self, case_id: str, task_id: str, data: dict[str, Any], actor: str) -> PublicCaseTaskV2:
        return await self._mutate_task(case_id, task_id, data, actor, "UPDATE")

    async def complete_task(self, case_id: str, task_id: str, data: dict[str, Any], actor: str) -> PublicCaseTaskV2:
        return await self._mutate_task(case_id, task_id, data, actor, "COMPLETED")

    async def cancel_task(self, case_id: str, task_id: str, data: dict[str, Any], actor: str) -> PublicCaseTaskV2:
        return await self._mutate_task(case_id, task_id, data, actor, "CANCELLED")

    async def _mutate_task(self, case_id: str, task_id: str, data: dict[str, Any], actor: str, operation: str) -> PublicCaseTaskV2:
        pool = await self.cases._get_pool()
        async with pool.acquire() as connection:
            try:
                await connection.begin()
                async with connection.cursor(aiomysql.DictCursor) as cursor:
                    row = await self._one(cursor, "case_tasks", "task_id", case_id, task_id, lock=True)
                    if not row:
                        raise KeyError(task_id)
                    before = _task(row)
                    if before.version != data["expected_version"]:
                        raise ContextV2ConflictError(before.version)
                    reopening = operation == "UPDATE" and data.get("status") == "TODO" and before.status in {"COMPLETED", "CANCELLED"}
                    if before.status in {"COMPLETED", "CANCELLED"} and not reopening:
                        raise ContextV2TransitionError("종료된 업무는 변경할 수 없습니다.")
                    now = _now()
                    if operation == "UPDATE":
                        changes = {key: value for key, value in data.items() if key != "expected_version" and value is not None}
                        allowed = {"status", "title", "description", "priority", "assignee_user_id", "due_at"}
                        changes = {key: value for key, value in changes.items() if key in allowed}
                        assignments, values = [], []
                        if reopening:
                            assignments.extend(["completed_by=NULL", "completed_at=NULL", "cancellation_reason=NULL", "result_summary=NULL", "result_code=NULL"])
                        for key, value in changes.items():
                            assignments.append(f"{key}=%s")
                            values.append(_naive_utc(value) if key == "due_at" else value)
                        assignments.extend(["version=version+1", "updated_at=%s"])
                        values.extend([_naive_utc(now), task_id])
                        await cursor.execute(f"UPDATE case_tasks SET {','.join(assignments)} WHERE task_id=%s", tuple(values))
                    elif operation == "COMPLETED":
                        await cursor.execute("UPDATE case_tasks SET status='COMPLETED',result_code=%s,result_summary=%s,evidence_refs_json=%s,completed_by=%s,completed_at=%s,version=version+1,updated_at=%s WHERE task_id=%s", (data.get("result_code"), data["result_summary"], _json_dump(data.get("evidence_refs", [])), actor, _naive_utc(now), _naive_utc(now), task_id))
                    else:
                        await cursor.execute("UPDATE case_tasks SET status='CANCELLED',cancellation_reason=%s,version=version+1,updated_at=%s WHERE task_id=%s", (data["reason"], _naive_utc(now), task_id))
                    after = _task(await self._one(cursor, "case_tasks", "task_id", case_id, task_id))
                    await self._history(cursor, case_id, "TASK", task_id, after.version, operation, actor, before, after)
                await connection.commit()
                return after
            except BaseException:
                await connection.rollback()
                raise

    async def create_decision(self, case_id: str, data: dict[str, Any], actor: str) -> PublicDecisionRecordV2:
        pool = await self.cases._get_pool()
        async with pool.acquire() as connection:
            try:
                await connection.begin()
                async with connection.cursor(aiomysql.DictCursor) as cursor:
                    await self._case_revision(cursor, case_id, lock=True)
                    await cursor.execute("SELECT * FROM case_decisions WHERE case_id=%s AND client_request_id=%s", (case_id, data["client_request_id"]))
                    row = await cursor.fetchone()
                    if row:
                        await connection.rollback()
                        return _decision(row)
                    now, decision_id = _now(), f"decision-{uuid4().hex}"
                    await cursor.execute(
                        """INSERT INTO case_decisions
                        (decision_id,case_id,decision_type,title,rationale,related_entity_type,related_entity_id,
                         visibility,actor_user_id,supersedes_decision_id,client_request_id,created_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (decision_id, case_id, data["decision_type"], data["title"], data["rationale"],
                         data["related_entity_type"], data["related_entity_id"], data.get("visibility", "BANK_INTERNAL"),
                         actor, data.get("supersedes_decision_id"), data["client_request_id"], _naive_utc(now)),
                    )
                    item = _decision(await self._one(cursor, "case_decisions", "decision_id", case_id, decision_id))
                    await self._history(cursor, case_id, "DECISION", decision_id, 1, "APPEND", actor, None, item)
                await connection.commit()
                return item
            except BaseException:
                await connection.rollback()
                raise
