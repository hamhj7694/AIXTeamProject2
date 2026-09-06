import unittest
from datetime import datetime

from general_api.app.domains.cases.mysql_repository import MySqlCaseRepository, _utc_iso, _utc_naive


class CaseCreatedAtTimezoneTest(unittest.TestCase):
    def test_database_creation_time_is_normalized_to_utc(self):
        stored = _utc_naive("2026-09-05T10:15:00+09:00")
        self.assertEqual(stored, datetime(2026, 9, 5, 1, 15, 0))

    def test_database_utc_creation_time_has_offset_in_api(self):
        self.assertEqual(
            _utc_iso(datetime(2026, 9, 5, 1, 15, 0)),
            "2026-09-05T01:15:00+00:00",
        )

    def test_customer_question_timestamps_are_utc_aware(self):
        repository = MySqlCaseRepository()
        item = repository._question_row({
            "question_id": "question-1", "case_id": "VP-1", "source": "BANK_SELECTED",
            "target_field": "transfer_status", "question_text": "송금했나요?", "reason": "확인 필요",
            "priority": "HIGH", "status": "ANSWERED", "sequence": 1, "requested_by": "staff",
            "asked_at": datetime(2026, 9, 6, 6, 51), "answered_at": datetime(2026, 9, 6, 6, 52),
            "answer_text": "NO", "options_json": "[]", "question_message_id": "msg-q",
            "answer_message_id": "msg-a",
        })
        self.assertEqual(item["asked_at"], "2026-09-06T06:51:00+00:00")
        self.assertEqual(item["answered_at"], "2026-09-06T06:52:00+00:00")


if __name__ == "__main__":
    unittest.main()
