from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime
from typing import Any

import aiomysql


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
            "case_id": case_row["case_id"], "client_request_id": case_row["client_request_id"],
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
                           (case_id, client_request_id, risk_level, risk_score, mode, status, initial_brief, diagnosis_json, created_at, updated_at)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (record["case_id"], record.get("client_request_id"), record["risk"], record["risk_score"],
                         record["mode"], record["status"], record["initial_brief"], json.dumps(diagnosis, ensure_ascii=False),
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
                        "INSERT INTO case_events (case_id, event_type, payload_json, occurred_at) VALUES (%s,'CASE_CREATED',%s,%s)",
                        (record["case_id"], json.dumps({"report_id": report["report_id"]}), created_at),
                    )
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        return deepcopy(record)

    async def list(self) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as connection, connection.cursor() as cursor:
            await cursor.execute("SELECT case_id FROM cases ORDER BY created_at DESC")
            ids = [row[0] for row in await cursor.fetchall()]
        return [record for case_id in ids if (record := await self.get(case_id)) is not None]

    @staticmethod
    def _json(value: Any) -> Any:
        return json.loads(value) if isinstance(value, (str, bytes, bytearray)) else value
