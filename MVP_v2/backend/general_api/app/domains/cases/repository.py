from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol
from uuid import uuid4


class CaseRepository(Protocol):
    async def find_by_client_request_id(self, client_request_id: str) -> dict[str, Any] | None: ...
    async def get(self, case_id: str) -> dict[str, Any] | None: ...
    async def create(self, record: dict[str, Any]) -> dict[str, Any]: ...
    async def list(self) -> list[dict[str, Any]]: ...
    async def append_message(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]: ...
    async def list_messages(self, case_id: str, channel: str | None = None) -> list[dict[str, Any]]: ...
    async def list_events(self, case_id: str, after: int | None = None) -> list[dict[str, Any]]: ...
    async def list_members(self, case_id: str) -> list[dict[str, Any]]: ...
    async def upsert_member(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]: ...
    async def list_presence(self, case_id: str) -> list[dict[str, Any]]: ...
    async def heartbeat_presence(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]: ...
    async def create_verification(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]: ...
    async def list_verifications(self, case_id: str) -> list[dict[str, Any]]: ...
    async def update_verification(self, case_id: str, verification_task_id: str, expected_version: int, status: str) -> dict[str, Any]: ...
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


class CaseVersionConflictError(Exception):
    def __init__(self, current_version: int) -> None:
        self.current_version = current_version
        super().__init__(f"Case version conflict: {current_version}")


class InMemoryCaseRepository:
    """MySQL adapter가 연결되기 전 fixture E2E용 저장소."""

    def __init__(self) -> None:
        self._records: list[dict[str, Any]] = []
        self._messages: list[dict[str, Any]] = []
        self._events: list[dict[str, Any]] = []
        self._verifications: list[dict[str, Any]] = []
        self._actions: list[dict[str, Any]] = []
        self._voice_sessions: list[dict[str, Any]] = []
        self._transcripts: list[dict[str, Any]] = []
        self._members: list[dict[str, Any]] = []
        self._presence: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()

    async def find_by_client_request_id(self, client_request_id: str) -> dict[str, Any] | None:
        return next((deepcopy(row) for row in self._records if row.get("client_request_id") == client_request_id), None)

    async def get(self, case_id: str) -> dict[str, Any] | None:
        return next((deepcopy(row) for row in self._records if row.get("case_id") == case_id), None)

    async def create(self, record: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            stored = deepcopy(record)
            stored.setdefault("case_id", f"VP-{len(self._records) + 1:06d}")
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
        return deepcopy(self._records)

    async def append_message(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            if not any(item["case_id"] == case_id for item in self._records):
                raise KeyError(case_id)
            now = datetime.now(timezone.utc).isoformat()
            message = {
                "message_id": f"msg-{uuid4().hex}", "case_id": case_id, **record,
                "channel": record.get("channel", "CUSTOMER"),
                "audience": record.get("audience", "CUSTOMER"),
                "mentions": record.get("mentions", []),
                "reply_to_message_id": record.get("reply_to_message_id"),
                "created_at": now,
            }
            self._messages.append(message)
            self._events.append({
                "event_id": len(self._events) + 1, "case_id": case_id, "event_type": "MESSAGE_ADDED",
                "actor_type": message["actor_type"],
                "payload": {"message_id": message["message_id"], "channel": message["channel"]}, "occurred_at": now,
            })
            return deepcopy(message)

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
            return deepcopy(member)

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
            return deepcopy(item)

    async def list_verifications(self, case_id: str) -> list[dict[str, Any]]:
        return [deepcopy(item) for item in self._verifications if item["case_id"] == case_id]

    async def update_verification(self, case_id: str, verification_task_id: str, expected_version: int, status: str) -> dict[str, Any]:
        async with self._lock:
            for item in self._verifications:
                if item["case_id"] != case_id or item["verification_task_id"] != verification_task_id:
                    continue
                if item["version"] != expected_version:
                    raise CaseVersionConflictError(item["version"])
                now = datetime.now(timezone.utc).isoformat()
                item["status"] = status
                item["version"] += 1
                item["updated_at"] = now
                self._events.append({"event_id": len(self._events) + 1, "case_id": case_id, "event_type": "VERIFICATION_UPDATED", "actor_type": "SYSTEM", "payload": {"verification_task_id": verification_task_id, "status": status, "version": item["version"]}, "occurred_at": now})
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
