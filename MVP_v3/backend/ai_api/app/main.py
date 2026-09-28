from __future__ import annotations

from pathlib import Path
import json
import os

from dotenv import load_dotenv
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from openai import APIConnectionError, AuthenticationError, RateLimitError
from audio_upload import MAX_AUDIO_BYTES, read_audio_upload

from contracts.ai_internal.case_snapshot import CaseSnapshotAiInput, CaseSnapshotPresentation
from contracts.ai_internal.case_copilot import CaseCopilotInput, CaseCopilotOutput
from contracts.ai_internal.final_report import FinalCaseReportInput, FinalCaseReportOutput
from contracts.ai_internal.work_card import CaseWorkCardInput, CaseWorkCardOutput
from contracts.ai_internal.context_fact_extraction import ContextFactExtractionInput, ContextFactExtractionOutput
from contracts.diagnosis import AnalysisEnvelope, AnalyzeTextRequest, DiagnosisResult
from contracts.public_api.ai_runtime import runtime_error
from request_trace import install_request_trace

from .domains.case_support import CaseSnapshotAiAdapter
from .domains.case_support.copilot_service import (
    CaseCopilotAuthenticationError,
    CaseCopilotProviderUnavailableError,
    CaseCopilotQuotaError,
    CaseCopilotResponseError,
    CaseCopilotService,
)
from .domains.case_support.final_report_service import FinalCaseReportService
from .domains.case_support.work_card_service import CaseWorkCardService
from .domains.case_support.context_fact_extraction_service import ContextFactExtractionService
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
context_fact_extraction_service = ContextFactExtractionService()


def _audio_transcription_options() -> dict[str, str]:
    model = os.getenv("OPENAI_AUDIO_TRANSCRIPTION_MODEL", "gpt-4o-transcribe").strip()
    options = {
        "model": model,
        "stream": "true",
        "language": "ko",
    }
    if model == "gpt-4o-transcribe-diarize":
        # Keep compatibility with an explicitly configured diarization model.
        options["response_format"] = "diarized_json"
        options["chunking_strategy"] = "auto"
    else:
        options["response_format"] = "json"
        options["prompt"] = (
            "은행 고객 상담 및 금융사기 의심 통화의 한국어 전사입니다. 실제로 들리는 말을 그대로 전사하세요. "
            "전화번호, 계좌번호, 사건번호, 금액과 숫자 발화(공·영·일·이·삼·사·오·육·칠·팔·구)를 특히 주의해 "
            "누락하지 말고 들린 순서대로 보존하세요. 숫자 발음은 숫자로 표기하되 불확실한 숫자는 추측하거나 보정하지 마세요. "
            "오디오에 없는 단어나 숫자를 덧붙이지 마세요."
        )
    return options


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


@app.get("/readiness")
async def readiness() -> dict[str, object]:
    """Local readiness only; never spends a provider request or credits."""
    import os
    return {
        "status": "ready" if os.getenv("OPENAI_API_KEY") else "degraded",
        "provider_configured": bool(os.getenv("OPENAI_API_KEY")),
        "provider_live_check": False,
        "diagnosis_limits": {
            "max_calls": int(os.getenv("OPENAI_MAX_CALLS_PER_DIAGNOSIS", "1024")),
            "max_total_tokens": int(os.getenv("OPENAI_MAX_TOTAL_TOKENS_PER_DIAGNOSIS", "2000000")),
            "max_input_chars": int(os.getenv("DIAGNOSIS_MAX_INPUT_CHARS", "500000")),
            "max_turns": int(os.getenv("DIAGNOSIS_MAX_TURNS", "1000")),
            "max_duration_seconds": float(os.getenv("DIAGNOSIS_MAX_DURATION_SECONDS", "1800")),
            "event_output_tokens": int(os.getenv("OPENAI_EVENT_MAX_OUTPUT_TOKENS", "3200")),
            "context_output_tokens": int(os.getenv("OPENAI_CONTEXT_MAX_OUTPUT_TOKENS", "16000")),
        },
    }


