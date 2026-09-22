from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, StrictInt


TransactionType = Literal["TRANSFER_OUT", "RETURN_IN", "CANCELLED"]


class PublicCaseTransactionBase(BaseModel):
    transaction_type: TransactionType
    transaction_at: str
    amount: StrictInt = Field(ge=0)
    account_number: str | None = Field(default=None, max_length=100)
    counterparty_name: str | None = Field(default=None, max_length=100)
    counterparty_account: str | None = Field(default=None, max_length=100)
    bank_name: str | None = Field(default=None, max_length=100)
    memo: str | None = Field(default=None, max_length=500)
    source: str = Field(default="MANUAL", min_length=1, max_length=32)


class PublicCaseTransactionCreateRequest(PublicCaseTransactionBase):
    pass


class PublicCaseTransactionPatchRequest(BaseModel):
    transaction_type: TransactionType | None = None
    transaction_at: str | None = None
    amount: StrictInt | None = Field(default=None, ge=0)
    account_number: str | None = Field(default=None, max_length=100)
    counterparty_name: str | None = Field(default=None, max_length=100)
    counterparty_account: str | None = Field(default=None, max_length=100)
    bank_name: str | None = Field(default=None, max_length=100)
    memo: str | None = Field(default=None, max_length=500)
    source: str | None = Field(default=None, min_length=1, max_length=32)


class PublicCaseTransactionResponse(PublicCaseTransactionBase):
    id: int
    case_id: str
    created_at: str
    updated_at: str
