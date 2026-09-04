from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol
from uuid import uuid4


_TARGET_FIELD_ALIASES = {
    "PERSONAL_INFO": "personal_information_exposure",
    "PERSONAL_INFORMATION": "personal_information_exposure",
    "AUTHENTICATION_INFO": "authentication_information_exposure",
    "AUTH_INFO": "authentication_information_exposure",
    "VICTIM_TRANSFER_STATUS": "transfer_status",
}


def normalize_target_field(value: str) -> str:
    normalized = value.strip()
    return _TARGET_FIELD_ALIASES.get(normalized.upper(), normalized.lower())


class CaseRepository(Protocol):
    async def next_case_id(self) -> str: ...
    async def find_by_client_request_id(self, client_request_id: str) -> dict[str, Any] | None: ...
    async def get(self, case_id: str) -> dict[str, Any] | None: ...
    async def create(self, record: dict[str, Any]) -> dict[str, Any]: ...
    async def list(self) -> list[dict[str, Any]]: ...
    async def delete_case(self, case_id: str) -> None: ...
    async def list_trashed_cases(self) -> list[dict[str, Any]]: ...
    async def restore_case(self, case_id: str) -> None: ...
    async def append_message(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]: ...
    async def list_messages(self, case_id: str, channel: str | None = None) -> list[dict[str, Any]]: ...
    async def create_attachment(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]: ...
    async def get_attachment(self, case_id: str, attachment_id: str) -> dict[str, Any] | None: ...
    async def list_attachments(self, case_id: str) -> list[dict[str, Any]]: ...
    async def list_events(self, case_id: str, after: int | None = None) -> list[dict[str, Any]]: ...
    async def list_members(self, case_id: str) -> list[dict[str, Any]]: ...
    async def upsert_member(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]: ...
    async def set_primary_assignee(self, case_id: str, display_name: str | None) -> str | None: ...
    async def list_presence(self, case_id: str) -> list[dict[str, Any]]: ...
    async def heartbeat_presence(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]: ...
    async def create_verification(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]: ...
    async def list_verifications(self, case_id: str) -> list[dict[str, Any]]: ...
    async def update_verification(self, case_id: str, verification_task_id: str, expected_version: int, status: str, details: dict[str, Any] | None = None) -> dict[str, Any]: ...
    async def create_action(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]: ...
    async def list_actions(self, case_id: str) -> list[dict[str, Any]]: ...
    async def update_case(self, case_id: str, expected_version: int, changes: dict[str, Any]) -> dict[str, Any]: ...
    async def create_voice_session(self, case_id: str, participants: list[str]) -> dict[str, Any]: ...
    async def update_voice_session(self, case_id: str, session_id: str, status: str) -> dict[str, Any]: ...
    async def get_voice_session(self, case_id: str, session_id: str | None = None) -> dict[str, Any] | None: ...
    async def append_transcript(self, case_id: str, session_id: str, record: dict[str, Any]) -> dict[str, Any]: ...
    async def list_transcript(self, case_id: str, session_id: str) -> list[dict[str, Any]]: ...
    async def finalize_report(self, case_id: str, expected_version: int, note: str) -> dict[str, Any]: ...
    async def get_final_report(self, case_id: str) -> dict[str, Any] | None: ...
    async def list_customer_questions(self, case_id: str) -> list[dict[str, Any]]: ...
    async def queue_customer_questions(self, case_id: str, questions: list[dict[str, Any]], requested_by: str) -> list[dict[str, Any]]: ...
    async def dispatch_next_customer_question(self, case_id: str) -> dict[str, Any] | None: ...
    async def link_customer_question_message(self, case_id: str, question_id: str, message_id: str) -> None: ...
    async def answer_customer_question(self, case_id: str, question_id: str, message_id: str, answer_text: str) -> dict[str, Any]: ...
    async def list_case_facts(self, case_id: str) -> list[dict[str, Any]]: ...
    async def propose_case_fact(self, case_id: str, question_id: str, value: str, evidence_message_id: str | None) -> dict[str, Any]: ...
    async def confirm_case_fact(self, case_id: str, fact_id: str, confirmed_by: str) -> dict[str, Any]: ...
    async def list_personal_notes(self, case_id: str, author_id: str) -> list[dict[str, Any]]: ...
    async def create_personal_note(self, case_id: str, author_id: str, content: str) -> dict[str, Any]: ...
    async def update_personal_note(self, case_id: str, note_id: str, author_id: str, content: str) -> dict[str, Any]: ...
    async def delete_personal_note(self, case_id: str, note_id: str, author_id: str) -> None: ...


