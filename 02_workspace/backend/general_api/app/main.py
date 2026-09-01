from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from contracts.diagnosis import AiError, AnalyzeCaseResponse, AnalyzeTextRequest

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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/cases/analyze", response_model=AnalyzeCaseResponse, status_code=201)
async def analyze_case(request: AnalyzeTextRequest) -> AnalyzeCaseResponse | JSONResponse:
    try:
        return await service.analyze(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "INVALID_INPUT", "message": str(exc)}) from exc
    except AiServiceError as exc:
        failure = AnalyzeCaseResponse(
            disposition="FAILED",
            error=AiError(code="AI_ANALYSIS_FAILED", message=str(exc), retryable=True),
        )
        return JSONResponse(status_code=503, content=failure.model_dump(mode="json"))
    except Exception as exc:
        failure = AnalyzeCaseResponse(
            disposition="FAILED",
            error=AiError(code="AI_ANALYSIS_FAILED", message="진단을 완료하지 못했습니다.", retryable=True, details={"cause": type(exc).__name__}),
        )
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
