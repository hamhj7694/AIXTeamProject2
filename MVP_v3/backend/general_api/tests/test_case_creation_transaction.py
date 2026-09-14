"""Exercise the real SQL repository's commit/rollback boundary without touching a DB."""
import unittest
from unittest.mock import AsyncMock, MagicMock

from pymysql.err import IntegrityError
from general_api.app.domains.cases.mysql_repository import MySqlCaseRepository
from general_api.app.domains.cases.repository import CaseCreationConflictError


class CreationTransactionTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.cursor = AsyncMock()
        self.connection = MagicMock()
        self.connection.cursor.return_value.__aenter__ = AsyncMock(return_value=self.cursor)
        self.connection.cursor.return_value.__aexit__ = AsyncMock(return_value=False)
        self.connection.commit = AsyncMock()
        self.connection.rollback = AsyncMock()
        pool = MagicMock()
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=self.connection)
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        self.repository = MySqlCaseRepository()
        self.repository._get_pool = AsyncMock(return_value=pool)
        self.record = {
            "case_id": "VP-TEST", "risk": "HIGH", "risk_score": 99,
            "mode": "PREVENT", "status": "TRIAGE", "initial_brief": "테스트",
            "input_text": "", "created_at": "2026-09-05T00:00:00+00:00",
            "updated_at": "2026-09-05T00:00:00+00:00",
            "diagnosis": {"windows": [], "features": {}},
            "initial_report": {"report_id": "live-VP-TEST", "report_version": 1,
                               "sections": [{"section_key": "summary", "content": {}, "version": 1}]},
        }

    async def test_case_precedes_children_and_commit_precedes_success(self):
        result = await self.repository.create(self.record)
        tables = [call.args[0].split()[2] for call in self.cursor.execute.await_args_list]
        self.assertEqual(tables, ["cases", "case_inputs", "case_reports", "case_report_sections", "case_events"])
        self.connection.commit.assert_awaited_once()
        self.connection.rollback.assert_not_awaited()
        self.assertEqual(result["case_id"], "VP-TEST")

    async def test_report_failure_rolls_back_entire_creation(self):
        async def execute(sql, args):
            if "INSERT INTO case_reports" in sql:
                raise IntegrityError(1452, "test report failure")
        self.cursor.execute.side_effect = execute
        with self.assertRaises(IntegrityError):
            await self.repository.create(self.record)
        self.connection.rollback.assert_awaited_once()
        self.connection.commit.assert_not_awaited()

    async def test_only_case_insert_duplicates_are_retryable(self):
        self.cursor.execute.side_effect = IntegrityError(1062, "test duplicate")
        with self.assertRaises(CaseCreationConflictError):
            await self.repository.create(self.record)
        self.connection.rollback.assert_awaited_once()
        self.connection.commit.assert_not_awaited()
