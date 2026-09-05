"""현재 Case 목록·상세 화면과 호환되는 공개 Read Contract.

Frontend가 이미 사용하는 필드만 고정한다. AI 내부 진단 구조의 의미를
이 모듈에서 재정의하거나 DB 저장 구조를 변경하지 않는다.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from .case_enums import CaseMode, CaseRisk, CaseStatus


class PublicCaseReadModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PublicCaseReadResponse(PublicCaseReadModel):
    case_id: str
    version: int = 1
    client_request_id: str | None
    input_text: str
    risk: CaseRisk
    risk_score: float
    mode: CaseMode
    status: CaseStatus
    initial_brief: str
    diagnosis: dict[str, Any]
    initial_report: dict[str, Any] | None
    primary_assignee: str | None = None
    victim_transfer_status: str = "UNKNOWN"
    actual_loss_amount_krw: float | None = None
    created_at: str
    updated_at: str
    deleted_at: str | None = None
    trash_expires_at: str | None = None


class PublicCaseSummaryResponse(PublicCaseReadModel):
    """Screen-safe Case context shared by customer, bank, and verification views."""
    case_id: str
    version: int = 1
    context_revision: int = 1
    risk: CaseRisk
    mode: CaseMode
    status: CaseStatus
    initial_brief: str
    primary_assignee: str | None = None
    victim_transfer_status: str = "UNKNOWN"
    actual_loss_amount_krw: float | None = None
    created_at: str
    updated_at: str


def to_public_case_read_response(record: dict[str, Any]) -> PublicCaseReadResponse:
    """Repository 내부 레코드에서 기존 화면 호환 공개 필드만 반환한다."""
    return PublicCaseReadResponse.model_validate({
        "case_id": record["case_id"],
        "version": record.get("version", 1),
        "client_request_id": record.get("client_request_id"),
        "input_text": record["input_text"],
        "risk": record["risk"],
        "risk_score": record["risk_score"],
        "mode": record["mode"],
        "status": record["status"],
        "initial_brief": record["initial_brief"],
        "diagnosis": record["diagnosis"],
        "initial_report": record.get("initial_report"),
        "primary_assignee": record.get("primary_assignee"),
        "victim_transfer_status": record.get("victim_transfer_status", "UNKNOWN"),
        "actual_loss_amount_krw": record.get("actual_loss_amount_krw"),
        "created_at": record["created_at"],
        "updated_at": record["updated_at"],
        "deleted_at": record.get("deleted_at"),
        "trash_expires_at": record.get("trash_expires_at"),
    })


def to_public_case_summary_response(record: dict[str, Any]) -> PublicCaseSummaryResponse:
    """Do not include original call text, diagnosis payload, or internal report in chat bundles."""
    return PublicCaseSummaryResponse.model_validate({
        "case_id": record["case_id"], "version": record.get("version", 1),
        "context_revision": record.get("context_revision", 1),
        "risk": record["risk"], "mode": record["mode"], "status": record["status"],
        "initial_brief": record["initial_brief"], "primary_assignee": record.get("primary_assignee"),
        "victim_transfer_status": record.get("victim_transfer_status", "UNKNOWN"),
        "actual_loss_amount_krw": record.get("actual_loss_amount_krw"),
        "created_at": record["created_at"], "updated_at": record["updated_at"],
    })
