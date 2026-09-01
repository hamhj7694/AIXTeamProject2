from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from contracts.diagnosis import AnalyzeTextRequest
from contracts.public_api.case_analyze import (
    PublicAnalyzeCaseRequest,
    PublicAnalyzeCaseResponse,
    PublicAnalyzeError,
    PublicInitialReportReference,
)

from .clients.diagnosis_ai import AiServiceError, HttpDiagnosisAiClient
from .domains.cases.repository import InMemoryCaseRepository
from .domains.cases.service import AnalyzeCaseService


load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)


def build_repository():
    if os.getenv("CASE_REPOSITORY", "memory").lower() == "mysql":
        from .domains.cases.mysql_repository import MySqlCaseRepository
        return MySqlCaseRepository()
    return InMemoryCaseRepository()

app = FastAPI(title="AI Independent Verification - General API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
repository = build_repository()
service = AnalyzeCaseService(HttpDiagnosisAiClient(), repository)


def public_failed_response(code: str, message: str, *, retryable: bool) -> PublicAnalyzeCaseResponse:
    return PublicAnalyzeCaseResponse(
        disposition="FAILED",
        error=PublicAnalyzeError(code=code, message=message, retryable=retryable),
    )


def to_public_analyze_response(result) -> PublicAnalyzeCaseResponse:
    if result.disposition == "FAILED":
        error = result.error
        return public_failed_response(
            error.code if error else "AI_ANALYSIS_FAILED",
            error.message if error else "진단을 완료하지 못했습니다.",
            retryable=error.retryable if error else True,
        )

    if result.disposition == "NO_CASE":
        return PublicAnalyzeCaseResponse(
            disposition="NO_CASE",
            risk="NORMAL",
            initial_brief=result.initial_brief,
        )

    report = result.initial_report
    return PublicAnalyzeCaseResponse(
        disposition="CASE_CREATED",
        case_id=result.case_id,
        risk=result.risk.value if hasattr(result.risk, "value") else result.risk,
        mode=result.mode,
        status=result.status,
        initial_brief=result.initial_brief,
        initial_report=PublicInitialReportReference(
            report_id=report.report_id,
            case_id=report.case_id,
            report_version=report.report_version,
        ) if report else None,
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(RequestValidationError)
async def public_analyze_validation_error(request: Request, exc: RequestValidationError):
    if request.url.path == "/api/cases/analyze":
        failure = public_failed_response("INVALID_INPUT", "요청 형식을 확인해 주세요.", retryable=False)
        return JSONResponse(status_code=400, content=failure.model_dump(mode="json"))
    return await request_validation_exception_handler(request, exc)


@app.post("/api/cases/analyze", response_model=PublicAnalyzeCaseResponse, status_code=201)
async def analyze_case(request: PublicAnalyzeCaseRequest) -> PublicAnalyzeCaseResponse | JSONResponse:
    internal_request = AnalyzeTextRequest.model_validate(request.model_dump())
    try:
        return to_public_analyze_response(await service.analyze(internal_request))
    except ValueError as exc:
        failure = public_failed_response("INVALID_INPUT", str(exc), retryable=False)
        return JSONResponse(status_code=400, content=failure.model_dump(mode="json"))
    except AiServiceError as exc:
        failure = public_failed_response("AI_ANALYSIS_FAILED", str(exc), retryable=True)
        return JSONResponse(status_code=503, content=failure.model_dump(mode="json"))
    except Exception as exc:
        failure = public_failed_response("AI_ANALYSIS_FAILED", "진단을 완료하지 못했습니다.", retryable=True)
        return JSONResponse(status_code=503, content=failure.model_dump(mode="json"))


@app.get("/api/cases")
async def list_cases() -> list[dict]:
    return await repository.list()


@app.get("/api/cases/{case_id}")
async def get_case(case_id: str) -> dict:
    record = await repository.get(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."})
    return record


@app.get("/api/cases/{case_id}/reports/live")
async def get_live_report(case_id: str) -> dict:
    record = await repository.get(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."})
    return record["initial_report"]
