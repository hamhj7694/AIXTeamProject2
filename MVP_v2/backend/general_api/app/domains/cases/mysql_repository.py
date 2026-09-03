from __future__ import annotations

import json
import os
import uuid
from copy import deepcopy
from datetime import datetime, timedelta
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
                db=os.getenv("MYSQL_DATABASE", "aix_case_platform_mvp_v2"),
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

    async def next_case_id(self) -> str:
        pool = await self._get_pool()
        async with pool.acquire() as connection, connection.cursor() as cursor:
            await cursor.execute("SELECT case_id FROM cases WHERE case_id REGEXP '^VP-[0-9]+$'")
            values = [int(str(row[0]).removeprefix("VP-")) for row in await cursor.fetchall()]
        return f"VP-{max(values, default=0) + 1}"

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
            "victim_transfer_status": case_row.get("victim_transfer_status") or "UNKNOWN",
            "actual_loss_amount_krw": case_row.get("actual_loss_amount_krw"),
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

    async def delete_case(self, case_id: str) -> None:
        pool = await self._get_pool(); now = datetime.now()
        async with pool.acquire() as connection, connection.cursor() as cursor:
            await cursor.execute("UPDATE cases SET deleted_at=%s, updated_at=%s WHERE case_id=%s AND deleted_at IS NULL", (now, now, case_id))
            if cursor.rowcount == 0: raise KeyError(case_id)
            await connection.commit()

    async def list_trashed_cases(self) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as connection, connection.cursor() as cursor:
            await cursor.execute("SELECT case_id FROM cases WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC")
            ids = [row[0] for row in await cursor.fetchall()]
        return [record for case_id in ids if (record := await self.get(case_id)) is not None]

    async def restore_case(self, case_id: str) -> None:
        pool = await self._get_pool(); now = datetime.now()
        async with pool.acquire() as connection, connection.cursor() as cursor:
            await cursor.execute("UPDATE cases SET deleted_at=NULL, updated_at=%s WHERE case_id=%s AND deleted_at IS NOT NULL", (now, case_id))
            if cursor.rowcount == 0: raise KeyError(case_id)
            await connection.commit()

    async def append_message(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]:
        pool = await self._get_pool()
        message_id = f"msg-{__import__('uuid').uuid4().hex}"
        created_at = datetime.now()
        attachment_ids = list(dict.fromkeys(record.get("attachment_ids", [])))
        async with pool.acquire() as connection:
            try:
                async with connection.cursor() as cursor:
                    await cursor.execute("SELECT case_id FROM cases WHERE case_id=%s FOR UPDATE", (case_id,))
                    if not await cursor.fetchone():
                        raise KeyError(case_id)
                    if attachment_ids:
                        placeholders = ",".join(["%s"] * len(attachment_ids))
                        await cursor.execute(
                            f"SELECT attachment_id, status, visibility FROM case_attachments WHERE case_id=%s AND attachment_id IN ({placeholders}) FOR UPDATE",
                            (case_id, *attachment_ids),
                        )
                        attachment_rows = await cursor.fetchall()
                        expected_visibility = record.get("visibility", record.get("audience", "CUSTOMER"))
                        if len(attachment_rows) != len(attachment_ids) or any(row[1] != "UPLOADED" or row[2] != expected_visibility for row in attachment_rows):
                            raise ValueError("ATTACHMENT_NOT_FOUND")
                    await cursor.execute(
                        """INSERT INTO messages
                           (message_id, case_id, actor_type, actor_user_id, actor_display_name, actor_role, content, channel, audience, visibility, message_kind, private_owner_user_id, mentions_json, reply_to_message_id, client_request_id, attachments_json, created_at)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (
                            message_id, case_id, record["actor_type"], record.get("actor_user_id"), record.get("actor_display_name"), record.get("actor_role"), record["content"],
                            record.get("channel", "CUSTOMER"), record.get("audience", "CUSTOMER"),
                            record.get("visibility", "CUSTOMER"), record.get("message_kind", "CHAT"), record.get("private_owner_user_id"),
                            json.dumps(record.get("mentions", []), ensure_ascii=False), record.get("reply_to_message_id"),
                            record.get("client_request_id"), json.dumps(record.get("attachment_ids", []), ensure_ascii=False), created_at,
                        ),
                    )
                    if attachment_ids:
                        await cursor.executemany(
                            "INSERT INTO message_attachments (message_id, attachment_id, attached_at) VALUES (%s,%s,%s)",
                            [(message_id, attachment_id, created_at) for attachment_id in attachment_ids],
                        )
                        await cursor.execute(
                            f"UPDATE case_attachments SET status='LINKED' WHERE case_id=%s AND attachment_id IN ({','.join(['%s'] * len(attachment_ids))})",
                            (case_id, *attachment_ids),
                        )
                    if record.get("log_event"):
                        await cursor.execute(
                            "INSERT INTO case_events (case_id, event_type, actor_type, payload_json, occurred_at) VALUES (%s,'MESSAGE_ADDED',%s,%s,%s)",
                            (case_id, record["actor_type"], json.dumps({"message_id": message_id, "channel": record.get("channel", "CUSTOMER")}), created_at),
                        )
                    await cursor.execute("UPDATE cases SET updated_at=%s WHERE case_id=%s", (created_at, case_id))
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        attachments = [item for item in [await self.get_attachment(case_id, attachment_id) for attachment_id in attachment_ids] if item]
        return {
            "message_id": message_id, "case_id": case_id, **record,
            "channel": record.get("channel", "CUSTOMER"), "audience": record.get("audience", "CUSTOMER"),
            "mentions": record.get("mentions", []), "reply_to_message_id": record.get("reply_to_message_id"),
            "attachment_ids": attachment_ids, "attachments": attachments,
            "created_at": created_at.isoformat(),
        }

    async def list_messages(self, case_id: str, channel: str | None = None) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        query = "SELECT message_id, case_id, actor_type, actor_user_id, actor_display_name, actor_role, content, channel, audience, visibility, message_kind, private_owner_user_id, mentions_json, reply_to_message_id, attachments_json, created_at FROM messages WHERE case_id=%s"
        values: tuple[Any, ...] = (case_id,)
        if channel is not None:
            query += " AND channel=%s"
            values += (channel,)
        query += " ORDER BY created_at, message_id"
        async with pool.acquire() as connection, connection.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(query, values)
            messages = [
                {**row, "mentions": self._json(row["mentions_json"]) or [], "created_at": row["created_at"].isoformat()}
                for row in await cursor.fetchall()
            ]
            for message in messages:
                await cursor.execute(
                    """SELECT a.* FROM case_attachments a
                       INNER JOIN message_attachments ma ON ma.attachment_id=a.attachment_id
                       WHERE ma.message_id=%s ORDER BY ma.attached_at, a.attachment_id""",
                    (message["message_id"],),
                )
                message["attachments"] = [
                    {**row, "size_bytes": int(row["size_bytes"]), "ai_readable": bool(row["ai_readable"]), "created_at": row["created_at"].isoformat()}
                    for row in await cursor.fetchall()
                ]
                message["attachment_ids"] = [item["attachment_id"] for item in message["attachments"]]
            return messages

    async def create_attachment(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]:
        pool = await self._get_pool()
        attachment_id = f"att-{uuid.uuid4().hex}"
        created_at = datetime.fromisoformat(record["created_at"]).replace(tzinfo=None)
        async with pool.acquire() as connection:
            try:
                async with connection.cursor() as cursor:
                    await cursor.execute("SELECT case_id FROM cases WHERE case_id=%s", (case_id,))
                    if not await cursor.fetchone():
                        raise KeyError(case_id)
                    await cursor.execute(
                        """INSERT INTO case_attachments
                           (attachment_id, case_id, original_name, stored_name, storage_path, mime_type, size_bytes, sha256, uploaded_by, status, visibility, ai_readable, created_at)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (attachment_id, case_id, record["original_name"], record["stored_name"], record["storage_path"], record["mime_type"],
                         record["size_bytes"], record["sha256"], record["uploaded_by"], record.get("status", "UPLOADED"),
                         record.get("visibility", "CUSTOMER"), bool(record.get("ai_readable", True)), created_at),
                    )
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        return {"attachment_id": attachment_id, "case_id": case_id, **record}

    async def get_attachment(self, case_id: str, attachment_id: str) -> dict[str, Any] | None:
        pool = await self._get_pool()
        async with pool.acquire() as connection, connection.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SELECT * FROM case_attachments WHERE case_id=%s AND attachment_id=%s", (case_id, attachment_id))
            row = await cursor.fetchone()
        return {**row, "size_bytes": int(row["size_bytes"]), "ai_readable": bool(row["ai_readable"]), "created_at": row["created_at"].isoformat()} if row else None

    async def list_attachments(self, case_id: str) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as connection, connection.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SELECT * FROM case_attachments WHERE case_id=%s ORDER BY created_at, attachment_id", (case_id,))
            return [
                {**row, "size_bytes": int(row["size_bytes"]), "ai_readable": bool(row["ai_readable"]), "created_at": row["created_at"].isoformat()}
                for row in await cursor.fetchall()
            ]

    async def list_members(self, case_id: str) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as connection, connection.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(
                "SELECT case_id, user_id, display_name, role, status, assigned_at, updated_at FROM case_members WHERE case_id=%s AND status='ACTIVE' ORDER BY assigned_at, user_id",
                (case_id,),
            )
            return [{**row, "assigned_at": row["assigned_at"].isoformat(), "updated_at": row["updated_at"].isoformat()} for row in await cursor.fetchall()]

    async def upsert_member(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]:
        pool = await self._get_pool()
        now = datetime.now()
        async with pool.acquire() as connection:
            try:
                async with connection.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute("SELECT case_id FROM cases WHERE case_id=%s FOR UPDATE", (case_id,))
                    if not await cursor.fetchone():
                        raise KeyError(case_id)
                    await cursor.execute(
                        """INSERT INTO case_members (case_id, user_id, display_name, role, status, assigned_at, updated_at)
                           VALUES (%s,%s,%s,%s,'ACTIVE',%s,%s)
                           ON DUPLICATE KEY UPDATE display_name=VALUES(display_name), role=VALUES(role), status='ACTIVE', updated_at=VALUES(updated_at)""",
                        (case_id, record["user_id"], record["display_name"], record["role"], now, now),
                    )
                    await cursor.execute(
                        "INSERT INTO case_events (case_id, event_type, actor_type, payload_json, occurred_at) VALUES (%s,'CASE_MEMBER_UPDATED','SYSTEM',%s,%s)",
                        (case_id, json.dumps({"user_id": record["user_id"], "role": record["role"]}), now),
                    )
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        members = await self.list_members(case_id)
        return next(item for item in members if item["user_id"] == record["user_id"])

    async def set_primary_assignee(self, case_id: str, display_name: str | None) -> str | None:
        pool = await self._get_pool()
        normalized = (display_name or "").strip()
        now = datetime.now()
        async with pool.acquire() as connection:
            try:
                async with connection.cursor() as cursor:
                    await cursor.execute("SELECT case_id FROM cases WHERE case_id=%s FOR UPDATE", (case_id,))
                    if not await cursor.fetchone():
                        raise KeyError(case_id)
                    await cursor.execute("UPDATE case_members SET role='VIEWER', updated_at=%s WHERE case_id=%s AND role='CASE_OWNER'", (now, case_id))
                    if normalized:
                        await cursor.execute("SELECT user_id FROM case_members WHERE case_id=%s AND display_name=%s LIMIT 1", (case_id, normalized))
                        existing = await cursor.fetchone()
                        if existing:
                            await cursor.execute("UPDATE case_members SET role='CASE_OWNER', status='ACTIVE', updated_at=%s WHERE case_id=%s AND user_id=%s", (now, case_id, existing[0]))
                        else:
                            user_id = f"owner-{uuid.uuid4().hex}"
                            await cursor.execute(
                                "INSERT INTO case_members (case_id,user_id,display_name,role,status,assigned_at,updated_at) VALUES (%s,%s,%s,'CASE_OWNER','ACTIVE',%s,%s)",
                                (case_id, user_id, normalized, now, now),
                            )
                    await cursor.execute(
                        "INSERT INTO case_events (case_id,event_type,actor_type,payload_json,occurred_at) VALUES (%s,'CASE_ASSIGNEE_UPDATED','SYSTEM',%s,%s)",
                        (case_id, json.dumps({"display_name": normalized or None}, ensure_ascii=False), now),
                    )
                    await cursor.execute("UPDATE cases SET updated_at=%s WHERE case_id=%s", (now, case_id))
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        return normalized or None

    async def list_presence(self, case_id: str) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as connection, connection.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(
                "SELECT case_id, user_id, display_name, presence, channel, last_seen_at, expires_at FROM case_presence WHERE case_id=%s AND expires_at > NOW(6) ORDER BY last_seen_at DESC",
                (case_id,),
            )
            return [{**row, "last_seen_at": row["last_seen_at"].isoformat(), "expires_at": row["expires_at"].isoformat()} for row in await cursor.fetchall()]

    async def heartbeat_presence(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]:
        pool = await self._get_pool()
        now = datetime.now()
        expires_at = now + timedelta(seconds=45)
        async with pool.acquire() as connection:
            try:
                async with connection.cursor() as cursor:
                    await cursor.execute("SELECT case_id FROM cases WHERE case_id=%s", (case_id,))
                    if not await cursor.fetchone():
                        raise KeyError(case_id)
                    await cursor.execute(
                        """INSERT INTO case_presence (case_id, user_id, display_name, presence, channel, last_seen_at, expires_at)
                           VALUES (%s,%s,%s,%s,%s,%s,%s)
                           ON DUPLICATE KEY UPDATE display_name=VALUES(display_name), presence=VALUES(presence), channel=VALUES(channel), last_seen_at=VALUES(last_seen_at), expires_at=VALUES(expires_at)""",
                        (case_id, record["user_id"], record["display_name"], record["presence"], record["channel"], now, expires_at),
                    )
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        return {"case_id": case_id, **record, "last_seen_at": now.isoformat(), "expires_at": expires_at.isoformat()}

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
            await cursor.execute("SELECT verification_task_id, case_id, claim, target, status, version, result_summary, evidence_url, verified_by, rag_source, customer_visible, created_at, updated_at FROM verification_tasks WHERE case_id=%s ORDER BY created_at, verification_task_id", (case_id,))
            return [{**row, "created_at": row["created_at"].isoformat(), "updated_at": row["updated_at"].isoformat()} for row in await cursor.fetchall()]

    async def update_verification(self, case_id: str, verification_task_id: str, expected_version: int, status: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
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
                    details = details or {}
                    await cursor.execute("UPDATE verification_tasks SET status=%s, result_summary=%s, evidence_url=%s, verified_by=%s, rag_source=%s, customer_visible=COALESCE(%s, customer_visible), version=%s, updated_at=%s WHERE case_id=%s AND verification_task_id=%s", (status, details.get("result_summary"), details.get("evidence_url"), details.get("verified_by"), details.get("rag_source"), details.get("customer_visible"), next_version, now, case_id, verification_task_id))
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

    async def create_attachment(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]:
        pool = await self._get_pool(); attachment_id = f"att-{uuid.uuid4().hex}"; now = datetime.now()
        async with pool.acquire() as connection:
            try:
                async with connection.cursor() as cursor:
                    await cursor.execute("SELECT case_id FROM cases WHERE case_id=%s", (case_id,))
                    if not await cursor.fetchone(): raise KeyError(case_id)
                    await cursor.execute("INSERT INTO attachments (attachment_id,case_id,original_name,mime_type,size_bytes,sha256,uploaded_by,status,ai_readable,storage_key,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (attachment_id, case_id, record["original_name"], record["mime_type"], record["size_bytes"], record["sha256"], record["uploaded_by"], record.get("status", "UPLOADED"), record.get("ai_readable", True), record.get("storage_key"), now))
                await connection.commit()
            except Exception: await connection.rollback(); raise
        return {"attachment_id": attachment_id, "case_id": case_id, **record, "status": record.get("status", "UPLOADED"), "ai_readable": record.get("ai_readable", True), "created_at": now.isoformat()}

    async def get_attachment(self, case_id: str, attachment_id: str) -> dict[str, Any] | None:
        pool = await self._get_pool()
        async with pool.acquire() as connection, connection.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SELECT * FROM attachments WHERE case_id=%s AND attachment_id=%s", (case_id, attachment_id)); row = await cursor.fetchone()
        if not row: return None
        return {**row, "created_at": row["created_at"].isoformat()}

    async def list_attachments(self, case_id: str) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as connection, connection.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SELECT * FROM attachments WHERE case_id=%s ORDER BY created_at, attachment_id", (case_id,)); rows = await cursor.fetchall()
        return [{**row, "created_at": row["created_at"].isoformat()} for row in rows]

    async def list_customer_questions(self, case_id: str) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as connection, connection.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SELECT * FROM customer_questions WHERE case_id=%s ORDER BY sequence, question_id", (case_id,)); rows = await cursor.fetchall()
        return [self._question_row(row) for row in rows]

    async def queue_customer_questions(self, case_id: str, questions: list[dict[str, Any]], requested_by: str) -> list[dict[str, Any]]:
        pool = await self._get_pool(); now = datetime.now(); created_ids: list[str] = []
        async with pool.acquire() as connection:
            try:
                async with connection.cursor() as cursor:
                    await cursor.execute("SELECT COALESCE(MAX(sequence),0) FROM customer_questions WHERE case_id=%s", (case_id,)); sequence = int((await cursor.fetchone())[0])
                    await cursor.execute("SELECT target_field FROM customer_questions WHERE case_id=%s AND status IN ('PENDING','ASKED','ANSWERED')", (case_id,)); active_fields = {row[0] for row in await cursor.fetchall()}
                    for question in questions:
                        if question["target_field"] in active_fields:
                            continue
                        sequence += 1; qid = question.get("question_id") or f"question-{uuid.uuid4().hex}"
                        created_ids.append(qid)
                        active_fields.add(question["target_field"])
                        await cursor.execute("INSERT INTO customer_questions (question_id,case_id,source,target_field,question_text,reason,priority,status,sequence,requested_by,options_json,created_at) VALUES (%s,%s,'BANK_SELECTED',%s,%s,%s,%s,'PENDING',%s,%s,%s,%s)", (qid, case_id, question["target_field"], question["question_text"], question["reason"], question["priority"], sequence, requested_by, json.dumps(question.get("options", []), ensure_ascii=False), now))
                    if created_ids:
                        await cursor.execute("INSERT INTO case_events (case_id,event_type,actor_type,payload_json,occurred_at) VALUES (%s,'CUSTOMER_QUESTIONS_QUEUED','BANK_STAFF',%s,%s)", (case_id, json.dumps({"question_ids": created_ids}), now))
                        await cursor.execute("UPDATE cases SET updated_at=%s WHERE case_id=%s", (now, case_id))
                await connection.commit()
            except Exception: await connection.rollback(); raise
        all_items = await self.list_customer_questions(case_id)
        return [item for item in all_items if item["question_id"] in created_ids]

    async def dispatch_next_customer_question(self, case_id: str) -> dict[str, Any] | None:
        pool = await self._get_pool(); now = datetime.now()
        async with pool.acquire() as connection:
            try:
                async with connection.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute("SELECT * FROM customer_questions WHERE case_id=%s AND status='PENDING' ORDER BY sequence LIMIT 1 FOR UPDATE", (case_id,)); row = await cursor.fetchone()
                    if not row: await connection.commit(); return None
                    await cursor.execute("UPDATE customer_questions SET status='ASKED', asked_at=%s WHERE question_id=%s", (now, row["question_id"]))
                    await cursor.execute("INSERT INTO case_events (case_id,event_type,actor_type,payload_json,occurred_at) VALUES (%s,'CUSTOMER_QUESTION_DISPATCHED','CUSTOMER_AGENT',%s,%s)", (case_id, json.dumps({"question_id": row["question_id"]}), now))
                    await cursor.execute("UPDATE cases SET updated_at=%s WHERE case_id=%s", (now, case_id))
                await connection.commit()
            except Exception: await connection.rollback(); raise
        row["status"] = "ASKED"; row["asked_at"] = now; return self._question_row(row)

    async def answer_customer_question(self, case_id: str, question_id: str, message_id: str) -> dict[str, Any]:
        pool = await self._get_pool(); now = datetime.now()
        async with pool.acquire() as connection:
            try:
                async with connection.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute("SELECT * FROM customer_questions WHERE case_id=%s AND question_id=%s FOR UPDATE", (case_id, question_id)); row = await cursor.fetchone()
                    if not row or row["status"] != "ASKED": raise KeyError(question_id)
                    await cursor.execute("UPDATE customer_questions SET status='ANSWERED', answered_at=%s, answer_message_id=%s WHERE case_id=%s AND question_id=%s", (now, message_id, case_id, question_id))
                    await cursor.execute("INSERT INTO case_events (case_id,event_type,actor_type,payload_json,occurred_at) VALUES (%s,'CUSTOMER_QUESTION_ANSWERED','CUSTOMER',%s,%s)", (case_id, json.dumps({"question_id": question_id, "message_id": message_id}), now))
                    await cursor.execute("UPDATE cases SET updated_at=%s WHERE case_id=%s", (now, case_id))
                await connection.commit()
            except Exception: await connection.rollback(); raise
        row["status"] = "ANSWERED"; row["answered_at"] = now; row["answer_message_id"] = message_id; return self._question_row(row)

    async def list_case_facts(self, case_id: str) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as connection, connection.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SELECT * FROM case_facts WHERE case_id=%s ORDER BY created_at, fact_id", (case_id,)); rows = await cursor.fetchall()
        return [self._fact_row(row) for row in rows]

    async def propose_case_fact(self, case_id: str, question_id: str, value: str, evidence_message_id: str | None) -> dict[str, Any]:
        pool = await self._get_pool(); now = datetime.now()
        async with pool.acquire() as connection:
            try:
                async with connection.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute("SELECT target_field FROM customer_questions WHERE case_id=%s AND question_id=%s", (case_id, question_id)); question = await cursor.fetchone()
                    if not question: raise KeyError(question_id)
                    await cursor.execute("SELECT * FROM case_facts WHERE case_id=%s AND field_name=%s AND status='PROPOSED' LIMIT 1 FOR UPDATE", (case_id, question["target_field"])); fact = await cursor.fetchone()
                    if fact:
                        await cursor.execute("UPDATE case_facts SET value=%s,evidence_message_id=%s WHERE fact_id=%s", (value, evidence_message_id, fact["fact_id"]))
                    else:
                        fact_id = f"fact-{uuid.uuid4().hex}"; await cursor.execute("INSERT INTO case_facts (fact_id,case_id,field_name,value,source,status,confidence,evidence_message_id,created_at) VALUES (%s,%s,%s,%s,'AI_EXTRACTED','PROPOSED',0.7000,%s,%s)", (fact_id, case_id, question["target_field"], value, evidence_message_id, now)); fact = {"fact_id": fact_id, "case_id": case_id, "field_name": question["target_field"], "value": value, "source": "AI_EXTRACTED", "status": "PROPOSED", "confidence": 0.7, "evidence_message_id": evidence_message_id, "created_at": now}
                    await cursor.execute("INSERT INTO case_events (case_id,event_type,actor_type,payload_json,occurred_at) VALUES (%s,'CASE_FACT_PROPOSED','CUSTOMER_AGENT',%s,%s)", (case_id, json.dumps({"fact_id": fact["fact_id"], "field": question["target_field"]}), now))
                    await cursor.execute("UPDATE cases SET updated_at=%s WHERE case_id=%s", (now, case_id))
                await connection.commit()
            except Exception: await connection.rollback(); raise
        return self._fact_row(fact)

    async def confirm_case_fact(self, case_id: str, fact_id: str, confirmed_by: str) -> dict[str, Any]:
        pool = await self._get_pool(); now = datetime.now()
        async with pool.acquire() as connection:
            try:
                async with connection.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute("SELECT * FROM case_facts WHERE case_id=%s AND fact_id=%s FOR UPDATE", (case_id, fact_id)); fact = await cursor.fetchone()
                    if not fact: raise KeyError(fact_id)
                    await cursor.execute("UPDATE case_facts SET status='CONFIRMED',source='HUMAN_CONFIRMED',confirmed_by=%s,confirmed_at=%s WHERE case_id=%s AND fact_id=%s", (confirmed_by, now, case_id, fact_id))
                    await cursor.execute("INSERT INTO case_events (case_id,event_type,actor_type,payload_json,occurred_at) VALUES (%s,'CASE_FACT_CONFIRMED','BANK_STAFF',%s,%s)", (case_id, json.dumps({"fact_id": fact_id}), now))
                    await cursor.execute("UPDATE cases SET updated_at=%s WHERE case_id=%s", (now, case_id))
                await connection.commit()
            except Exception: await connection.rollback(); raise
        fact["status"] = "CONFIRMED"; fact["source"] = "HUMAN_CONFIRMED"; fact["confirmed_by"] = confirmed_by; fact["confirmed_at"] = now; return self._fact_row(fact)

    async def list_personal_notes(self, case_id: str, author_id: str) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as connection, connection.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SELECT * FROM personal_notes WHERE case_id=%s AND author_id=%s ORDER BY updated_at DESC", (case_id, author_id)); rows = await cursor.fetchall()
        return [{**row, "created_at": row["created_at"].isoformat(), "updated_at": row["updated_at"].isoformat()} for row in rows]

    async def create_personal_note(self, case_id: str, author_id: str, content: str) -> dict[str, Any]:
        pool = await self._get_pool(); note_id = f"note-{uuid.uuid4().hex}"; now = datetime.now()
        async with pool.acquire() as connection:
            try:
                async with connection.cursor() as cursor: await cursor.execute("INSERT INTO personal_notes (note_id,case_id,author_id,content,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s)", (note_id, case_id, author_id, content, now, now))
                await connection.commit()
            except Exception: await connection.rollback(); raise
        return {"note_id": note_id, "case_id": case_id, "author_id": author_id, "content": content, "visibility": "PRIVATE_TO_AUTHOR", "created_at": now.isoformat(), "updated_at": now.isoformat()}

    async def update_personal_note(self, case_id: str, note_id: str, author_id: str, content: str) -> dict[str, Any]:
        pool = await self._get_pool(); now = datetime.now()
        async with pool.acquire() as connection, connection.cursor() as cursor:
            await cursor.execute("UPDATE personal_notes SET content=%s,updated_at=%s WHERE case_id=%s AND note_id=%s AND author_id=%s", (content, now, case_id, note_id, author_id));
            if cursor.rowcount == 0: raise KeyError(note_id)
            await connection.commit()
        return {"note_id": note_id, "case_id": case_id, "author_id": author_id, "content": content, "visibility": "PRIVATE_TO_AUTHOR", "updated_at": now.isoformat(), "created_at": now.isoformat()}

    async def delete_personal_note(self, case_id: str, note_id: str, author_id: str) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as connection, connection.cursor() as cursor:
            await cursor.execute("DELETE FROM personal_notes WHERE case_id=%s AND note_id=%s AND author_id=%s", (case_id, note_id, author_id))
            if cursor.rowcount == 0: raise KeyError(note_id)
            await connection.commit()

    def _question_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {"question_id": row["question_id"], "case_id": row["case_id"], "source": row["source"], "target_field": row["target_field"], "question_text": row["question_text"], "reason": row["reason"], "priority": row["priority"], "status": row["status"], "sequence": row["sequence"], "requested_by": row.get("requested_by"), "asked_at": row["asked_at"].isoformat() if row.get("asked_at") else None, "answered_at": row["answered_at"].isoformat() if row.get("answered_at") else None, "options": self._json(row.get("options_json")) or [], "question_message_id": row.get("question_message_id"), "answer_message_id": row.get("answer_message_id")}

    def _fact_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {"fact_id": row["fact_id"], "case_id": row["case_id"], "field": row.get("field", row.get("field_name")), "value": row["value"], "source": row["source"], "status": row["status"], "confidence": float(row["confidence"]), "evidence_message_id": row.get("evidence_message_id"), "confirmed_by": row.get("confirmed_by"), "confirmed_at": row["confirmed_at"].isoformat() if row.get("confirmed_at") else None, "created_at": row["created_at"].isoformat() if hasattr(row.get("created_at"), "isoformat") else row["created_at"]}

    @staticmethod
    def _json(value: Any) -> Any:
        return json.loads(value) if isinstance(value, (str, bytes, bytearray)) else value
