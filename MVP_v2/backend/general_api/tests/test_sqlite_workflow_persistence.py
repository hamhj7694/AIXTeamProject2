from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from general_api.app.domains.cases.sqlite_repository import LocalSqliteCaseRepository


class SqliteWorkflowPersistenceTest(unittest.IsolatedAsyncioTestCase):
    async def test_question_answer_and_fact_survive_repository_restart(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "case.sqlite3"
            repository = LocalSqliteCaseRepository(str(database))
            now = datetime.now(timezone.utc).isoformat()
            await repository.create({
                "case_id": "VP-1", "initial_report": {"report_id": "report-1"},
                "created_at": now, "updated_at": now, "status": "TRIAGE", "mode": "PREVENT",
            })
            queued = await repository.queue_customer_questions("VP-1", [{
                "target_field": "transfer_status", "question_text": "송금했나요?", "reason": "피해 확인",
                "priority": "P0", "options": ["예", "아니요"],
            }], "staff-1")
            question = await repository.dispatch_next_customer_question("VP-1")
            await repository.link_customer_question_message("VP-1", question["question_id"], "question-message-1")
            await repository.answer_customer_question("VP-1", question["question_id"], "message-1", "아니요")
            await repository.propose_case_fact("VP-1", question["question_id"], "아니요", "message-1")

            restarted = LocalSqliteCaseRepository(str(database))
            questions = await restarted.list_customer_questions("VP-1")
            facts = await restarted.list_case_facts("VP-1")

            self.assertEqual(len(queued), 1)
            self.assertEqual(questions[0]["status"], "ANSWERED")
            self.assertEqual(questions[0]["question_message_id"], "question-message-1")
            self.assertEqual(questions[0]["answer_message_id"], "message-1")
            self.assertEqual(questions[0]["answer_text"], "아니요")
            self.assertEqual(facts[0]["value"], "아니요")
            self.assertEqual(facts[0]["source_question_id"], question["question_id"])

    async def test_only_one_customer_question_is_asked_at_a_time(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = LocalSqliteCaseRepository(str(Path(directory) / "case.sqlite3"))
            now = datetime.now(timezone.utc).isoformat()
            await repository.create({"case_id": "VP-2", "initial_report": {"report_id": "report-2"}, "created_at": now, "updated_at": now})
            created = await repository.queue_customer_questions("VP-2", [
                {"source": "CUSTOMER_AGENT", "target_field": "transfer_status", "question_text": "송금했나요?", "reason": "안전 확인", "priority": "P0"},
                {"source": "CUSTOMER_AGENT", "target_field": "personal_information_exposure", "question_text": "개인정보를 제공했나요?", "reason": "안전 확인", "priority": "P0"},
            ], "customer-agent")
            first = await repository.dispatch_next_customer_question("VP-2")
            blocked = await repository.dispatch_next_customer_question("VP-2")
            await repository.answer_customer_question("VP-2", first["question_id"], "message-2", "아니요")
            second = await repository.dispatch_next_customer_question("VP-2")

            self.assertEqual(len(created), 2)
            self.assertEqual(first["source"], "CUSTOMER_AGENT")
            self.assertIsNone(blocked)
            self.assertEqual(second["target_field"], "personal_information_exposure")

    async def test_answered_field_and_same_question_text_cannot_be_queued_again(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = LocalSqliteCaseRepository(str(Path(directory) / "case.sqlite3"))
            now = datetime.now(timezone.utc).isoformat()
            await repository.create({"case_id": "VP-3", "initial_report": {"report_id": "report-3"}, "created_at": now, "updated_at": now})
            created = await repository.queue_customer_questions("VP-3", [{
                "target_field": "PERSONAL_INFO",
                "question_text": "개인정보를 제공했나요?", "reason": "노출 확인", "priority": "P0",
            }], "customer-agent")
            asked = await repository.dispatch_next_customer_question("VP-3")
            await repository.answer_customer_question("VP-3", asked["question_id"], "answer-3", "예")

            same_field = await repository.queue_customer_questions("VP-3", [{
                "target_field": "personal_information_exposure",
                "question_text": "주민등록번호를 알려주셨나요?", "reason": "중복 필드", "priority": "P0",
            }], "customer-agent")
            same_text = await repository.queue_customer_questions("VP-3", [{
                "target_field": "custom_duplicate_field",
                "question_text": "  개인정보를   제공했나요? ", "reason": "중복 문구", "priority": "P1",
            }], "staff-1")

            self.assertEqual(len(created), 1)
            self.assertEqual(same_field, [])
            self.assertEqual(same_text, [])


if __name__ == "__main__":
    unittest.main()
