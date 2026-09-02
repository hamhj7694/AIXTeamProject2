from __future__ import annotations

import os
from uuid import uuid4
from pathlib import Path
from typing import Literal

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
from contracts.public_api.case_read import PublicCaseReadResponse, to_public_case_read_response
from contracts.public_api.case_transition import PublicCasePatchRequest
from contracts.public_api.case_activity import (
    PublicCaseEventResponse,
    PublicCreateMessageRequest,
    PublicMessageResponse,
    to_public_event,
    to_public_message,
)
from contracts.public_api.case_workflow import (
    PublicActionResponse,
    PublicCaseBundleResponse,
    PublicCreateActionRequest,
    PublicActionCommandRequest,
    PublicCreateVoiceSessionRequest,
    PublicUpdateVoiceSessionRequest,
    PublicVoiceSessionResponse,
    PublicCreateTranscriptRequest,
    PublicTranscriptResponse,
    PublicFinalizeReportRequest,
    PublicReportResponse,
    PublicCreateVerificationRequest,
    PublicUpdateVerificationRequest,
    PublicVerificationResponse,
    to_public_action,
    to_public_verification,
)
from contracts.public_api.collaboration import (
    MessageChannel,
    PublicAiInvocationRequest,
    PublicAiInvocationResponse,
    PublicCaseMemberResponse,
    PublicCaseMemberUpsertRequest,
    PublicCasePresenceResponse,
    PublicPresenceHeartbeatRequest,
)

from .clients.diagnosis_ai import AiServiceError, HttpDiagnosisAiClient
from .domains.cases.repository import CaseVersionConflictError, InMemoryCaseRepository
from .domains.cases.service import AnalyzeCaseService, InvalidCaseTransitionError, transition_case


load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)


def build_repository():
    if os.getenv("CASE_REPOSITORY", "memory").lower() == "mysql":
        from .domains.cases.mysql_repository import MySqlCaseRepository
        return MySqlCaseRepository()
    return InMemoryCaseRepository()