@app.post("/ai/audio/transcriptions/stream")
async def stream_audio_transcription(request: Request) -> StreamingResponse:
    try:
        upload = await read_audio_upload(request)
    except ValueError as exc:
        code = str(exc)
        messages = {
            "AUDIO_FILE_TOO_LARGE": f"음성 파일은 {MAX_AUDIO_BYTES // (1024 * 1024)}MB 이하만 분석할 수 있습니다.",
            "AUDIO_FILE_TYPE_UNSUPPORTED": "FLAC, MP3, MP4, MPEG, M4A, OGG, WAV, WEBM 음성 파일을 선택해 주세요.",
            "AUDIO_FILE_EMPTY": "선택한 음성 파일이 비어 있습니다.",
            "AUDIO_REQUEST_INVALID": "음성 파일 요청을 읽을 수 없습니다.",
        }
        raise HTTPException(status_code=413 if code == "AUDIO_FILE_TOO_LARGE" else 400,
                            detail={"code": code, "message": messages.get(code, "음성 파일을 확인해 주세요.")}) from exc

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail={
            "code": "OPENAI_AUDIO_NOT_CONFIGURED",
            "message": "음성 전사 기능을 사용할 수 없습니다. 관리자에게 OpenAI API 설정을 요청해 주세요.",
        })

    client = httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=20.0))
    try:
        outbound = client.build_request(
            "POST",
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            data=_audio_transcription_options(),
            files={"file": (upload.filename, upload.content, upload.content_type)},
        )
        upstream = await client.send(outbound, stream=True)
    except httpx.TimeoutException as exc:
        await client.aclose()
        raise HTTPException(status_code=504, detail={"code": "AUDIO_TRANSCRIPTION_TIMEOUT", "message": "음성 전사 요청 시간이 초과되었습니다."}) from exc
    except httpx.HTTPError as exc:
        await client.aclose()
        raise HTTPException(status_code=503, detail={"code": "AI_PROVIDER_UNAVAILABLE", "message": "음성 전사 서버에 연결할 수 없습니다."}) from exc

    if upstream.is_error:
        await upstream.aread()
        await upstream.aclose()
        await client.aclose()
        status = upstream.status_code
        if status == 401:
            code, message, public_status = "OPENAI_AUTHENTICATION_FAILED", "OpenAI 인증에 실패했습니다. 관리자에게 API 키 확인을 요청해 주세요.", 401
        elif status == 429:
            code, message, public_status = "OPENAI_QUOTA_EXHAUSTED", "음성 전사 사용 한도에 도달했습니다. 잠시 후 다시 시도해 주세요.", 429
        elif status in (400, 413, 415, 422):
            code, message, public_status = "AUDIO_TRANSCRIPTION_REJECTED", "음성 파일 형식 또는 전사 요청을 처리할 수 없습니다.", 422
        else:
            code, message, public_status = "AI_PROVIDER_UNAVAILABLE", "음성 전사 서버에서 오류가 발생했습니다.", 503
        raise HTTPException(status_code=public_status, detail={"code": code, "message": message})

    async def events():
        try:
            async for line in upstream.aiter_lines():
                yield (line + "\n").encode("utf-8")
            yield b"\n"
        except httpx.HTTPError:
            payload = json.dumps({"type": "error", "message": "전사 연결이 중단되었습니다. 이미 표시된 부분 전사는 유지됩니다."}, ensure_ascii=False)
            yield f"data: {payload}\n\n".encode("utf-8")
        finally:
            await upstream.aclose()
            await client.aclose()

    return StreamingResponse(events(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
    })


@app.post("/ai/analyze/text", response_model=DiagnosisResult)
async def analyze_text(request: AnalyzeTextRequest) -> DiagnosisResult:
    """Backward-compatible demo route. Production integration uses /ai/analyze/signals."""
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
        raise HTTPException(status_code=503, detail=runtime_error(
            "AI_PROVIDER_UNAVAILABLE",
            "AI 서버에서 외부 AI 서비스에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.",
            retryable=True, legacy_code="AI_PROVIDER_CONNECTION_FAILED",
        )) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=runtime_error(
            "AI_SERVICE_UNAVAILABLE", "AI 분석을 완료하지 못했습니다. 다시 시도해 주세요.",
            retryable=True, legacy_code="AI_ANALYSIS_FAILED",
        )) from exc


