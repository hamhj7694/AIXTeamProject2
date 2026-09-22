import pytest
from pydantic import ValidationError

from contracts.public_api.case_transactions import PublicCaseTransactionCreateRequest


def _request(**overrides):
    values = {
        "transaction_type": "TRANSFER_OUT",
        "transaction_at": "2026-09-22T00:00:00Z",
        "amount": 3_000_000,
    }
    values.update(overrides)
    return PublicCaseTransactionCreateRequest(**values)


def test_transaction_amount_is_a_non_negative_krw_integer() -> None:
    assert _request().amount == 3_000_000
    with pytest.raises(ValidationError):
        _request(amount=3_000_000.5)
    with pytest.raises(ValidationError):
        _request(amount=-1)


def test_transaction_type_is_explicit() -> None:
    assert _request(transaction_type="RETURN_IN").transaction_type == "RETURN_IN"
    assert _request(transaction_type="CANCELLED").transaction_type == "CANCELLED"
    with pytest.raises(ValidationError):
        _request(transaction_type="UNKNOWN")
