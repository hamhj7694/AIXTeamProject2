"""Safe detection for conflicting customer-reported transfer amounts.

This module deliberately does not create or update a transaction.  A chat
message is only a customer statement; an existing transaction remains the
authoritative record until a staff-reviewed clarification confirms otherwise.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any


TRANSACTION_AMOUNT_CONFLICT_TARGET = "transaction_amount_conflict"

# Longest units first so ``천만원`` is not parsed as ``천`` + ``만원``.
_AMOUNT_RE = re.compile(
    r"(?P<number>\d[\d,]*(?:\.\d+)?)\s*"
    r"(?P<unit>천만|백만|십만|억|만|천)?\s*원"
)
_UNIT_MULTIPLIERS = {
    "천": 1_000,
    "만": 10_000,
    "십만": 100_000,
    "백만": 1_000_000,
    "천만": 10_000_000,
    "억": 100_000_000,
}

# These are completion/reporting forms, not requests.  In particular,
# ``보내 줘`` and ``이체해`` must not be treated as a completed transfer.
_TRANSFER_COMPLETION_RE = re.compile(
    r"(?:송금\s*(?:했|함|한|했어|했어요|했습니다)|"
    r"이체\s*(?:했|함|한|했어|했어요|했습니다)|"
    r"입금\s*(?:했|함|한|했어|했어요|했습니다)|"
    r"보냈(?:어|어요|습니다)?|보낸)"
)


def extract_krw_amounts(text: str) -> list[int]:
    """Extract integer KRW amounts written with Korean units or ``원``."""
    amounts: list[int] = []
    for match in _AMOUNT_RE.finditer(text or ""):
        try:
            number = Decimal(match.group("number").replace(",", ""))
            multiplier = _UNIT_MULTIPLIERS.get(match.group("unit") or "", 1)
            amount = number * multiplier
            if amount != amount.to_integral_value() or amount <= 0:
                continue
            value = int(amount)
        except (InvalidOperation, ValueError):
            continue
        if value not in amounts:
            amounts.append(value)
    return amounts


def detect_transfer_amount_conflict(
    message: dict[str, Any], transactions: list[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    """Return a review proposal when a customer reports a new, conflicting amount."""
    if message.get("actor_type") != "CUSTOMER" or message.get("message_kind", "CHAT") != "CHAT":
        return None
    content = str(message.get("content") or "")
    if not _TRANSFER_COMPLETION_RE.search(content):
        return None
    reported_amounts = extract_krw_amounts(content)
    if not reported_amounts:
        return None
    existing = [
        item for item in (transactions or [])
        if item.get("transaction_type") == "TRANSFER_OUT"
        and isinstance(item.get("amount"), int)
        and not isinstance(item.get("amount"), bool)
        and int(item["amount"]) > 0
    ]
    if not existing:
        return None
    existing_amounts = sorted({int(item["amount"]) for item in existing})
    conflicting = [amount for amount in reported_amounts if amount not in existing_amounts]
    matching = [amount for amount in reported_amounts if amount in existing_amounts]
    if not conflicting and not matching:
        return None
    # A matching amount is still ambiguous: it can be a repeated statement or
    # a second transfer for the same amount.  The caller must ask before adding
    # or changing a ledger row.
    reported_amount = conflicting[0] if conflicting else matching[0]
    return {
        "reported_amount_krw": reported_amount,
        "existing_amounts_krw": existing_amounts,
        "conflict_kind": "DIFFERENT_AMOUNT" if conflicting else "SAME_AMOUNT_AMBIGUOUS",
        "existing_transaction_ids": [str(item.get("id")) for item in existing],
        "reported_message_id": str(message.get("message_id") or ""),
        "reported_at": message.get("created_at"),
    }


def conflict_client_request_id(case_id: str, conflict: dict[str, Any]) -> str:
    return (
        f"transaction-amount-conflict:{case_id}:"
        f"{conflict['reported_message_id']}:{conflict['reported_amount_krw']}"
    )