app = FastAPI(title="AI Independent Verification - General API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
repository = build_repository()
service = AnalyzeCaseService(HttpDiagnosisAiClient(), repository)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or f"req-{uuid4().hex}"
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


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


@app.get("/api/cases", response_model=list[PublicCaseReadResponse])
async def list_cases() -> list[PublicCaseReadResponse]:
    return [to_public_case_read_response(record) for record in await repository.list()]


@app.get("/api/cases/{case_id}", response_model=PublicCaseReadResponse)
async def get_case(case_id: str) -> PublicCaseReadResponse:
    record = await repository.get(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."})
    return to_public_case_read_response(record)


@app.patch("/api/cases/{case_id}", response_model=PublicCaseReadResponse)
async def patch_case(case_id: str, request: PublicCasePatchRequest) -> PublicCaseReadResponse:
    try:
        record = await transition_case(
            repository,
            case_id,
            request.expected_version,
            status=request.status,
            mode=request.mode,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found."}) from exc
    except CaseVersionConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "VERSION_CONFLICT", "message": "Case has changed.", "current_version": exc.current_version},
        ) from exc
    except InvalidCaseTransitionError as exc:
        raise HTTPException(status_code=409, detail={"code": "INVALID_STATE_TRANSITION", "message": str(exc)}) from exc
    return to_public_case_read_response(record)


async def require_case(case_id: str) -> None:
    if await repository.get(case_id) is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."})


@app.get("/api/cases/{case_id}/messages", response_model=list[PublicMessageResponse])
async def list_case_messages(case_id: str, channel: MessageChannel | None = None) -> list[PublicMessageResponse]:
    await require_case(case_id)
    return [to_public_message(record) for record in await repository.list_messages(case_id, channel)]


@app.post("/api/cases/{case_id}/messages", response_model=PublicMessageResponse, status_code=201)
async def create_case_message(case_id: str, request: PublicCreateMessageRequest) -> PublicMessageResponse:
    await require_case(case_id)
    try:
        record = await repository.append_message(case_id, request.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."}) from exc
    return to_public_message(record)


@app.get("/api/cases/{case_id}/events", response_model=list[PublicCaseEventResponse])
async def list_case_events(case_id: str, after: int | None = None) -> list[PublicCaseEventResponse]:
    await require_case(case_id)
    return [to_public_event(record) for record in await repository.list_events(case_id, after)]


@app.get("/api/cases/{case_id}/members", response_model=list[PublicCaseMemberResponse])
async def list_case_members(case_id: str) -> list[PublicCaseMemberResponse]:
    await require_case(case_id)
    return [PublicCaseMemberResponse.model_validate(item) for item in await repository.list_members(case_id)]


@app.post("/api/cases/{case_id}/members", response_model=PublicCaseMemberResponse, status_code=201)
async def upsert_case_member(case_id: str, request: PublicCaseMemberUpsertRequest) -> PublicCaseMemberResponse:
    await require_case(case_id)
    try:
        return PublicCaseMemberResponse.model_validate(await repository.upsert_member(case_id, request.model_dump()))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."}) from exc


@app.get("/api/cases/{case_id}/presence", response_model=list[PublicCasePresenceResponse])
async def list_case_presence(case_id: str) -> list[PublicCasePresenceResponse]:
    await require_case(case_id)
    return [PublicCasePresenceResponse.model_validate(item) for item in await repository.list_presence(case_id)]


@app.post("/api/cases/{case_id}/presence/heartbeat", response_model=PublicCasePresenceResponse)
async def heartbeat_case_presence(case_id: str, request: PublicPresenceHeartbeatRequest) -> PublicCasePresenceResponse:
    await require_case(case_id)
    try:
        return PublicCasePresenceResponse.model_validate(await repository.heartbeat_presence(case_id, request.model_dump()))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."}) from exc


def build_mvp_copilot_reply(case: dict, verifications: list[dict], prompt: str) -> str:
    unresolved = [item.get("claim", "추가 확인 항목") for item in verifications if item.get("status") != "COMPLETED"]
    unresolved_text = ", ".join(unresolved[:3]) or "추가 확인 항목이 아직 등록되지 않았습니다."
    return (
        f"[MVP CaseCopilot] 요청: {prompt.strip()}\n\n"
        f"현재 Case는 {case.get('status', 'TRIAGE')} 상태이며, 요약은 “{case.get('initial_brief', '확인안됨')}”입니다.\n"
        f"미완료 검증: {unresolved_text}\n"
        "다음 단계로 고객에게 확인할 사실을 한 번에 하나씩 정리하고, 고객 전송 전 담당자 승인을 받으세요."
    )


@app.post("/api/cases/{case_id}/ai/invocations", response_model=PublicAiInvocationResponse, status_code=201)
async def invoke_case_copilot(case_id: str, request: PublicAiInvocationRequest) -> PublicAiInvocationResponse:
    case = await repository.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."})
    content = build_mvp_copilot_reply(case, await repository.list_verifications(case_id), request.prompt)
    message = await repository.append_message(case_id, {
        "actor_type": "BANK_AGENT", "content": content, "channel": "AI_INTERNAL", "audience": "BANK_INTERNAL",
        "mentions": ["CaseCopilot"], "client_request_id": request.client_request_id,
    })
    return PublicAiInvocationResponse(
        invocation_id=f"ai-{uuid4().hex}", message_id=message["message_id"], case_id=case_id,
        channel="AI_INTERNAL", content=content, model_mode="MVP_DETERMINISTIC", created_at=message["created_at"],
    )


@app.patch("/api/cases/{case_id}/verifications/{verification_task_id}", response_model=PublicVerificationResponse)
async def update_case_verification(case_id: str, verification_task_id: str, request: PublicUpdateVerificationRequest) -> PublicVerificationResponse:
    await require_case(case_id)
    try:
        return to_public_verification(await repository.update_verification(case_id, verification_task_id, request.expected_version, request.status))
    except CaseVersionConflictError as exc:
        raise HTTPException(status_code=409, detail={"code": "VERSION_CONFLICT", "message": "Verification task has changed.", "current_version": exc.current_version}) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "VERIFICATION_NOT_FOUND", "message": "Verification task not found."}) from exc


@app.get("/api/cases/{case_id}/verifications", response_model=list[PublicVerificationResponse])
async def list_case_verifications(case_id: str) -> list[PublicVerificationResponse]:
    await require_case(case_id)
    return [to_public_verification(record) for record in await repository.list_verifications(case_id)]


@app.post("/api/cases/{case_id}/verifications", response_model=PublicVerificationResponse, status_code=201)
async def create_case_verification(case_id: str, request: PublicCreateVerificationRequest) -> PublicVerificationResponse:
    await require_case(case_id)
    try:
        return to_public_verification(await repository.create_verification(case_id, request.model_dump()))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."}) from exc


@app.get("/api/cases/{case_id}/actions", response_model=list[PublicActionResponse])
async def list_case_actions(case_id: str) -> list[PublicActionResponse]:
    await require_case(case_id)
    return [to_public_action(record) for record in await repository.list_actions(case_id)]


@app.post("/api/cases/{case_id}/actions", response_model=PublicActionResponse, status_code=201)
async def create_case_action(case_id: str, request: PublicCreateActionRequest) -> PublicActionResponse:
    await require_case(case_id)
    try:
        return to_public_action(await repository.create_action(case_id, request.model_dump()))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."}) from exc


async def create_case_control_action(case_id: str, action_type: str, request: PublicActionCommandRequest) -> PublicActionResponse:
    await require_case(case_id)
    try:
        return to_public_action(await repository.create_action(case_id, {"action_type": action_type, "actor_type": "BANK_STAFF", "note": request.note}))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found."}) from exc


