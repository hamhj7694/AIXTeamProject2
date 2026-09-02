from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

from contracts.diagnosis import AnalyzeTextRequest, DiagnosisResult

from .domains.diagnosis import DiagnosisService


load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

app = FastAPI(title="AI Independent Verification - Diagnosis AI API", version="0.1.0")
service = DiagnosisService()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ai/analyze/text", response_model=DiagnosisResult)
async def analyze_text(request: AnalyzeTextRequest) -> DiagnosisResult:
    try:
        return await service.analyze(request.text.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "INVALID_INPUT", "message": str(exc)}) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"code": "AI_ANALYSIS_FAILED", "message": str(exc)}) from exc


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
