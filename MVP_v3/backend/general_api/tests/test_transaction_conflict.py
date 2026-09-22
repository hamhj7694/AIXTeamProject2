from __future__ import annotations

import unittest

from general_api.app.domains.cases.transaction_conflict import (
    detect_transfer_amount_conflict,
    extract_krw_amounts,
)


class TransactionConflictTest(unittest.TestCase):
    def test_extracts_korean_units_as_integer_krw(self) -> None:
        self.assertEqual(extract_krw_amounts("300만원과 2,000,000원을 말했습니다."), [3_000_000, 2_000_000])
        self.assertEqual(extract_krw_amounts("3백만원을 보냈어요."), [3_000_000])

    def test_request_is_not_treated_as_completed_transfer(self) -> None:
        message = {"actor_type": "CUSTOMER", "message_kind": "CHAT", "content": "300만원 보내 줘."}
        transactions = [{"id": 1, "transaction_type": "TRANSFER_OUT", "amount": 2_000_000}]
        self.assertIsNone(detect_transfer_amount_conflict(message, transactions))

    def test_different_reported_amount_becomes_review_candidate(self) -> None:
        message = {
            "message_id": "msg-1", "actor_type": "CUSTOMER", "message_kind": "CHAT",
            "content": "아까 300만원 보냈어.", "created_at": "2026-09-22T10:00:00+09:00",
        }
        transactions = [{"id": 1, "transaction_type": "TRANSFER_OUT", "amount": 2_000_000}]
        self.assertEqual(
            detect_transfer_amount_conflict(message, transactions),
            {
                "reported_amount_krw": 3_000_000,
                "existing_amounts_krw": [2_000_000],
                "conflict_kind": "DIFFERENT_AMOUNT",
                "existing_transaction_ids": ["1"],
                "reported_message_id": "msg-1",
                "reported_at": "2026-09-22T10:00:00+09:00",
            },
        )

    def test_same_amount_is_not_a_conflict(self) -> None:
        message = {"actor_type": "CUSTOMER", "message_kind": "CHAT", "content": "아까 200만원 보냈어."}
        transactions = [{"id": 1, "transaction_type": "TRANSFER_OUT", "amount": 2_000_000}]
        result = detect_transfer_amount_conflict(message, transactions)
        self.assertIsNotNone(result)
        self.assertEqual(result["conflict_kind"], "SAME_AMOUNT_AMBIGUOUS")
        self.assertEqual(result["reported_amount_krw"], 2_000_000)
