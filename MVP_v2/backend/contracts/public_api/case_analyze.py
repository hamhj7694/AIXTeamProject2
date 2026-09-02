"""Frontend ↔ General API의 공개 Analyze Contract v1.

AI API의 진단 결과 전체는 General API 내부에서만 사용한다. 이 모듈은
`POST /api/cases/analyze`가 Browser에 반환할 최소 필드만 정의한다.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .case_enums import (
    AnalyzeDisposition,
    CaseRisk,
    InitialCaseMode,
    InitialCaseStatus,
    PublicAnalyzeErrorCode,
)


PUBLIC_ANALYZE_SCHEMA_VERSION = "case_analyze.v1"


class PublicStrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PublicAnalyzeCaseRequest(PublicStrictModel):
    text: str = Field(min_length=1, max_length=50_000)
    # 현재 Frontend는 매 요청마다 UUID를 생성한다. 빈 문자열은 기존 구현과
    # 동일하게 "미제공"으로 취급하며, 멱등성 키로 사용하지 않는다.
    client_request_id: str | None = Field(default=None, max_length=100)
    sample_type: str | None = Field(default=None, max_length=50)


class PublicAnalyzeError(PublicStrictModel):
    code: PublicAnalyzeErrorCode
    message: str = Field(min_length=1)
    retryable: bool = False


class PublicInitialReportReference(PublicStrictModel):
    report_id: str
    case_id: str
    report_version: int = Field(ge=1)


class PublicAnalyzeCaseResponse(PublicStrictModel):
    schema_version: Literal[PUBLIC_ANALYZE_SCHEMA_VERSION] = PUBLIC_ANALYZE_SCHEMA_VERSION
    disposition: AnalyzeDisposition
    case_id: str | None = None
    risk: CaseRisk | None = None
    mode: InitialCaseMode | None = None
    status: InitialCaseStatus | None = None
    initial_brief: str | None = None
    initial_report: PublicInitialReportReference | None = None
    error: PublicAnalyzeError | None = None

    @model_validator(mode="after")
    def validate_disposition_fields(self) -> "PublicAnalyzeCaseResponse":
        if self.disposition == "CASE_CREATED":
            if not all((self.case_id, self.risk, self.mode, self.status, self.initial_brief, self.initial_report)):
                raise ValueError("CASE_CREATED requires case summary fields and an initial_report reference.")
            if self.error is not None:
                raise ValueError("CASE_CREATED must not include error.")
        elif self.disposition == "NO_CASE":
            if self.case_id is not None or self.mode is not None or self.status is not None or self.initial_report is not None:
                raise ValueError("NO_CASE must not include Case creation fields.")
            if self.risk != "NORMAL" or not self.initial_brief or self.error is not None:
                raise ValueError("NO_CASE requires NORMAL risk and initial_brief without error.")
        else:
            if any((self.case_id, self.risk, self.mode, self.status, self.initial_brief, self.initial_report)):
                raise ValueError("FAILED must not include analysis or Case fields.")
            if self.error is None:
                raise ValueError("FAILED requires error.")
        return self
