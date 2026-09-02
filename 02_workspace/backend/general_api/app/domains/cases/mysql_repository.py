from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime
from typing import Any

import aiomysql

from .repository import CaseVersionConflictError


class MySqlCaseRepository:
    """Core migration을 사용하는 영구 Case Repository."""

    def __init__(self) -> None:
        self._pool: aiomysql.Pool | None = None

    async def _get_pool(self) -> aiomysql.Pool:
        if self._pool is None:
            self._pool = await aiomysql.create_pool(
                host=os.getenv("MYSQL_HOST", "127.0.0.1"),
                port=int(os.getenv("MYSQL_PORT", "3306")),
                user=os.getenv("MYSQL_USER", "root"),
                password=os.getenv("MYSQL_PASSWORD", ""),
                db=os.getenv("MYSQL_DATABASE", "aix_case_platform"),
                autocommit=False,
                minsize=1,
                maxsize=5,
            )
        return self._pool

    async def close(self) -> None:
        """테스트·애플리케이션 종료 시 MySQL 연결 Pool을 정리한다."""
        if self._pool is None:
            return
        self._pool.close()
        await self._pool.wait_closed()
        self._pool = None

    async def find_by_client_request_id(self, client_request_id: str) -> dict[str, Any] | None:
        pool = await self._get_pool()
        async with pool.acquire() as connection, connection.cursor() as cursor:
            await cursor.execute("SELECT case_id FROM cases WHERE client_request_id=%s", (client_request_id,))
            row = await cursor.fetchone()
        return await self.get(row[0]) if row else None

    async def get(self, case_id: str) -> dict[str, Any] | None:
        pool = await self._get_pool()
        async with pool.acquire() as connection, connection.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(
                """SELECT c.*, i.input_text FROM cases c
                   LEFT JOIN case_inputs i ON i.case_id=c.case_id
                   WHERE c.case_id=%s ORDER BY i.input_id LIMIT 1""",
                (case_id,),
            )
            case_row = await cursor.fetchone()
            if not case_row:
                return None
            await cursor.execute("SELECT * FROM case_reports WHERE case_id=%s AND report_type='LIVE'", (case_id,))
            report_row = await cursor.fetchone()
            sections: list[dict[str, Any]] = []
            if report_row:
                await cursor.execute(
                    "SELECT section_key, content_json, section_version FROM case_report_sections WHERE report_id=%s ORDER BY section_key",
                    (report_row["report_id"],),
                )
                sections = [
                    {"section_key": row["section_key"], "content": self._json(row["content_json"]), "version": row["section_version"]}
                    for row in await cursor.fetchall()
                ]
        return {
            "case_id": case_row["case_id"], "version": case_row.get("version", 1), "client_request_id": case_row["client_request_id"],
            "input_text": case_row["input_text"], "risk": case_row["risk_level"],
            "risk_score": float(case_row["risk_score"]), "mode": case_row["mode"], "status": case_row["status"],
            "initial_brief": case_row["initial_brief"], "diagnosis": self._json(case_row["diagnosis_json"]),
            "initial_report": {
                "report_id": report_row["report_id"], "case_id": case_id,
                "report_version": report_row["report_version"], "status": report_row["report_type"],
                "sections": sections, "created_at": report_row["created_at"].isoformat(),
            } if report_row else None,
            "created_at": case_row["created_at"].isoformat(), "updated_at": case_row["updated_at"].isoformat(),
        }

    async def create(self, record: dict[str, Any]) -> dict[str, Any]:
        pool = await self._get_pool()
        # MySQL DATETIME은 timezone 정보를 저장하지 않으므로 UTC offset을 제거한다.
        created_at = datetime.fromisoformat(record["created_at"]).replace(tzinfo=None)
        updated_at = datetime.fromisoformat(record["updated_at"]).replace(tzinfo=None)
        diagnosis = record["diagnosis"]
        report = record["initial_report"]
        async with pool.acquire() as connection:
            try:
                async with connection.cursor() as cursor:
                    await cursor.execute(
                        """INSERT INTO cases
                           (case_id, client_request_id, risk_level, risk_score, mode, status, version, initial_brief, diagnosis_json, created_at, updated_at)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (record["case_id"], record.get("client_request_id"), record["risk"], record["risk_score"],
                         record["mode"], record["status"], record.get("version", 1), record["initial_brief"], json.dumps(diagnosis, ensure_ascii=False),
                         created_at, updated_at),
                    )
                    await cursor.execute(
                        "INSERT INTO case_inputs (case_id, input_type, input_text, created_at) VALUES (%s,'TEXT',%s,%s)",
                        (record["case_id"], record["input_text"], created_at),
                    )
                    for window in diagnosis["windows"]:
                        await cursor.execute(
                            """INSERT INTO analysis_segments
                               (segment_id, case_id, start_turn, end_turn, segment_text, risk_score, model_label, evidence_json, created_at)
                               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                            (f"{record['case_id']}-{window['segment_id']}", record["case_id"], window["start_turn"], window["end_turn"],
                             window["text"], window["final_risk_score"], window["label"], json.dumps(diagnosis["evidence"], ensure_ascii=False), created_at),
                        )
                    for key, value in diagnosis["features"].items():
                        await cursor.execute(
                            "INSERT INTO context_features (case_id, segment_id, feature_key, feature_value, source, created_at) VALUES (%s,NULL,%s,%s,'DIAGNOSIS_FUSION',%s)",
                            (record["case_id"], key, float(value), created_at),
                        )
                    await cursor.execute(
                        "INSERT INTO case_reports (report_id, case_id, report_type, report_version, created_at, updated_at) VALUES (%s,%s,'LIVE',%s,%s,%s)",
                        (report["report_id"], record["case_id"], report["report_version"], created_at, updated_at),
                    )
                    for section in report["sections"]:
                        await cursor.execute(
                            "INSERT INTO case_report_sections (report_id, section_key, content_json, section_version, updated_at) VALUES (%s,%s,%s,%s,%s)",
                            (report["report_id"], section["section_key"], json.dumps(section["content"], ensure_ascii=False), section["version"], updated_at),
                        )
                    await cursor.execute(
                        "INSERT INTO case_events (case_id, event_type, actor_type, payload_json, occurred_at) VALUES (%s,'CASE_CREATED','SYSTEM',%s,%s)",
                        (record["case_id"], json.dumps({"report_id": report["report_id"]}), created_at),
                    )
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        return deepcopy(record)

    async def update_case(self, case_id: str, expected_version: int, changes: dict[str, Any]) -> dict[str, Any]:
        pool = await self._get_pool()
        now = datetime.now()
        async with pool.acquire() as connection:
            try:
                async with connection.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute("SELECT version FROM cases WHERE case_id=%s FOR UPDATE", (case_id,))
                    row = await cursor.fetchone()
                    if not row:
                        raise KeyError(case_id)
                    current_version = int(row["version"])
                    if current_version != expected_version:
                        raise CaseVersionConflictError(current_version)
                    assignments = ", ".join(f"{field}=%s" for field in changes) + ", version=%s, updated_at=%s"
                    values = tuple(changes.values()) + (current_version + 1, now, case_id)
                    await cursor.execute(f"UPDATE cases SET {assignments} WHERE case_id=%s", values)
                    await cursor.execute(
                        "INSERT INTO case_events (case_id, event_type, actor_type, payload_json, occurred_at) VALUES (%s,'CASE_FIELD_UPDATED','SYSTEM',%s,%s)",
                        (case_id, json.dumps({**changes, "version": current_version + 1}), now),
                    )
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        updated = await self.get(case_id)
        if updated is None:
            raise KeyError(case_id)
        return updated

    async def list(self) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as connection, connection.cursor() as cursor:
            await cursor.execute("SELECT case_id FROM cases ORDER BY created_at DESC")
            ids = [row[0] for row in await cursor.fetchall()]
        return [record for case_id in ids if (record := await self.get(case_id)) is not None]

    async def append_message(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]:
        pool = await self._get_pool()
        message_id = f"msg-{__import__('uuid').uuid4().hex}"
        created_at = datetime.now()
        async with pool.acquire() as connection:
            try:
                async with connection.cursor() as cursor:
                    await cursor.execute("SELECT case_id FROM cases WHERE case_id=%s FOR UPDATE", (case_id,))
                    if not await cursor.fetchone():
                        raise KeyError(case_id)
                    await cursor.execute(
                        "INSERT INTO messages (message_id, case_id, actor_type, content, client_request_id, created_at) VALUES (%s,%s,%s,%s,%s,%s)",
                        (message_id, case_id, record["actor_type"], record["content"], record.get("client_request_id"), created_at),
                    )
                    await cursor.execute(
                        "INSERT INTO case_events (case_id, event_type, actor_type, payload_json, occurred_at) VALUES (%s,'MESSAGE_ADDED',%s,%s,%s)",
                        (case_id, record["actor_type"], json.dumps({"message_id": message_id}), created_at),
                    )
                    await cursor.execute("UPDATE cases SET updated_at=%s WHERE case_id=%s", (created_at, case_id))
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        return {"message_id": message_id, "case_id": case_id, **record, "created_at": created_at.isoformat()}

    async def list_messages(self, case_id: str) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as connection, connection.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(
                "SELECT message_id, case_id, actor_type, content, created_at FROM messages WHERE case_id=%s ORDER BY created_at, message_id",
                (case_id,),
            )
            return [{**row, "created_at": row["created_at"].isoformat()} for row in await cursor.fetchall()]

    async def list_events(self, case_id: str, after: int | None = None) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        query = "SELECT event_id, case_id, event_type, actor_type, payload_json, occurred_at FROM case_events WHERE case_id=%s"
        values: tuple[Any, ...] = (case_id,)
        if after is not None:
            query += " AND event_id > %s"
            values += (after,)
        query += " ORDER BY event_id"
        async with pool.acquire() as connection, connection.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(query, values)
            return [
                {"event_id": row["event_id"], "case_id": row["case_id"], "event_type": row["event_type"],
                 "actor_type": row["actor_type"], "payload": self._json(row["payload_json"]), "occurred_at": row["occurred_at"].isoformat()}
                for row in await cursor.fetchall()
            ]

    async def create_verification(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]:
        pool = await self._get_pool()
        verification_task_id = f"ver-{__import__('uuid').uuid4().hex}"
        now = datetime.now()
        async with pool.acquire() as connection:
            try:
                async with connection.cursor() as cursor:
                    await cursor.execute("SELECT case_id FROM cases WHERE case_id=%s FOR UPDATE", (case_id,))
                    if not await cursor.fetchone():
                        raise KeyError(case_id)
                    await cursor.execute(
                        "INSERT INTO verification_tasks (verification_task_id, case_id, claim, target, status, version, created_at, updated_at) VALUES (%s,%s,%s,%s,'PENDING',1,%s,%s)",
                        (verification_task_id, case_id, record["claim"], record["target"], now, now),
                    )
                    await cursor.execute(
                        "INSERT INTO case_events (case_id, event_type, actor_type, payload_json, occurred_at) VALUES (%s,'VERIFICATION_CREATED','BANK_STAFF',%s,%s)",
                        (case_id, json.dumps({"verification_task_id": verification_task_id}), now),
                    )
                    await cursor.execute("UPDATE cases SET updated_at=%s WHERE case_id=%s", (now, case_id))
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        return {"verification_task_id": verification_task_id, "case_id": case_id, **record, "status": "PENDING", "version": 1, "created_at": now.isoformat(), "updated_at": now.isoformat()}

    async def list_verifications(self, case_id: str) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as connection, connection.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SELECT verification_task_id, case_id, claim, target, status, version, created_at, updated_at FROM verification_tasks WHERE case_id=%s ORDER BY created_at, verification_task_id", (case_id,))
            return [{**row, "created_at": row["created_at"].isoformat(), "updated_at": row["updated_at"].isoformat()} for row in await cursor.fetchall()]

    async def update_verification(self, case_id: str, verification_task_id: str, expected_version: int, status: str) -> dict[str, Any]:
        pool = await self._get_pool()
        now = datetime.now()
        async with pool.acquire() as connection:
            try:
                async with connection.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute("SELECT version FROM verification_tasks WHERE case_id=%s AND verification_task_id=%s FOR UPDATE", (case_id, verification_task_id))
                    row = await cursor.fetchone()
                    if not row:
                        raise KeyError(verification_task_id)
                    current_version = int(row["version"])
                    if current_version != expected_version:
                        raise CaseVersionConflictError(current_version)
                    next_version = current_version + 1
                    await cursor.execute("UPDATE verification_tasks SET status=%s, version=%s, updated_at=%s WHERE case_id=%s AND verification_task_id=%s", (status, next_version, now, case_id, verification_task_id))
                    await cursor.execute("INSERT INTO case_events (case_id, event_type, actor_type, payload_json, occurred_at) VALUES (%s,'VERIFICATION_UPDATED','SYSTEM',%s,%s)", (case_id, json.dumps({"verification_task_id": verification_task_id, "status": status, "version": next_version}), now))
                    await cursor.execute("UPDATE cases SET updated_at=%s WHERE case_id=%s", (now, case_id))
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        tasks = await self.list_verifications(case_id)
        task = next((item for item in tasks if item["verification_task_id"] == verification_task_id), None)
        if task is None:
            raise KeyError(verification_task_id)
        return task

    async def create_action(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]:
        pool = await self._get_pool()
        action_id = f"act-{__import__('uuid').uuid4().hex}"
        now = datetime.now()
        async with pool.acquire() as connection:
            try:
                async with connection.cursor() as cursor:
                    await cursor.execute("SELECT case_id FROM cases WHERE case_id=%s FOR UPDATE", (case_id,))
                    if not await cursor.fetchone():
                        raise KeyError(case_id)
                    await cursor.execute(
                        "INSERT INTO actions (action_id, case_id, action_type, status, actor_type, note, created_at) VALUES (%s,%s,%s,'REQUESTED',%s,%s,%s)",
                        (action_id, case_id, record["action_type"], record["actor_type"], record["note"], now),
                    )
                    await cursor.execute(
                        "INSERT INTO case_events (case_id, event_type, actor_type, payload_json, occurred_at) VALUES (%s,'BANK_ACTION_ADDED',%s,%s,%s)",
                        (case_id, record["actor_type"], json.dumps({"action_id": action_id}), now),
                    )
                    await cursor.execute("UPDATE cases SET updated_at=%s WHERE case_id=%s", (now, case_id))
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        return {"action_id": action_id, "case_id": case_id, **record, "status": "REQUESTED", "created_at": now.isoformat()}

    async def list_actions(self, case_id: str) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as connection, connection.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SELECT action_id, case_id, action_type, status, actor_type, note, created_at FROM actions WHERE case_id=%s ORDER BY created_at, action_id", (case_id,))
            return [{**row, "created_at": row["created_at"].isoformat()} for row in await cursor.fetchall()]

    async def create_voice_session(self, case_id: str, participants: list[str]) -> dict[str, Any]:
        pool = await self._get_pool()
        from uuid import uuid4
        session_id = f"voice-{uuid4().hex}"
        now = datetime.now()
        async with pool.acquire() as connection:
            try:
                async with connection.cursor() as cursor:
                    await cursor.execute("SELECT case_id FROM cases WHERE case_id=%s FOR UPDATE", (case_id,))
                    if not await cursor.fetchone(): raise KeyError(case_id)
                    await cursor.execute("INSERT INTO voice_sessions (session_id, case_id, status, participants_json, created_at) VALUES (%s,%s,'REQUESTED',%s,%s)", (session_id, case_id, json.dumps(participants), now))
                    await cursor.execute("INSERT INTO case_events (case_id, event_type, actor_type, payload_json, occurred_at) VALUES (%s,'VOICE_SESSION_REQUESTED','SYSTEM',%s,%s)", (case_id, json.dumps({"session_id": session_id}), now))
                await connection.commit()
            except Exception:
                await connection.rollback(); raise
        return {"session_id": session_id, "case_id": case_id, "status": "REQUESTED", "participants": participants, "started_at": None, "ended_at": None, "created_at": now.isoformat()}

    async def update_voice_session(self, case_id: str, session_id: str, status: str) -> dict[str, Any]:
        pool = await self._get_pool()
        now = datetime.now()
        async with pool.acquire() as connection:
            try:
                async with connection.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute("SELECT * FROM voice_sessions WHERE case_id=%s AND session_id=%s FOR UPDATE", (case_id, session_id))
                    row = await cursor.fetchone()
                    if not row: raise KeyError(session_id)
                    started_at = row["started_at"] or (now if status == "ACTIVE" else None)
                    ended_at = now if status in {"ENDED", "FAILED"} else row["ended_at"]
                    await cursor.execute("UPDATE voice_sessions SET status=%s, started_at=%s, ended_at=%s WHERE case_id=%s AND session_id=%s", (status, started_at, ended_at, case_id, session_id))
                    await cursor.execute("INSERT INTO case_events (case_id, event_type, actor_type, payload_json, occurred_at) VALUES (%s,%s,'SYSTEM',%s,%s)", (case_id, f"VOICE_SESSION_{status}", json.dumps({"session_id": session_id}), now))
                await connection.commit()
            except Exception:
                await connection.rollback(); raise
        session = await self.get_voice_session(case_id, session_id)
        if session is None: raise KeyError(session_id)
        return session

    async def get_voice_session(self, case_id: str, session_id: str | None = None) -> dict[str, Any] | None:
        pool = await self._get_pool()
        query = "SELECT * FROM voice_sessions WHERE case_id=%s" + (" AND session_id=%s" if session_id else "") + " ORDER BY created_at DESC LIMIT 1"
        values = (case_id, session_id) if session_id else (case_id,)
        async with pool.acquire() as connection, connection.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(query, values); row = await cursor.fetchone()
        if not row: return None
        return {"session_id": row["session_id"], "case_id": row["case_id"], "status": row["status"], "participants": self._json(row["participants_json"]), "started_at": row["started_at"].isoformat() if row["started_at"] else None, "ended_at": row["ended_at"].isoformat() if row["ended_at"] else None, "created_at": row["created_at"].isoformat()}

    async def append_transcript(self, case_id: str, session_id: str, record: dict[str, Any]) -> dict[str, Any]:
        pool = await self._get_pool()
        from uuid import uuid4
        segment_id = f"seg-{uuid4().hex}"; now = datetime.now()
        async with pool.acquire() as connection:
            try:
                async with connection.cursor() as cursor:
                    await cursor.execute("SELECT session_id FROM voice_sessions WHERE case_id=%s AND session_id=%s", (case_id, session_id))
                    if not await cursor.fetchone(): raise KeyError(session_id)
                    started_at = datetime.fromisoformat(record["started_at"]).replace(tzinfo=None) if record.get("started_at") else None
                    await cursor.execute("INSERT INTO transcript_segments (segment_id, session_id, case_id, speaker, content, started_at, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s)", (segment_id, session_id, case_id, record["speaker"], record["content"], started_at, now))
                    await cursor.execute("INSERT INTO case_events (case_id, event_type, actor_type, payload_json, occurred_at) VALUES (%s,'TRANSCRIPT_SEGMENT_ADDED','SYSTEM',%s,%s)", (case_id, json.dumps({"session_id": session_id, "segment_id": segment_id}), now))
                await connection.commit()
            except Exception:
                await connection.rollback(); raise
        return {"segment_id": segment_id, "session_id": session_id, "case_id": case_id, **record, "created_at": now.isoformat()}

    async def list_transcript(self, case_id: str, session_id: str) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as connection, connection.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SELECT * FROM transcript_segments WHERE case_id=%s AND session_id=%s ORDER BY created_at, segment_id", (case_id, session_id)); rows = await cursor.fetchall()
        return [{"segment_id": row["segment_id"], "session_id": row["session_id"], "case_id": row["case_id"], "speaker": row["speaker"], "content": row["content"], "started_at": row["started_at"].isoformat() if row["started_at"] else None, "created_at": row["created_at"].isoformat()} for row in rows]

    async def finalize_report(self, case_id: str, expected_version: int, note: str) -> dict[str, Any]:
        pool = await self._get_pool()
        now = datetime.now()
        report_id = f"final-{case_id}"
        async with pool.acquire() as connection:
            try:
                async with connection.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute("SELECT version FROM cases WHERE case_id=%s FOR UPDATE", (case_id,)); case_row = await cursor.fetchone()
                    if not case_row: raise KeyError(case_id)
                    current_version = int(case_row["version"])
                    if current_version != expected_version: raise CaseVersionConflictError(current_version)
                    await cursor.execute("SELECT report_id, report_version FROM case_reports WHERE case_id=%s AND report_type='LIVE'", (case_id,)); live = await cursor.fetchone()
                    if not live: raise KeyError(case_id)
                    await cursor.execute("SELECT section_key, content_json, section_version FROM case_report_sections WHERE report_id=%s ORDER BY section_key", (live["report_id"],)); sections = await cursor.fetchall()
                    await cursor.execute("INSERT INTO case_reports (report_id, case_id, report_type, report_version, created_at, updated_at) VALUES (%s,%s,'FINAL',%s,%s,%s)", (report_id, case_id, live["report_version"], now, now))
                    for section in sections:
                        await cursor.execute("INSERT INTO case_report_sections (report_id, section_key, content_json, section_version, updated_at) VALUES (%s,%s,%s,%s,%s)", (report_id, section["section_key"], section["content_json"], section["section_version"], now))
                    next_version = current_version + 1
                    await cursor.execute("UPDATE cases SET mode='CLOSED', status='CLOSED', version=%s, updated_at=%s WHERE case_id=%s", (next_version, now, case_id))
                    await cursor.execute("INSERT INTO case_events (case_id, event_type, actor_type, payload_json, occurred_at) VALUES (%s,'CASE_REPORT_FINALIZED','BANK_STAFF',%s,%s)", (case_id, json.dumps({"report_id": report_id, "version": next_version, "note": note}), now))
                await connection.commit()
            except Exception:
                await connection.rollback(); raise
        return await self.get_final_report(case_id) or {"report_id": report_id, "case_id": case_id, "report_version": live["report_version"], "status": "FINAL", "sections": [], "created_at": now.isoformat()}

    async def get_final_report(self, case_id: str) -> dict[str, Any] | None:
        pool = await self._get_pool()
        async with pool.acquire() as connection, connection.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SELECT report_id, case_id, report_version, created_at FROM case_reports WHERE case_id=%s AND report_type='FINAL'", (case_id,)); report = await cursor.fetchone()
            if not report: return None
            await cursor.execute("SELECT section_key, content_json, section_version FROM case_report_sections WHERE report_id=%s ORDER BY section_key", (report["report_id"],)); sections = await cursor.fetchall()
        return {"report_id": report["report_id"], "case_id": report["case_id"], "report_version": report["report_version"], "status": "FINAL", "sections": [{"section_key": item["section_key"], "content": self._json(item["content_json"]), "version": item["section_version"]} for item in sections], "created_at": report["created_at"].isoformat()}

    @staticmethod
    def _json(value: Any) -> Any:
        return json.loads(value) if isinstance(value, (str, bytes, bytearray)) else value