@app.post("/ai/demo/parse-transcript", response_model=AnalysisEnvelope)
async def parse_demo_transcript(request: AnalyzeTextRequest) -> AnalysisEnvelope:
    """Development simulator for the external/on-device structured analyzer."""
    try:
        return await service.build_demo_envelope(request.text.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "INVALID_INPUT", "message": str(exc)}) from exc
    except DiagnosisBudgetExceededError as exc:
        raise HTTPException(status_code=429, detail={"code": "AI_BUDGET_LIMIT_REACHED", "message": str(exc)}) from exc
    except (AiProviderQuotaError, RateLimitError) as exc:
        raise HTTPException(status_code=429, detail={"code": "OPENAI_QUOTA_EXHAUSTED", "message": str(exc)}) from exc
    except (AiProviderAuthenticationError, AuthenticationError) as exc:
        raise HTTPException(status_code=401, detail={"code": "OPENAI_AUTHENTICATION_FAILED", "message": str(exc)}) from exc
    except APIConnectionError as exc:
        raise HTTPException(status_code=503, detail=runtime_error(
            "AI_PROVIDER_UNAVAILABLE",
            "데모 분석기가 외부 AI 서비스에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.",
            retryable=True, legacy_code="AI_PROVIDER_CONNECTION_FAILED",
        )) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=runtime_error(
            "AI_SERVICE_UNAVAILABLE", "데모 분석 결과를 구조화하지 못했습니다. 다시 시도해 주세요.",
            retryable=True, legacy_code="AI_ANALYSIS_FAILED",
        )) from exc


@app.post("/ai/analyze/signals", response_model=DiagnosisResult)
async def analyze_signals(request: AnalysisEnvelope) -> DiagnosisResult:
    """CSR production boundary. Raw transcript fields are rejected by the contract."""
    try:
        return await service.analyze_envelope(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "INVALID_ENVELOPE", "message": str(exc)}) from exc
    except DiagnosisBudgetExceededError as exc:
        raise HTTPException(status_code=429, detail={"code": "AI_BUDGET_LIMIT_REACHED", "message": str(exc)}) from exc
    except (AiProviderQuotaError, RateLimitError) as exc:
        raise HTTPException(status_code=429, detail={"code": "OPENAI_QUOTA_EXHAUSTED", "message": str(exc)}) from exc
    except (AiProviderAuthenticationError, AuthenticationError) as exc:
        raise HTTPException(status_code=401, detail={"code": "OPENAI_AUTHENTICATION_FAILED", "message": str(exc)}) from exc
    except APIConnectionError as exc:
        raise HTTPException(status_code=503, detail=runtime_error(
            "AI_PROVIDER_UNAVAILABLE",
            "AI 서버에서 외부 AI 서비스에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.",
            retryable=True, legacy_code="AI_PROVIDER_CONNECTION_FAILED",
        )) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=runtime_error(
            "AI_SERVICE_UNAVAILABLE", "AI 분석을 완료하지 못했습니다. 다시 시도해 주세요.",
            retryable=True, legacy_code="AI_ANALYSIS_FAILED",
        )) from exc


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


@app.post("/ai/context/facts/extract", response_model=ContextFactExtractionOutput)
async def extract_context_facts(request: ContextFactExtractionInput) -> ContextFactExtractionOutput:
    """Extract typed, review-required proposals from one committed human message."""
    try:
        return await context_fact_extraction_service.extract(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "INVALID_CONTEXT_EXTRACTION_INPUT", "message": str(exc)}) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"code": "CONTEXT_FACT_EXTRACTION_FAILED", "message": str(exc)}) from exc


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
    except CaseCopilotProviderUnavailableError as exc:
        raise HTTPException(status_code=503, detail=runtime_error(
            "AI_PROVIDER_UNAVAILABLE",
            str(exc),
            retryable=True,
            legacy_code="AI_PROVIDER_CONNECTION_FAILED",
        )) from exc
    except CaseCopilotResponseError as exc:
        raise HTTPException(status_code=502, detail=runtime_error(
            "AI_INVALID_RESPONSE",
            str(exc),
            retryable=False,
            legacy_code="AI_WORK_CARD_CONTRACT_INVALID",
        )) from exc
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