@app.post("/api/cases/{case_id}/takeover", response_model=PublicActionResponse, status_code=201)
async def start_human_takeover(case_id: str, request: PublicActionCommandRequest) -> PublicActionResponse:
    return await create_case_control_action(case_id, "HUMAN_TAKEOVER", request)


@app.post("/api/cases/{case_id}/resume", response_model=PublicActionResponse, status_code=201)
async def resume_ai(case_id: str, request: PublicActionCommandRequest) -> PublicActionResponse:
    return await create_case_control_action(case_id, "RESUME_AI", request)


@app.get("/api/cases/{case_id}/bundle", response_model=PublicCaseBundleResponse)
async def get_case_bundle(case_id: str, view: Literal["entry", "customer", "bank"] = "entry") -> PublicCaseBundleResponse:
    record = await repository.get(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."})
    # A customer bundle must never carry staff or AI-internal messages. The
    # dedicated messages endpoint applies the same channel constraint.
    visible_channel = "CUSTOMER" if view == "customer" else None
    messages = [to_public_message(item).model_dump(mode="json") for item in await repository.list_messages(case_id, visible_channel)]
    actions = [to_public_action(item) for item in await repository.list_actions(case_id)]
    verifications = [to_public_verification(item) for item in await repository.list_verifications(case_id)]
    events = [to_public_event(item).model_dump(mode="json") for item in await repository.list_events(case_id)]
    voice = await repository.get_voice_session(case_id)
    return PublicCaseBundleResponse(
        case=to_public_case_read_response(record).model_dump(mode="json"),
        live_report=record.get("initial_report"),
        questions=[], progress_items=[], verification_tasks=verifications,
        recent_messages=messages[-50:], recent_actions=actions[-50:], recent_events=events[-50:],
        voice_session=PublicVoiceSessionResponse.model_validate(voice) if voice else None, cursor=str(events[-1]["event_id"]) if events else None,
    )


@app.post("/api/cases/{case_id}/voice-sessions", response_model=PublicVoiceSessionResponse, status_code=201)
async def create_voice_session(case_id: str, request: PublicCreateVoiceSessionRequest) -> PublicVoiceSessionResponse:
    await require_case(case_id)
    try:
        return PublicVoiceSessionResponse.model_validate(await repository.create_voice_session(case_id, request.participants))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found."}) from exc


@app.patch("/api/cases/{case_id}/voice-sessions/{session_id}", response_model=PublicVoiceSessionResponse)
async def update_voice_session(case_id: str, session_id: str, request: PublicUpdateVoiceSessionRequest) -> PublicVoiceSessionResponse:
    await require_case(case_id)
    try:
        return PublicVoiceSessionResponse.model_validate(await repository.update_voice_session(case_id, session_id, request.status))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "VOICE_SESSION_NOT_FOUND", "message": "Voice session not found."}) from exc


@app.get("/api/cases/{case_id}/voice-sessions/{session_id}/transcript", response_model=list[PublicTranscriptResponse])
async def list_voice_transcript(case_id: str, session_id: str) -> list[PublicTranscriptResponse]:
    await require_case(case_id)
    return [PublicTranscriptResponse.model_validate(item) for item in await repository.list_transcript(case_id, session_id)]


@app.post("/api/cases/{case_id}/voice-sessions/{session_id}/transcript", response_model=PublicTranscriptResponse, status_code=201)
async def append_voice_transcript(case_id: str, session_id: str, request: PublicCreateTranscriptRequest) -> PublicTranscriptResponse:
    await require_case(case_id)
    try:
        return PublicTranscriptResponse.model_validate(await repository.append_transcript(case_id, session_id, request.model_dump()))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "VOICE_SESSION_NOT_FOUND", "message": "Voice session not found."}) from exc


@app.get("/api/cases/{case_id}/reports/live")
async def get_live_report(case_id: str) -> dict:
    record = await repository.get(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."})
    return record["initial_report"]


@app.post("/api/cases/{case_id}/reports/finalize", response_model=PublicReportResponse)
async def finalize_case_report(case_id: str, request: PublicFinalizeReportRequest) -> PublicReportResponse:
    try:
        report = await repository.finalize_report(case_id, request.expected_version, request.note)
    except CaseVersionConflictError as exc:
        raise HTTPException(status_code=409, detail={"code": "VERSION_CONFLICT", "message": "Case has changed.", "current_version": exc.current_version}) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found."}) from exc
    return PublicReportResponse.model_validate(report)


@app.get("/api/cases/{case_id}/reports/final", response_model=PublicReportResponse)
async def get_final_case_report(case_id: str) -> PublicReportResponse:
    await require_case(case_id)
    report = await repository.get_final_report(case_id)
    if report is None:
        raise HTTPException(status_code=404, detail={"code": "FINAL_REPORT_NOT_FOUND", "message": "Final report not found."})
    return PublicReportResponse.model_validate(report)
