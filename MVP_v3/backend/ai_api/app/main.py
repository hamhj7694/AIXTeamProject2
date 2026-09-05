from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from openai import APIConnectionError, AuthenticationError, RateLimitError

from contracts.ai_internal.case_snapshot import CaseSnapshotAiInput, CaseSnapshotPresentation
from contracts.ai_internal.case_copilot import CaseCopilotInput, CaseCopilotOutput
from contracts.ai_internal.final_report import FinalCaseReportInput, FinalCaseReportOutput
from contracts.ai_internal.work_card import CaseWorkCardInput, CaseWorkCardOutput
from contracts.diagnosis import AnalyzeTextRequest, DiagnosisResult
from request_trace import install_request_trace

from .domains.case_support import CaseSnapshotAiAdapter
from .domains.case_support.copilot_service import CaseCopilotAuthenticationError, CaseCopilotQuotaError, CaseCopilotService
from .domains.case_support.final_report_service import FinalCaseReportService
from .domains.case_support.work_card_service import CaseWorkCardService
from .domains.diagnosis import DiagnosisService
from .domains.diagnosis.budget import DiagnosisBudgetExceededError
from .domains.diagnosis.extractor import AiProviderAuthenticationError, AiProviderQuotaError
from .domains.diagnosis.model_adapter import load_model_bundle


load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)

app = FastAPI(title="AI Independent Verification - Diagnosis AI API", version="0.1.0")
install_request_trace(app, "ai-api")
service = DiagnosisService()
case_snapshot_adapter = CaseSnapshotAiAdapter()
case_copilot_service = CaseCopilotService()
case_work_card_service = CaseWorkCardService()
final_report_service = FinalCaseReportService()


@app.on_event("startup")
async def validate_ml_runtime() -> None:
    # Reject incompatible runtimes before accepting requests that could spend AI credits.
    load_model_bundle()


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "diagnosis-ai-api", "status": "ok", "health": "/health"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ai/analyze/text", response_model=DiagnosisResult)
async def analyze_text(request: AnalyzeTextRequest) -> DiagnosisResult:
    try:
        return await service.analyze(request.text.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "INVALID_INPUT", "message": str(exc)}) from exc
    except DiagnosisBudgetExceededError as exc:
        raise HTTPException(status_code=429, detail={"code": "AI_BUDGET_LIMIT_REACHED", "message": str(exc)}) from exc
    except (AiProviderQuotaError, RateLimitError) as exc:
        raise HTTPException(status_code=429, detail={"code": "OPENAI_QUOTA_EXHAUSTED", "message": str(exc)}) from exc
    except (AiProviderAuthenticationError, AuthenticationError) as exc:
        raise HTTPException(status_code=401, detail={"code": "OPENAI_AUTHENTICATION_FAILED", "message": str(exc)}) from exc
    except APIConnectionError as exc:
        raise HTTPException(status_code=503, detail={
            "code": "AI_PROVIDER_CONNECTION_FAILED",
            "message": "AI 서버에서 외부 AI 서비스에 연결하지 못했습니다. 네트워크 연결을 확인해 주세요.",
        }) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"code": "AI_ANALYSIS_FAILED", "message": str(exc)}) from exc


@app.post("/ai/case-support/snapshot", response_model=CaseSnapshotPresentation)
async def build_case_support_snapshot(request: CaseSnapshotAiInput) -> CaseSnapshotPresentation:
    """기존 진단 결과를 담당자 검토용 Brief·질문 후보로 변환하는 독립 내부 API."""
    try:
        return case_snapshot_adapter.build_presentation(request.model_dump(mode="python"))
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "AI_CASE_SUPPORT_FAILED", "message": str(exc)},
        ) from exc


@app.post("/ai/case-copilot/replies", response_model=CaseCopilotOutput)
async def generate_case_copilot_reply(request: CaseCopilotInput) -> CaseCopilotOutput:
    try:
        return await case_copilot_service.generate(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "INVALID_INPUT", "message": str(exc)}) from exc
    except CaseCopilotQuotaError as exc:
        raise HTTPException(status_code=429, detail={"code": "OPENAI_QUOTA_EXHAUSTED", "message": str(exc)}) from exc
    except CaseCopilotAuthenticationError as exc:
        raise HTTPException(status_code=401, detail={"code": "OPENAI_AUTHENTICATION_FAILED", "message": str(exc)}) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"code": "AI_CASE_COPILOT_FAILED", "message": str(exc)}) from exc


@app.post("/ai/work-cards/generate", response_model=CaseWorkCardOutput)
async def generate_case_work_card(request: CaseWorkCardInput) -> CaseWorkCardOutput:
    try:
        return await case_work_card_service.generate(request)
    except CaseCopilotQuotaError as exc:
        raise HTTPException(status_code=429, detail={"code": "OPENAI_QUOTA_EXHAUSTED", "message": str(exc)}) from exc
    except CaseCopilotAuthenticationError as exc:
        raise HTTPException(status_code=401, detail={"code": "OPENAI_AUTHENTICATION_FAILED", "message": str(exc)}) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"code": "AI_WORK_CARD_FAILED", "message": str(exc)}) from exc


@app.post("/ai/final-reports/generate", response_model=FinalCaseReportOutput)
async def generate_final_case_report(request: FinalCaseReportInput) -> FinalCaseReportOutput:
    try:
        return await final_report_service.generate(request)
    except CaseCopilotQuotaError as exc:
        raise HTTPException(status_code=429, detail={"code": "OPENAI_QUOTA_EXHAUSTED", "message": str(exc)}) from exc
    except CaseCopilotAuthenticationError as exc:
        raise HTTPException(status_code=401, detail={"code": "OPENAI_AUTHENTICATION_FAILED", "message": str(exc)}) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"code": "AI_FINAL_REPORT_FAILED", "message": str(exc)}) from exc


@app.post("/ai/analyze/windows", response_model=list)
async def analyze_windows(request: AnalyzeTextRequest) -> list[dict]:
    return [window.model_dump(mode="json") for window in (await service.analyze(request.text.strip())).windows]


@app.post("/ai/features/extract", response_model=dict)
async def extract_features(request: AnalyzeTextRequest) -> dict[str, float]:
    return (await service.analyze(request.text.strip())).features


@app.post("/ai/risk/predict", response_model=dict)
async def predict_risk(request: AnalyzeTextRequest) -> dict[str, str | float]:
    result = await service.analyze(request.text.strip())
    return {"risk_level": result.risk_level.value, "risk_score": result.risk_score, "model_label": result.model_label}
