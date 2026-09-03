"""Small persistent repository for local MVP demonstrations.

The production adapter remains MySQL.  This adapter deliberately uses Python's
built-in SQLite so a teammate can run the whole MVP without preparing MySQL.
It persists the same Case aggregates as the in-memory repository in one local
database file; no fixture or browser-only mock data is used.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from .repository import InMemoryCaseRepository


class LocalSqliteCaseRepository(InMemoryCaseRepository):
    _STATE_FIELDS = (
        "_records", "_messages", "_attachments", "_events", "_verifications", "_actions",
        "_voice_sessions", "_transcripts", "_members", "_presence", "_customer_questions", "_case_facts", "_personal_notes",
    )

    def __init__(self, database_path: str | None = None) -> None:
        super().__init__()
        default_path = Path(__file__).resolve().parents[4] / "data" / "mvp_v2.sqlite3"
        self._database_path = Path(database_path or os.getenv("LOCAL_SQLITE_PATH", str(default_path)))
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.execute("CREATE TABLE IF NOT EXISTS local_case_state (state_key TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        return connection

    def _load(self) -> None:
        with self._connection() as connection:
            row = connection.execute("SELECT payload FROM local_case_state WHERE state_key='case_repository'").fetchone()
        if not row:
            return
        state = json.loads(row[0])
        for field in self._STATE_FIELDS:
            setattr(self, field, state.get(field, []))

    def _persist(self) -> None:
        state = {field: getattr(self, field) for field in self._STATE_FIELDS}
        payload = json.dumps(state, ensure_ascii=False, separators=(",", ":"))
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO local_case_state (state_key, payload) VALUES ('case_repository', ?) "
                "ON CONFLICT(state_key) DO UPDATE SET payload=excluded.payload",
                (payload,),
            )

    async def create(self, record: dict[str, Any]) -> dict[str, Any]:
        result = await super().create(record); self._persist(); return result

    async def list(self) -> list[dict[str, Any]]:
        result = await super().list(); self._persist(); return result

    async def list_trashed_cases(self) -> list[dict[str, Any]]:
        result = await super().list_trashed_cases(); self._persist(); return result

    async def delete_case(self, case_id: str) -> None:
        await super().delete_case(case_id); self._persist()

    async def restore_case(self, case_id: str) -> None:
        await super().restore_case(case_id); self._persist()

    async def update_case(self, case_id: str, expected_version: int, changes: dict[str, Any]) -> dict[str, Any]:
        result = await super().update_case(case_id, expected_version, changes); self._persist(); return result

    async def append_message(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]:
        result = await super().append_message(case_id, record); self._persist(); return result

    async def create_attachment(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]:
        result = await super().create_attachment(case_id, record); self._persist(); return result

    async def upsert_member(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]:
        result = await super().upsert_member(case_id, record); self._persist(); return result

    async def set_primary_assignee(self, case_id: str, display_name: str | None) -> str | None:
        result = await super().set_primary_assignee(case_id, display_name); self._persist(); return result

    async def heartbeat_presence(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]:
        result = await super().heartbeat_presence(case_id, record); self._persist(); return result

    async def create_verification(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]:
        result = await super().create_verification(case_id, record); self._persist(); return result

    async def update_verification(self, case_id: str, verification_task_id: str, expected_version: int, status: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
        result = await super().update_verification(case_id, verification_task_id, expected_version, status, details); self._persist(); return result

    async def create_action(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]:
        result = await super().create_action(case_id, record); self._persist(); return result

    async def create_voice_session(self, case_id: str, participants: list[str]) -> dict[str, Any]:
        result = await super().create_voice_session(case_id, participants); self._persist(); return result

    async def update_voice_session(self, case_id: str, session_id: str, status: str) -> dict[str, Any]:
        result = await super().update_voice_session(case_id, session_id, status); self._persist(); return result

    async def append_transcript(self, case_id: str, session_id: str, record: dict[str, Any]) -> dict[str, Any]:
        result = await super().append_transcript(case_id, session_id, record); self._persist(); return result

    async def finalize_report(self, case_id: str, expected_version: int, note: str) -> dict[str, Any]:
        result = await super().finalize_report(case_id, expected_version, note); self._persist(); return result

    async def create_personal_note(self, case_id: str, author_id: str, content: str) -> dict[str, Any]:
        result = await super().create_personal_note(case_id, author_id, content); self._persist(); return result

    async def update_personal_note(self, case_id: str, note_id: str, author_id: str, content: str) -> dict[str, Any]:
        result = await super().update_personal_note(case_id, note_id, author_id, content); self._persist(); return result

    async def delete_personal_note(self, case_id: str, note_id: str, author_id: str) -> None:
        await super().delete_personal_note(case_id, note_id, author_id); self._persist()
