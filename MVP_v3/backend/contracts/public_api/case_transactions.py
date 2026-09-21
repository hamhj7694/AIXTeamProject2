from __future__ import annotations

from pydantic import BaseModel, Field


class PublicCaseTransactionBase(BaseModel):
    transaction_type: str = Field(min_length=1, max_length=32)
    transaction_at: str
    amount: float = Field(ge=0)
    account_number: str | None = Field(default=None, max_length=100)
    counterparty_name: str | None = Field(default=None, max_length=100)
    counterparty_account: str | None = Field(default=None, max_length=100)
    bank_name: str | None = Field(default=None, max_length=100)
    memo: str | None = Field(default=None, max_length=500)
    source: str = Field(default="MANUAL", min_length=1, max_length=32)


class PublicCaseTransactionCreateRequest(PublicCaseTransactionBase):
    pass


class PublicCaseTransactionPatchRequest(BaseModel):
    transaction_type: str | None = Field(default=None, min_length=1, max_length=32)
    transaction_at: str | None = None
    amount: float | None = Field(default=None, ge=0)
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
