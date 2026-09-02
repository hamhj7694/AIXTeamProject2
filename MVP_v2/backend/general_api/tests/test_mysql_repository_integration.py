from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pymysql

from ai_api.app.domains.diagnosis import DiagnosisService
from general_api.app.domains.cases.initial_report import InitialReportBuilder
from general_api.app.domains.cases.mysql_repository import MySqlCaseRepository
from general_api.app.domains.cases.repository import InMemoryCaseRepository
from general_api.app.main import build_repository


BACKEND_DIR = Path(__file__).resolve().parents[2]


def mysql_test_environment(database: str) -> dict[str, str]:
    required = ("MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD")
    if not all(os.getenv(key) for key in required):
        raise unittest.SkipTest("MySQL 통합 테스트 환경변수가 설정되지 않았습니다.")
    environment = os.environ.copy()
    environment.update({
        "MYSQL_DATABASE": database,
        "CASE_REPOSITORY": "mysql",
        "DIAGNOSIS_EXTRACTOR_MODE": "fixture",
    })
    return environment


class MySqlCaseRepositoryIntegrationTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.database = f"aix_case_platform_a0_test_{uuid4().hex[:12]}"
        cls.environment = mysql_test_environment(cls.database)
        for _ in range(2):
            subprocess.run(
                [sys.executable, "scripts/apply_migrations.py"],
                cwd=BACKEND_DIR,
                env=cls.environment,
                check=True,
                capture_output=True,
                text=True,
            )

    @classmethod
    def tearDownClass(cls) -> None:
        connection = pymysql.connect(
            host=cls.environment["MYSQL_HOST"],
            port=int(cls.environment.get("MYSQL_PORT", "3306")),
            user=cls.environment["MYSQL_USER"],
            password=cls.environment["MYSQL_PASSWORD"],
            autocommit=True,
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"DROP DATABASE IF EXISTS `{cls.database}`")
        finally:
            connection.close()

    async def asyncSetUp(self) -> None:
        self.environment_patch = patch.dict(os.environ, self.environment, clear=False)
        self.environment_patch.start()
        self.repository = MySqlCaseRepository()
        self.case_ids: list[str] = []

    async def asyncTearDown(self) -> None:
        try:
            await self._delete_created_cases()
        finally:
            await self.repository.close()
            self.environment_patch.stop()

    async def _delete_created_cases(self) -> None:
        if not self.case_ids:
            return
        connection = pymysql.connect(
            host=self.environment["MYSQL_HOST"],
            port=int(self.environment.get("MYSQL_PORT", "3306")),
            user=self.environment["MYSQL_USER"],
            password=self.environment["MYSQL_PASSWORD"],
            database=self.database,
            autocommit=False,
        )
        try:
            with connection.cursor() as cursor:
                placeholders = ",".join(["%s"] * len(self.case_ids))
                cursor.execute(
                    f"DELETE FROM case_report_sections WHERE report_id IN "
                    f"(SELECT report_id FROM case_reports WHERE case_id IN ({placeholders}))",
                    self.case_ids,
                )
                for table in ("messages", "verification_tasks", "actions", "context_features", "analysis_segments", "case_inputs", "case_events", "case_reports"):
                    cursor.execute(f"DELETE FROM {table} WHERE case_id IN ({placeholders})", self.case_ids)
                cursor.execute(f"DELETE FROM cases WHERE case_id IN ({placeholders})", self.case_ids)
            connection.commit()
        finally:
            connection.close()

    async def test_migrations_create_expected_core_schema(self) -> None:
        connection = pymysql.connect(
            host=self.environment["MYSQL_HOST"],
            port=int(self.environment.get("MYSQL_PORT", "3306")),
            user=self.environment["MYSQL_USER"],
            password=self.environment["MYSQL_PASSWORD"],
            database=self.database,
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                self.assertEqual(
                    {row[0] for row in cursor.fetchall()},
                    {
                        "actions", "analysis_segments", "case_events", "case_inputs", "case_report_sections", "messages", "verification_tasks",
                        "case_reports", "cases", "context_features", "schema_migrations", "voice_sessions", "transcript_segments",
                    },
                )
                cursor.execute(
                    """SELECT NUMERIC_PRECISION, NUMERIC_SCALE
                       FROM information_schema.columns
                       WHERE table_schema=%s AND table_name='cases' AND column_name='risk_score'""",
                    (self.database,),
                )
                self.assertEqual(cursor.fetchone(), (9, 6))
        finally:
            connection.close()

    async def _record(self, *, case_id: str, client_request_id: str) -> dict:
        diagnosis = await DiagnosisService().analyze("검찰청입니다. 지금 안전계좌로 500만원을 송금하세요.")
        diagnosis = diagnosis.model_copy(update={"case_id": case_id})
        report = InitialReportBuilder().build(case_id, diagnosis)
        now = datetime.now(timezone.utc).isoformat()
        return {
            "case_id": case_id,
            "client_request_id": client_request_id,
            "input_text": "검찰청입니다. 지금 안전계좌로 500만원을 송금하세요.",
            "risk": diagnosis.risk_level.value,
            "risk_score": diagnosis.risk_score,
            "mode": "PREVENT",
            "status": "TRIAGE",
            "initial_brief": diagnosis.context.summary,
            "diagnosis": diagnosis.model_dump(mode="json"),
            "initial_report": report.model_dump(mode="json"),
            "created_at": now,
            "updated_at": now,
        }

    async def test_create_list_get_and_idempotency_lookup(self) -> None:
        case_id = f"A0-{uuid4().hex[:12].upper()}"
        self.case_ids.append(case_id)
        record = await self._record(case_id=case_id, client_request_id=f"a0-{uuid4().hex}")

        await self.repository.create(record)
        fetched = await self.repository.get(case_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["case_id"], case_id)
        self.assertEqual(fetched["risk"], "HIGH")
        self.assertEqual(len(fetched["initial_report"]["sections"]), 7)
        self.assertEqual((await self.repository.find_by_client_request_id(record["client_request_id"]))["case_id"], case_id)
        self.assertIn(case_id, [item["case_id"] for item in await self.repository.list()])

    async def test_failed_create_rolls_back_all_rows(self) -> None:
        case_id = f"A0-{uuid4().hex[:12].upper()}"
        self.case_ids.append(case_id)
        record = await self._record(case_id=case_id, client_request_id=f"a0-{uuid4().hex}")
        broken = deepcopy(record)
        broken["diagnosis"]["features"] = {"invalid_feature": "not-a-number"}

        with self.assertRaises((TypeError, ValueError)):
            await self.repository.create(broken)
        self.assertIsNone(await self.repository.get(case_id))

    async def test_message_append_and_event_cursor(self) -> None:
        case_id = f"A3-{uuid4().hex[:12].upper()}"
        self.case_ids.append(case_id)
        await self.repository.create(await self._record(case_id=case_id, client_request_id=f"a3-{uuid4().hex}"))

        message = await self.repository.append_message(case_id, {"actor_type": "CUSTOMER", "content": "송금하지 않았습니다."})
        messages = await self.repository.list_messages(case_id)
        events = await self.repository.list_events(case_id)

        self.assertEqual(messages[0]["message_id"], message["message_id"])
        self.assertEqual(messages[0]["content"], "송금하지 않았습니다.")
        self.assertEqual(events[-1]["event_type"], "MESSAGE_ADDED")
        self.assertEqual(events[-1]["actor_type"], "CUSTOMER")
        self.assertEqual(await self.repository.list_events(case_id, events[-2]["event_id"]), [events[-1]])

    async def test_verification_and_action_append_events(self) -> None:
        case_id = f"A4-{uuid4().hex[:12].upper()}"
        self.case_ids.append(case_id)
        await self.repository.create(await self._record(case_id=case_id, client_request_id=f"a4-{uuid4().hex}"))

        verification = await self.repository.create_verification(case_id, {"claim": "기관 사칭", "target": "검찰청"})
        action = await self.repository.create_action(case_id, {"action_type": "HUMAN_TAKEOVER", "actor_type": "BANK_STAFF", "note": "담당자 검토 요청"})

        self.assertEqual((await self.repository.list_verifications(case_id))[0]["verification_task_id"], verification["verification_task_id"])
        self.assertEqual((await self.repository.list_actions(case_id))[0]["action_id"], action["action_id"])
        self.assertEqual([event["event_type"] for event in await self.repository.list_events(case_id)][-2:], ["VERIFICATION_CREATED", "BANK_ACTION_ADDED"])


class RepositorySelectionTest(unittest.TestCase):
    def test_memory_and_mysql_repository_selection(self) -> None:
        with patch.dict(os.environ, {"CASE_REPOSITORY": "memory"}, clear=False):
            self.assertIsInstance(build_repository(), InMemoryCaseRepository)
        with patch.dict(os.environ, {"CASE_REPOSITORY": "mysql"}, clear=False):
            self.assertIsInstance(build_repository(), MySqlCaseRepository)


if __name__ == "__main__":
    unittest.main()