class CaseVersionConflictError(Exception):
    def __init__(self, current_version: int) -> None:
        self.current_version = current_version
        super().__init__(f"Case version conflict: {current_version}")


class InMemoryCaseRepository:
    """MySQL adapter가 연결되기 전 fixture E2E용 저장소."""

    def __init__(self) -> None:
        self._records: list[dict[str, Any]] = []
        self._messages: list[dict[str, Any]] = []
        self._attachments: list[dict[str, Any]] = []
        self._events: list[dict[str, Any]] = []
        self._verifications: list[dict[str, Any]] = []
        self._actions: list[dict[str, Any]] = []
        self._voice_sessions: list[dict[str, Any]] = []
        self._transcripts: list[dict[str, Any]] = []
        self._members: list[dict[str, Any]] = []
        self._presence: list[dict[str, Any]] = []
        self._customer_questions: list[dict[str, Any]] = []
        self._case_facts: list[dict[str, Any]] = []
        self._personal_notes: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()

    def _touch_case(self, case_id: str, occurred_at: str) -> None:
        case = next((item for item in self._records if item["case_id"] == case_id and not item.get("deleted_at")), None)
        if case is None:
            raise KeyError(case_id)
        case["updated_at"] = occurred_at

    def _remove_case_records(self, case_id: str) -> None:
        self._records = [item for item in self._records if item.get("case_id") != case_id]
        self._messages = [item for item in self._messages if item.get("case_id") != case_id]
        self._attachments = [item for item in self._attachments if item.get("case_id") != case_id]
        self._events = [item for item in self._events if item.get("case_id") != case_id]
        self._verifications = [item for item in self._verifications if item.get("case_id") != case_id]
        self._actions = [item for item in self._actions if item.get("case_id") != case_id]
        self._voice_sessions = [item for item in self._voice_sessions if item.get("case_id") != case_id]
        self._transcripts = [item for item in self._transcripts if item.get("case_id") != case_id]
        self._members = [item for item in self._members if item.get("case_id") != case_id]
        self._presence = [item for item in self._presence if item.get("case_id") != case_id]
        self._customer_questions = [item for item in self._customer_questions if item.get("case_id") != case_id]
        self._case_facts = [item for item in self._case_facts if item.get("case_id") != case_id]
        self._personal_notes = [item for item in self._personal_notes if item.get("case_id") != case_id]

    def _purge_expired_trash(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        expired = [item["case_id"] for item in self._records if item.get("deleted_at") and datetime.fromisoformat(item["deleted_at"]) <= cutoff]
        for case_id in expired:
            self._remove_case_records(case_id)

    async def find_by_client_request_id(self, client_request_id: str) -> dict[str, Any] | None:
        return next((deepcopy(row) for row in self._records if row.get("client_request_id") == client_request_id), None)

    async def next_case_id(self) -> str:
        """Allocate human-readable, monotonically increasing local Case IDs."""
        async with self._lock:
            numbers = [int(str(row["case_id"]).removeprefix("VP-")) for row in self._records if str(row.get("case_id", "")).removeprefix("VP-").isdigit()]
            return f"VP-{max(numbers, default=0) + 1}"

    async def get(self, case_id: str) -> dict[str, Any] | None:
        return next((deepcopy(row) for row in self._records if row.get("case_id") == case_id and not row.get("deleted_at")), None)

    async def create(self, record: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            stored = deepcopy(record)
            stored.setdefault("case_id", f"VP-{len(self._records) + 1}")
            stored.setdefault("version", 1)
            self._records.append(stored)
            self._events.append({
                "event_id": len(self._events) + 1, "case_id": stored["case_id"], "event_type": "CASE_CREATED",
                "actor_type": "SYSTEM", "payload": {"report_id": stored["initial_report"]["report_id"]},
                "occurred_at": stored["created_at"],
            })
            return deepcopy(stored)

    async def update_case(self, case_id: str, expected_version: int, changes: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            for item in self._records:
                if item.get("case_id") != case_id:
                    continue
                current_version = int(item.get("version", 1))
                if current_version != expected_version:
                    raise CaseVersionConflictError(current_version)
                item.update(changes)
                item["version"] = current_version + 1
                item["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._events.append({
                    "event_id": len(self._events) + 1, "case_id": case_id, "event_type": "CASE_FIELD_UPDATED",
                    "actor_type": "SYSTEM", "payload": {**changes, "version": item["version"]},
                    "occurred_at": item["updated_at"],
                })
                return deepcopy(item)
            raise KeyError(case_id)

    async def list(self) -> list[dict[str, Any]]:
        self._purge_expired_trash()
        return [deepcopy(item) for item in self._records if not item.get("deleted_at")]

    async def list_trashed_cases(self) -> list[dict[str, Any]]:
        self._purge_expired_trash()
        return [deepcopy(item) for item in self._records if item.get("deleted_at")]

    async def delete_case(self, case_id: str) -> None:
        """Move one Case to the local recycle bin without discarding its records."""
        async with self._lock:
            item = next((row for row in self._records if row.get("case_id") == case_id and not row.get("deleted_at")), None)
            if item is None: raise KeyError(case_id)
            item["deleted_at"] = datetime.now(timezone.utc).isoformat()

    async def restore_case(self, case_id: str) -> None:
        async with self._lock:
            item = next((row for row in self._records if row.get("case_id") == case_id and row.get("deleted_at")), None)
            if item is None: raise KeyError(case_id)
            item.pop("deleted_at", None)
            item["updated_at"] = datetime.now(timezone.utc).isoformat()

    async def append_message(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            if not any(item["case_id"] == case_id for item in self._records):
                raise KeyError(case_id)
            attachment_ids = list(dict.fromkeys(record.get("attachment_ids", [])))
            attachments = [item for item in self._attachments if item["case_id"] == case_id and item["attachment_id"] in attachment_ids]
            if len(attachments) != len(attachment_ids):
                raise ValueError("ATTACHMENT_NOT_FOUND")
            if any(item.get("status") != "UPLOADED" or item.get("visibility") != record.get("visibility", record.get("audience", "CUSTOMER")) for item in attachments):
                raise ValueError("ATTACHMENT_NOT_LINKABLE")
            now = datetime.now(timezone.utc).isoformat()
            message = {
                "message_id": f"msg-{uuid4().hex}", "case_id": case_id, **record,
                "channel": record.get("channel", "CUSTOMER"),
                "audience": record.get("audience", "CUSTOMER"),
                "visibility": record.get("visibility", record.get("audience", "CUSTOMER")),
                "message_kind": record.get("message_kind", "CHAT"),
                "mentions": record.get("mentions", []),
                "reply_to_message_id": record.get("reply_to_message_id"),
                "attachment_ids": attachment_ids,
                "created_at": now,
            }
            for attachment in attachments:
                attachment["status"] = "LINKED"
                attachment["message_id"] = message["message_id"]
            message["attachments"] = [deepcopy(item) for item in attachments]
            self._messages.append(message)
            self._touch_case(case_id, now)
            if record.get("log_event"):
                self._events.append({
                    "event_id": len(self._events) + 1, "case_id": case_id, "event_type": "MESSAGE_ADDED",
                    "actor_type": message["actor_type"],
                    "payload": {"message_id": message["message_id"], "channel": message["channel"]}, "occurred_at": now,
                })
            return deepcopy(message)

    async def create_attachment(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            if not any(item["case_id"] == case_id for item in self._records):
                raise KeyError(case_id)
            attachment = {"attachment_id": f"att-{uuid4().hex}", "case_id": case_id, **record}
            self._attachments.append(attachment)
            return deepcopy(attachment)

    async def get_attachment(self, case_id: str, attachment_id: str) -> dict[str, Any] | None:
        return next((deepcopy(item) for item in self._attachments if item["case_id"] == case_id and item["attachment_id"] == attachment_id), None)

    async def list_attachments(self, case_id: str) -> list[dict[str, Any]]:
        return [deepcopy(item) for item in self._attachments if item["case_id"] == case_id]

    async def list_messages(self, case_id: str, channel: str | None = None) -> list[dict[str, Any]]:
        return [deepcopy(item) for item in self._messages if item["case_id"] == case_id and (channel is None or item.get("channel") == channel)]

    async def list_events(self, case_id: str, after: int | None = None) -> list[dict[str, Any]]:
        return [deepcopy(item) for item in self._events if item["case_id"] == case_id and (after is None or item["event_id"] > after)]

    async def list_members(self, case_id: str) -> list[dict[str, Any]]:
        return [deepcopy(item) for item in self._members if item["case_id"] == case_id and item["status"] == "ACTIVE"]

    async def upsert_member(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            if not any(item["case_id"] == case_id for item in self._records):
                raise KeyError(case_id)
            now = datetime.now(timezone.utc).isoformat()
            member = next((item for item in self._members if item["case_id"] == case_id and item["user_id"] == record["user_id"]), None)
            if member is None:
                member = {"case_id": case_id, **record, "status": "ACTIVE", "assigned_at": now, "updated_at": now}
                self._members.append(member)
            else:
                member.update(record)
                member["status"] = "ACTIVE"
                member["updated_at"] = now
            self._events.append({
                "event_id": len(self._events) + 1, "case_id": case_id, "event_type": "CASE_MEMBER_UPDATED",
                "actor_type": "SYSTEM", "payload": {"user_id": member["user_id"], "role": member["role"]}, "occurred_at": now,
            })
            self._touch_case(case_id, now)
            return deepcopy(member)

    async def set_primary_assignee(self, case_id: str, display_name: str | None) -> str | None:
        async with self._lock:
            if not any(item["case_id"] == case_id for item in self._records):
                raise KeyError(case_id)
            now = datetime.now(timezone.utc).isoformat()
            for member in self._members:
                if member["case_id"] == case_id and member["role"] == "CASE_OWNER":
                    member["role"] = "VIEWER"
                    member["updated_at"] = now
            normalized = (display_name or "").strip()
            if normalized:
                member = next((item for item in self._members if item["case_id"] == case_id and item["display_name"] == normalized), None)
                if member is None:
                    member = {"case_id": case_id, "user_id": f"owner-{uuid4().hex}", "display_name": normalized, "role": "CASE_OWNER", "status": "ACTIVE", "assigned_at": now, "updated_at": now}
                    self._members.append(member)
                else:
                    member.update({"role": "CASE_OWNER", "status": "ACTIVE", "updated_at": now})
            self._events.append({"event_id": len(self._events) + 1, "case_id": case_id, "event_type": "CASE_ASSIGNEE_UPDATED", "actor_type": "SYSTEM", "payload": {"display_name": normalized or None}, "occurred_at": now})
            self._touch_case(case_id, now)
            return normalized or None

    async def list_presence(self, case_id: str) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        return [
            deepcopy(item) for item in self._presence
            if item["case_id"] == case_id and datetime.fromisoformat(item["expires_at"]) > now
        ]

    async def heartbeat_presence(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            if not any(item["case_id"] == case_id for item in self._records):
                raise KeyError(case_id)
            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(seconds=45)
            presence = next((item for item in self._presence if item["case_id"] == case_id and item["user_id"] == record["user_id"]), None)
            values = {"case_id": case_id, **record, "last_seen_at": now.isoformat(), "expires_at": expires_at.isoformat()}
            if presence is None:
                self._presence.append(values)
                presence = values
            else:
                presence.update(values)
            return deepcopy(presence)

    async def create_verification(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            if not any(item["case_id"] == case_id for item in self._records):
                raise KeyError(case_id)
            now = datetime.now(timezone.utc).isoformat()
            item = {"verification_task_id": f"ver-{uuid4().hex}", "case_id": case_id, **record, "status": "PENDING", "version": 1, "created_at": now, "updated_at": now}
            self._verifications.append(item)
            self._events.append({"event_id": len(self._events) + 1, "case_id": case_id, "event_type": "VERIFICATION_CREATED", "actor_type": "BANK_STAFF", "payload": {"verification_task_id": item["verification_task_id"]}, "occurred_at": now})
            self._touch_case(case_id, now)
            return deepcopy(item)

    async def list_verifications(self, case_id: str) -> list[dict[str, Any]]:
        return [deepcopy(item) for item in self._verifications if item["case_id"] == case_id]

    async def update_verification(self, case_id: str, verification_task_id: str, expected_version: int, status: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
        async with self._lock:
            for item in self._verifications:
                if item["case_id"] != case_id or item["verification_task_id"] != verification_task_id:
                    continue
                if item["version"] != expected_version:
                    raise CaseVersionConflictError(item["version"])
                now = datetime.now(timezone.utc).isoformat()
                item["status"] = status
                if details:
                    for key in ("result_summary", "evidence_url", "verified_by", "rag_source", "customer_visible"):
                        if key in details:
                            item[key] = details[key]
                item["version"] += 1
                item["updated_at"] = now
                self._events.append({"event_id": len(self._events) + 1, "case_id": case_id, "event_type": "VERIFICATION_UPDATED", "actor_type": "SYSTEM", "payload": {"verification_task_id": verification_task_id, "status": status, "version": item["version"]}, "occurred_at": now})
                self._touch_case(case_id, now)
                return deepcopy(item)
            raise KeyError(verification_task_id)

    async def create_action(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            if not any(item["case_id"] == case_id for item in self._records):
                raise KeyError(case_id)
            now = datetime.now(timezone.utc).isoformat()
            item = {"action_id": f"act-{uuid4().hex}", "case_id": case_id, **record, "status": "REQUESTED", "created_at": now}
            self._actions.append(item)
            self._events.append({"event_id": len(self._events) + 1, "case_id": case_id, "event_type": "BANK_ACTION_ADDED", "actor_type": item["actor_type"], "payload": {"action_id": item["action_id"]}, "occurred_at": now})
            self._touch_case(case_id, now)
            return deepcopy(item)

    async def list_actions(self, case_id: str) -> list[dict[str, Any]]:
        return [deepcopy(item) for item in self._actions if item["case_id"] == case_id]

    async def create_voice_session(self, case_id: str, participants: list[str]) -> dict[str, Any]:
        async with self._lock:
            if not any(item["case_id"] == case_id for item in self._records):
                raise KeyError(case_id)
            now = datetime.now(timezone.utc).isoformat()
            session = {"session_id": f"voice-{uuid4().hex}", "case_id": case_id, "status": "REQUESTED", "participants": participants, "started_at": None, "ended_at": None, "created_at": now}
            self._voice_sessions.append(session)
            self._events.append({"event_id": len(self._events) + 1, "case_id": case_id, "event_type": "VOICE_SESSION_REQUESTED", "actor_type": "SYSTEM", "payload": {"session_id": session["session_id"]}, "occurred_at": now})
            return deepcopy(session)

    async def update_voice_session(self, case_id: str, session_id: str, status: str) -> dict[str, Any]:
        async with self._lock:
            for session in self._voice_sessions:
                if session["case_id"] == case_id and session["session_id"] == session_id:
                    now = datetime.now(timezone.utc).isoformat()
                    session["status"] = status
                    if status == "ACTIVE": session["started_at"] = session["started_at"] or now
                    if status in {"ENDED", "FAILED"}: session["ended_at"] = now
                    self._events.append({"event_id": len(self._events) + 1, "case_id": case_id, "event_type": f"VOICE_SESSION_{status}", "actor_type": "SYSTEM", "payload": {"session_id": session_id}, "occurred_at": now})
                    return deepcopy(session)
            raise KeyError(session_id)

    async def get_voice_session(self, case_id: str, session_id: str | None = None) -> dict[str, Any] | None:
        found = [item for item in self._voice_sessions if item["case_id"] == case_id and (session_id is None or item["session_id"] == session_id)]
        return deepcopy(found[-1]) if found else None

    async def append_transcript(self, case_id: str, session_id: str, record: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            session = await self.get_voice_session(case_id, session_id)
            if session is None: raise KeyError(session_id)
            now = datetime.now(timezone.utc).isoformat()
            item = {"segment_id": f"seg-{uuid4().hex}", "session_id": session_id, "case_id": case_id, **record, "created_at": now}
            self._transcripts.append(item)
            self._events.append({"event_id": len(self._events) + 1, "case_id": case_id, "event_type": "TRANSCRIPT_SEGMENT_ADDED", "actor_type": "SYSTEM", "payload": {"session_id": session_id, "segment_id": item["segment_id"]}, "occurred_at": now})
            return deepcopy(item)

    async def list_transcript(self, case_id: str, session_id: str) -> list[dict[str, Any]]:
        return [deepcopy(item) for item in self._transcripts if item["case_id"] == case_id and item["session_id"] == session_id]

    async def finalize_report(self, case_id: str, expected_version: int, note: str) -> dict[str, Any]:
        async with self._lock:
            case = next((item for item in self._records if item["case_id"] == case_id), None)
            if case is None: raise KeyError(case_id)
            current_version = int(case.get("version", 1))
            if current_version != expected_version: raise CaseVersionConflictError(current_version)
            now = datetime.now(timezone.utc).isoformat()
            live = deepcopy(case.get("initial_report")) or {"sections": []}
            report = {"report_id": f"final-{case_id}", "case_id": case_id, "report_version": int(live.get("report_version", 1)), "status": "FINAL", "sections": live.get("sections", []), "created_at": now, "note": note}
            case["final_report"] = report
            case["mode"] = "CLOSED"; case["status"] = "CLOSED"; case["version"] = current_version + 1; case["updated_at"] = now
            self._events.append({"event_id": len(self._events) + 1, "case_id": case_id, "event_type": "CASE_REPORT_FINALIZED", "actor_type": "BANK_STAFF", "payload": {"report_id": report["report_id"], "version": case["version"]}, "occurred_at": now})
            return deepcopy(report)

    async def get_final_report(self, case_id: str) -> dict[str, Any] | None:
        case = await self.get(case_id)
        return deepcopy(case.get("final_report")) if case else None

    async def list_customer_questions(self, case_id: str) -> list[dict[str, Any]]:
        """Return the durable customer-question queue in delivery order."""
        return sorted(
            [deepcopy(item) for item in self._customer_questions if item["case_id"] == case_id],
            key=lambda item: (item["sequence"], item["question_id"]),
        )

    async def queue_customer_questions(
        self, case_id: str, questions: list[dict[str, Any]], requested_by: str
    ) -> list[dict[str, Any]]:
        """Queue bank-approved questions; never send them to the customer implicitly."""
        async with self._lock:
            if not any(item["case_id"] == case_id and not item.get("deleted_at") for item in self._records):
                raise KeyError(case_id)
            handled_questions = [
                item for item in self._customer_questions
                if item["case_id"] == case_id and item["status"] in {"PENDING", "ASKED", "ANSWERED"}
            ]
            active_fields = {
                normalize_target_field(item["target_field"])
                for item in handled_questions
            }
            active_texts = {
                " ".join(str(item.get("question_text", "")).split()).casefold()
                for item in handled_questions
            }
            sequence = max(
                (int(item["sequence"]) for item in self._customer_questions if item["case_id"] == case_id),
                default=0,
            )
            now = datetime.now(timezone.utc).isoformat()
            created: list[dict[str, Any]] = []
            for question in questions:
                target_field = normalize_target_field(question["target_field"])
                normalized_text = " ".join(str(question["question_text"]).split()).casefold()
                if target_field in active_fields or normalized_text in active_texts:
                    continue
                sequence += 1
                item = {
                    "question_id": f"cq-{uuid4().hex}", "case_id": case_id,
                    "source": question.get("source", "BANK_SELECTED"), "target_field": target_field,
                    "question_text": question["question_text"], "reason": question["reason"],
                    "priority": question["priority"], "options": question.get("options", []),
                    "customer_explanation": question.get("customer_explanation"),
                    "answer_mode": question.get("answer_mode", "CHOICE_OR_TEXT"),
                    "allow_free_text": question.get("allow_free_text", True),
                    "status": "PENDING", "sequence": sequence,
                    "requested_by": requested_by, "asked_at": None, "answered_at": None, "answer_text": None,
                    "created_at": now,
                }
                self._customer_questions.append(item)
                created.append(deepcopy(item))
                active_fields.add(target_field)
                active_texts.add(normalized_text)
            if created:
                self._events.append({
                    "event_id": len(self._events) + 1, "case_id": case_id,
                    "event_type": "CUSTOMER_QUESTIONS_QUEUED",
                    "actor_type": "CUSTOMER_AGENT" if all(item.get("source") == "CUSTOMER_AGENT" for item in created) else "BANK_STAFF",
                    "payload": {"question_ids": [item["question_id"] for item in created]}, "occurred_at": now,
                })
                self._touch_case(case_id, now)
            return created

    async def dispatch_next_customer_question(self, case_id: str) -> dict[str, Any] | None:
        """Mark exactly one queued question as customer-visible."""
        async with self._lock:
            if any(row["case_id"] == case_id and row["status"] == "ASKED" for row in self._customer_questions):
                return None
            item = next((row for row in sorted(self._customer_questions, key=lambda row: row["sequence"])
                         if row["case_id"] == case_id and row["status"] == "PENDING"), None)
            if item is None:
                return None
            now = datetime.now(timezone.utc).isoformat()
            item["status"] = "ASKED"
            item["asked_at"] = now
            self._events.append({
                "event_id": len(self._events) + 1, "case_id": case_id,
                "event_type": "CUSTOMER_QUESTION_DISPATCHED", "actor_type": "CUSTOMER_AGENT",
                "payload": {"question_id": item["question_id"]}, "occurred_at": now,
            })
            self._touch_case(case_id, now)
            return deepcopy(item)

    async def link_customer_question_message(self, case_id: str, question_id: str, message_id: str) -> None:
        """Persist the public message that rendered a queued question card."""
        async with self._lock:
            item = next((row for row in self._customer_questions if row["case_id"] == case_id and row["question_id"] == question_id), None)
            if item is None:
                raise KeyError(question_id)
            item["question_message_id"] = message_id

    async def answer_customer_question(self, case_id: str, question_id: str, message_id: str, answer_text: str) -> dict[str, Any]:
        async with self._lock:
            item = next((row for row in self._customer_questions if row["case_id"] == case_id and row["question_id"] == question_id), None)
            if item is None or item["status"] != "ASKED":
                raise KeyError(question_id)
            now = datetime.now(timezone.utc).isoformat()
            item["status"] = "ANSWERED"
            item["answered_at"] = now
            item["answer_message_id"] = message_id
            item["answer_text"] = answer_text
            self._events.append({
                "event_id": len(self._events) + 1, "case_id": case_id,
                "event_type": "CUSTOMER_QUESTION_ANSWERED", "actor_type": "CUSTOMER",
                "payload": {"question_id": question_id, "message_id": message_id}, "occurred_at": now,
            })
            self._touch_case(case_id, now)
            return deepcopy(item)

    async def list_case_facts(self, case_id: str) -> list[dict[str, Any]]:
        return [deepcopy(item) for item in self._case_facts if item["case_id"] == case_id]

    async def propose_case_fact(self, case_id: str, question_id: str, value: str, evidence_message_id: str | None) -> dict[str, Any]:
        async with self._lock:
            if not any(row["case_id"] == case_id and not row.get("deleted_at") for row in self._records):
                raise KeyError(case_id)
            question = next((row for row in self._customer_questions if row["case_id"] == case_id and row["question_id"] == question_id), None)
            if question is None:
                raise KeyError(question_id)
            canonical_field = normalize_target_field(question["target_field"])
            existing = next((row for row in self._case_facts if row["case_id"] == case_id and normalize_target_field(row["field"]) == canonical_field and row["status"] == "PROPOSED"), None)
            if existing is not None:
                existing["field"] = canonical_field
                existing["value"] = value
                existing["evidence_message_id"] = evidence_message_id
                existing["source_question_id"] = question_id
                return deepcopy(existing)
            now = datetime.now(timezone.utc).isoformat()
            fact = {"fact_id": f"fact-{uuid4().hex}", "case_id": case_id, "field": canonical_field, "value": value, "source": "AI_EXTRACTED", "status": "PROPOSED", "confidence": 0.7, "evidence_message_id": evidence_message_id, "source_question_id": question_id, "confirmed_by": None, "confirmed_at": None, "created_at": now}
            self._case_facts.append(fact)
            self._events.append({"event_id": len(self._events) + 1, "case_id": case_id, "event_type": "CASE_FACT_PROPOSED", "actor_type": "CUSTOMER_AGENT", "payload": {"fact_id": fact["fact_id"], "field": fact["field"]}, "occurred_at": now})
            self._touch_case(case_id, now)
            return deepcopy(fact)

    async def confirm_case_fact(self, case_id: str, fact_id: str, confirmed_by: str) -> dict[str, Any]:
        async with self._lock:
            fact = next((row for row in self._case_facts if row["case_id"] == case_id and row["fact_id"] == fact_id), None)
            if fact is None:
                raise KeyError(fact_id)
            now = datetime.now(timezone.utc).isoformat()
            fact["status"] = "CONFIRMED"; fact["source"] = "HUMAN_CONFIRMED"; fact["confirmed_by"] = confirmed_by; fact["confirmed_at"] = now
            self._events.append({"event_id": len(self._events) + 1, "case_id": case_id, "event_type": "CASE_FACT_CONFIRMED", "actor_type": "BANK_STAFF", "payload": {"fact_id": fact_id, "field": fact["field"]}, "occurred_at": now})
            self._touch_case(case_id, now)
            return deepcopy(fact)

    async def list_personal_notes(self, case_id: str, author_id: str) -> list[dict[str, Any]]:
        return [deepcopy(item) for item in self._personal_notes if item["case_id"] == case_id and item["author_id"] == author_id]

    async def create_personal_note(self, case_id: str, author_id: str, content: str) -> dict[str, Any]:
        async with self._lock:
            if not any(row["case_id"] == case_id and not row.get("deleted_at") for row in self._records):
                raise KeyError(case_id)
            now = datetime.now(timezone.utc).isoformat()
            note = {"note_id": f"note-{uuid4().hex}", "case_id": case_id, "author_id": author_id, "content": content, "visibility": "PRIVATE_TO_AUTHOR", "created_at": now, "updated_at": now}
            self._personal_notes.append(note)
            return deepcopy(note)

    async def update_personal_note(self, case_id: str, note_id: str, author_id: str, content: str) -> dict[str, Any]:
        async with self._lock:
            note = next((row for row in self._personal_notes if row["case_id"] == case_id and row["note_id"] == note_id and row["author_id"] == author_id), None)
            if note is None:
                raise KeyError(note_id)
            note["content"] = content
            note["updated_at"] = datetime.now(timezone.utc).isoformat()
            return deepcopy(note)

    async def delete_personal_note(self, case_id: str, note_id: str, author_id: str) -> None:
        async with self._lock:
            original = len(self._personal_notes)
            self._personal_notes = [row for row in self._personal_notes if not (row["case_id"] == case_id and row["note_id"] == note_id and row["author_id"] == author_id)]
            if len(self._personal_notes) == original:
                raise KeyError(note_id)
