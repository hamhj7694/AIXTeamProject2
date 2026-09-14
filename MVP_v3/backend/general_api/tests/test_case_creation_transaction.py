"""Exercise the real SQL repository's commit/rollback boundary without touching a DB."""
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from pymysql.err import IntegrityError
from general_api.app.domains.cases.mysql_repository import MySqlCaseRepository
from general_api.app.domains.cases.repository import CaseCreationConflictError, InMemoryCaseRepository


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


class CaseNumberAllocationTest(unittest.IsolatedAsyncioTestCase):
    async def test_in_memory_concurrent_reservations_are_unique(self):
        repository = InMemoryCaseRepository()

        case_ids = await asyncio.gather(*(repository.next_case_id() for _ in range(8)))

        self.assertEqual(set(case_ids), {f"VP-{number}" for number in range(1, 9)})

    async def test_in_memory_counter_follows_existing_ids_and_never_moves_back(self):
        repository = InMemoryCaseRepository()
        repository._records = [
            {"case_id": "VP-001"}, {"case_id": "VP-3"}, {"case_id": "VP-8"},
            {"case_id": "100"}, {"case_id": "TEST-100"}, {"case_id": "VP-X"},
        ]

        self.assertEqual(await repository.next_case_id(), "VP-9")
        repository._records.clear()  # 영구삭제되어도 이미 예약한 번호는 다시 쓰지 않는다.
        self.assertEqual(await repository.next_case_id(), "VP-10")

    async def test_mysql_reservation_locks_updates_and_commits_on_one_connection(self):
        cursor = AsyncMock()
        cursor.fetchone.return_value = (40,)
        connection = MagicMock()
        connection.begin = AsyncMock()
        connection.commit = AsyncMock()
        connection.rollback = AsyncMock()
        connection.cursor.return_value.__aenter__ = AsyncMock(return_value=cursor)
        connection.cursor.return_value.__aexit__ = AsyncMock(return_value=False)
        pool = MagicMock()
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        repository = MySqlCaseRepository()
        repository._get_pool = AsyncMock(return_value=pool)

        self.assertEqual(await repository.next_case_id(), "VP-41")

        connection.begin.assert_awaited_once()
        self.assertIn("FOR UPDATE", cursor.execute.await_args_list[0].args[0])
        self.assertIn("UPDATE case_number_sequences", cursor.execute.await_args_list[1].args[0])
        connection.commit.assert_awaited_once()
        connection.rollback.assert_not_awaited()

    async def test_mysql_missing_sequence_rolls_back_without_max_fallback(self):
        cursor = AsyncMock()
        cursor.fetchone.return_value = None
        connection = MagicMock()
        connection.begin = AsyncMock()
        connection.commit = AsyncMock()
        connection.rollback = AsyncMock()
        connection.cursor.return_value.__aenter__ = AsyncMock(return_value=cursor)
        connection.cursor.return_value.__aexit__ = AsyncMock(return_value=False)
        pool = MagicMock()
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        repository = MySqlCaseRepository()
        repository._get_pool = AsyncMock(return_value=pool)

        with self.assertRaisesRegex(RuntimeError, "015_case_number_sequence.sql"):
            await repository.next_case_id()

        connection.rollback.assert_awaited_once()
        connection.commit.assert_not_awaited()
