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
from pydantic import BaseModel

from contracts.diagnosis import AnalyzeTextRequest
from contracts.public_api.case_analyze import (
    PublicAnalyzeCaseRequest,
    PublicAnalyzeCaseResponse,
    PublicAnalyzeError,
    PublicInitialReportReference,
)
from contracts.public_api.case_read import PublicCaseReadResponse, to_public_case_read_response, to_public_case_summary_response
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
    PublicAnswerCustomerQuestionRequest,
    PublicCaseFactResponse,
    PublicConfirmCaseFactRequest,
    PublicPersonalNoteCreateRequest,
    PublicPersonalNoteUpdateRequest,
    PublicPersonalNoteResponse,
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
    PublicCustomerQuestionResponse,
    PublicCustomerQuestionView,
    PublicQuestionCandidateResponse,
    PublicQueueCustomerQuestionsRequest,
    PublicUpdateVerificationRequest,
    PublicVerificationResponse,
    to_public_action,
    to_public_verification,
)
from contracts.public_api.collaboration import (
    MessageChannel,
    PublicAiInvocationRequest,
    PublicAiInvocationResponse,
    PublicAiShareRequest,
    PublicCaseMemberResponse,
    PublicCaseMemberUpsertRequest,
    PublicCasePresenceResponse,
    PublicPresenceHeartbeatRequest,
    PublicPrimaryAssigneeRequest,
    PublicPrimaryAssigneeResponse,
)

from .clients.diagnosis_ai import AiServiceError, HttpDiagnosisAiClient
from .domains.cases.repository import CaseVersionConflictError, InMemoryCaseRepository
from .domains.cases.service import AnalyzeCaseService, InvalidCaseTransitionError, transition_case


load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)


def build_repository():
    repository_type = os.getenv("CASE_REPOSITORY", "sqlite").lower()
    if repository_type == "mysql":
        from .domains.cases.mysql_repository import MySqlCaseRepository
        return MySqlCaseRepository()
    if repository_type == "memory":
        return InMemoryCaseRepository()
    from .domains.cases.sqlite_repository import LocalSqliteCaseRepository
    return LocalSqliteCaseRepository()
    return InMemoryCaseRepository()

app = FastAPI(title="AI Independent Verification - General API", version="0.1.0")


class AdminCaseDeleteRequest(BaseModel):
    password: str


class CaseOutcomeRequest(BaseModel):
    expected_version: int
    victim_transfer_status: Literal["UNKNOWN", "YES", "NO"]
    actual_loss_amount_krw: float | None = None
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174", "http://localhost:5175", "http://127.0.0.1:5175"],
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


async def to_case_read(record: dict) -> PublicCaseReadResponse:
    members = await repository.list_members(record["case_id"])
    primary = next((item.get("display_name") for item in members if item.get("role") == "CASE_OWNER"), None)
    return to_public_case_read_response({**record, "primary_assignee": primary})


@app.get("/api/cases", response_model=list[PublicCaseReadResponse], response_model_exclude_none=True)
async def list_cases() -> list[PublicCaseReadResponse]:
    return [await to_case_read(record) for record in await repository.list()]


def require_admin_password(password: str) -> None:
    if password != os.getenv("CASE_ADMIN_DELETE_PASSWORD", "1234"):
        raise HTTPException(status_code=403, detail={"code": "ADMIN_AUTH_FAILED", "message": "관리자 비밀번호가 올바르지 않습니다."})


@app.post("/api/cases/admin/verify-password", status_code=204)
async def verify_admin_password(request: AdminCaseDeleteRequest) -> None:
    require_admin_password(request.password)


@app.get("/api/cases/trash", response_model=list[PublicCaseReadResponse], response_model_exclude_none=True)
async def list_trashed_cases() -> list[PublicCaseReadResponse]:
    return [await to_case_read(record) for record in await repository.list_trashed_cases()]


@app.delete("/api/cases/{case_id}", status_code=204)
async def permanently_delete_case(case_id: str, request: AdminCaseDeleteRequest) -> None:
    """Move the Case to the local recycle bin after administrator verification."""
    require_admin_password(request.password)
    try:
        await repository.delete_case(case_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found."}) from exc


@app.post("/api/cases/{case_id}/restore", status_code=204)
async def restore_case_from_trash(case_id: str) -> None:
    try:
        await repository.restore_case(case_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found in trash."}) from exc


@app.get("/api/cases/{case_id}", response_model=PublicCaseReadResponse, response_model_exclude_none=True)
async def get_case(case_id: str) -> PublicCaseReadResponse:
    record = await repository.get(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."})
    return await to_case_read(record)


@app.patch("/api/cases/{case_id}", response_model=PublicCaseReadResponse, response_model_exclude_none=True)
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
    return await to_case_read(record)


@app.put("/api/cases/{case_id}/outcome", response_model=PublicCaseReadResponse, response_model_exclude_none=True)
async def update_case_outcome(case_id: str, request: CaseOutcomeRequest) -> PublicCaseReadResponse:
    try:
        record = await repository.update_case(case_id, request.expected_version, {
            "victim_transfer_status": request.victim_transfer_status,
            "actual_loss_amount_krw": request.actual_loss_amount_krw if request.victim_transfer_status == "YES" else None,
        })
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found."}) from exc
    except CaseVersionConflictError as exc:
        raise HTTPException(status_code=409, detail={"code": "VERSION_CONFLICT", "message": "Case has changed.", "current_version": exc.current_version}) from exc
    return await to_case_read(record)


async def require_case(case_id: str) -> None:
    if await repository.get(case_id) is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."})


def build_customer_question_candidates(case: dict, queued: list[dict]) -> list[PublicQuestionCandidateResponse]:
    """Deterministic MVP candidates. AI may replace this source, not the queue contract."""
    already_handled = {item["target_field"] for item in queued if item.get("status") in {"PENDING", "ASKED", "ANSWERED"}}
    fields = [
        ("victim_transfer_status", "현재 송금하거나 이체한 금액이 있나요?", "피해 여부와 피해 금액을 먼저 확인해야 합니다.", "P0", ["없음", "있음", "잘 모르겠어요"]),
        ("remote_control_app", "휴대폰에 원격 제어 또는 화면 공유 앱을 설치하라는 안내를 받으셨나요?", "추가 피해 가능성을 확인해야 합니다.", "P0", ["설치함", "설치하지 않음", "잘 모르겠어요"]),
        ("credential_exposure", "비밀번호, 인증번호 또는 신분증 정보를 전달하셨나요?", "계정·인증정보 노출 여부를 확인해야 합니다.", "P1", ["전달함", "전달하지 않음", "잘 모르겠어요"]),
        ("impersonated_institution", "상대방이 어느 기관이나 은행을 사칭했는지 알려주실 수 있나요?", "공식 채널 검증 대상을 정해야 합니다.", "P1", []),
    ]
    if case.get("victim_transfer_status") != "UNKNOWN":
        already_handled.add("victim_transfer_status")
    return [
        PublicQuestionCandidateResponse(
            question_id=f"candidate-{target_field}", target_field=target_field,
            question_text=text, reason=reason, priority=priority, options=options,
        )
        for target_field, text, reason, priority, options in fields
        if target_field not in already_handled
    ]


@app.get("/api/cases/{case_id}/customer-question-candidates", response_model=list[PublicQuestionCandidateResponse])
async def list_customer_question_candidates(case_id: str) -> list[PublicQuestionCandidateResponse]:
    case = await repository.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."})
    return build_customer_question_candidates(case, await repository.list_customer_questions(case_id))


@app.get("/api/cases/{case_id}/customer-questions", response_model=list[PublicCustomerQuestionResponse | PublicCustomerQuestionView])
async def list_customer_questions(case_id: str, view: Literal["bank", "customer"] = "bank") -> list[PublicCustomerQuestionResponse | PublicCustomerQuestionView]:
    await require_case(case_id)
    items = await repository.list_customer_questions(case_id)
    if view == "customer":
        return [PublicCustomerQuestionView.model_validate(item) for item in items]
    return [PublicCustomerQuestionResponse.model_validate(item) for item in items]


@app.post("/api/cases/{case_id}/customer-questions", response_model=list[PublicCustomerQuestionResponse], status_code=201)
async def queue_customer_questions(case_id: str, request: PublicQueueCustomerQuestionsRequest) -> list[PublicCustomerQuestionResponse]:
    await require_case(case_id)
    try:
        items = await repository.queue_customer_questions(
            case_id, [item.model_dump() for item in request.questions], request.requested_by
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."}) from exc
    await dispatch_next_customer_question_message(case_id)
    return [PublicCustomerQuestionResponse.model_validate(item) for item in items]


async def dispatch_next_customer_question_message(case_id: str) -> PublicMessageResponse | None:
    """A confirmed queue is delivered one at a time through the public chat."""
    question = await repository.dispatch_next_customer_question(case_id)
    if question is None:
        return None
    message = await repository.append_message(case_id, {
        "actor_type": "CUSTOMER_AGENT", "actor_user_id": "customer-agent",
        "actor_display_name": "안전 상담 AI", "actor_role": "CUSTOMER_AGENT",
        "content": question["question_text"], "channel": "CUSTOMER", "audience": "CUSTOMER",
        "visibility": "CUSTOMER", "message_kind": "CHAT", "mentions": [], "log_event": False,
    })
    question["question_message_id"] = message["message_id"]
    return to_public_message(message)


@app.post("/api/cases/{case_id}/customer-questions/{question_id}/answer", response_model=PublicCustomerQuestionResponse)
async def answer_customer_question(case_id: str, question_id: str, request: PublicAnswerCustomerQuestionRequest) -> PublicCustomerQuestionResponse:
    await require_case(case_id)
    try:
        message = await repository.append_message(case_id, {
            "actor_type": "CUSTOMER", "actor_user_id": request.actor_user_id,
            "actor_display_name": request.actor_display_name, "actor_role": "CUSTOMER",
            "content": request.raw_answer, "channel": "CUSTOMER", "audience": "CUSTOMER",
            "visibility": "CUSTOMER", "message_kind": "CHAT", "mentions": [], "log_event": False,
        })
        answered = await repository.answer_customer_question(case_id, question_id, message["message_id"])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CUSTOMER_QUESTION_NOT_FOUND", "message": "응답 대기 중인 질문을 찾을 수 없습니다."}) from exc
    await repository.propose_case_fact(case_id, question_id, request.raw_answer, message["message_id"])
    await dispatch_next_customer_question_message(case_id)
    return PublicCustomerQuestionResponse.model_validate(answered)


@app.get("/api/cases/{case_id}/facts", response_model=list[PublicCaseFactResponse])
async def list_case_facts(case_id: str) -> list[PublicCaseFactResponse]:
    await require_case(case_id)
    return [PublicCaseFactResponse.model_validate(item) for item in await repository.list_case_facts(case_id)]


@app.post("/api/cases/{case_id}/facts/{fact_id}/confirm", response_model=PublicCaseFactResponse)
async def confirm_case_fact(case_id: str, fact_id: str, request: PublicConfirmCaseFactRequest) -> PublicCaseFactResponse:
    await require_case(case_id)
    try:
        return PublicCaseFactResponse.model_validate(await repository.confirm_case_fact(case_id, fact_id, request.confirmed_by))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CASE_FACT_NOT_FOUND", "message": "확정할 CaseFact를 찾을 수 없습니다."}) from exc


@app.get("/api/cases/{case_id}/personal-notes", response_model=list[PublicPersonalNoteResponse])
async def list_personal_notes(case_id: str, author_id: str) -> list[PublicPersonalNoteResponse]:
    await require_case(case_id)
    return [PublicPersonalNoteResponse.model_validate(item) for item in await repository.list_personal_notes(case_id, author_id)]


@app.post("/api/cases/{case_id}/personal-notes", response_model=PublicPersonalNoteResponse, status_code=201)
async def create_personal_note(case_id: str, request: PublicPersonalNoteCreateRequest) -> PublicPersonalNoteResponse:
    await require_case(case_id)
    return PublicPersonalNoteResponse.model_validate(await repository.create_personal_note(case_id, request.author_id, request.content))


@app.patch("/api/cases/{case_id}/personal-notes/{note_id}", response_model=PublicPersonalNoteResponse)
async def update_personal_note(case_id: str, note_id: str, request: PublicPersonalNoteUpdateRequest) -> PublicPersonalNoteResponse:
    await require_case(case_id)
    try:
        return PublicPersonalNoteResponse.model_validate(await repository.update_personal_note(case_id, note_id, request.author_id, request.content))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "PERSONAL_NOTE_NOT_FOUND", "message": "개인 메모를 찾을 수 없습니다."}) from exc


@app.delete("/api/cases/{case_id}/personal-notes/{note_id}", status_code=204)
async def delete_personal_note(case_id: str, note_id: str, author_id: str) -> None:
    await require_case(case_id)
    try:
        await repository.delete_personal_note(case_id, note_id, author_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "PERSONAL_NOTE_NOT_FOUND", "message": "개인 메모를 찾을 수 없습니다."}) from exc


@app.get("/api/cases/{case_id}/messages", response_model=list[PublicMessageResponse])
async def list_case_messages(case_id: str, channel: MessageChannel | None = None, view: Literal["bank", "customer"] = "bank") -> list[PublicMessageResponse]:
    await require_case(case_id)
    visible_channel = "CUSTOMER" if view == "customer" else channel
    messages = await repository.list_messages(case_id, visible_channel)
    if view == "customer":
        messages = [record for record in messages if record.get("visibility", record.get("audience")) == "CUSTOMER"]
    return [to_public_message(record) for record in messages]


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


@app.put("/api/cases/{case_id}/assignee", response_model=PublicPrimaryAssigneeResponse)
async def set_case_primary_assignee(case_id: str, request: PublicPrimaryAssigneeRequest) -> PublicPrimaryAssigneeResponse:
    try:
        display_name = await repository.set_primary_assignee(case_id, request.display_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found."}) from exc
    return PublicPrimaryAssigneeResponse(case_id=case_id, display_name=display_name)


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
    is_team_request = request.channel == "TEAM"
    message = await repository.append_message(case_id, {
        "actor_type": "BANK_AGENT", "actor_user_id": "case-copilot", "actor_display_name": "CaseCopilot",
        "actor_role": "BANK_AGENT", "content": content,
        "channel": "TEAM" if is_team_request else "AI_INTERNAL", "audience": "BANK_INTERNAL",
        "visibility": "BANK_INTERNAL" if is_team_request else "AI_PRIVATE", "message_kind": "AI_RESPONSE", "mentions": ["CaseCopilot"],
        "private_owner_user_id": None if is_team_request else request.requester_user_id, "client_request_id": request.client_request_id, "log_event": True,
    })
    return PublicAiInvocationResponse(
        invocation_id=f"ai-{uuid4().hex}", message_id=message["message_id"], case_id=case_id,
        channel="TEAM" if is_team_request else "AI_INTERNAL", content=content, model_mode="MVP_DETERMINISTIC", created_at=message["created_at"],
    )


@app.post("/api/cases/{case_id}/ai/messages/{message_id}/share", response_model=PublicMessageResponse, status_code=201)
async def share_ai_message_to_team(case_id: str, message_id: str, request: PublicAiShareRequest) -> PublicMessageResponse:
    await require_case(case_id)
    source = next((item for item in await repository.list_messages(case_id, "AI_INTERNAL") if item.get("message_id") == message_id), None)
    if source is None or source.get("actor_type") != "BANK_AGENT" or source.get("message_kind") != "AI_RESPONSE":
        raise HTTPException(status_code=404, detail={"code": "AI_MESSAGE_NOT_FOUND", "message": "공유할 AI 답변을 찾을 수 없습니다."})
    shared = await repository.append_message(case_id, {
        "actor_type": "BANK_AGENT", "actor_user_id": source.get("actor_user_id", "case-copilot"),
        "actor_display_name": source.get("actor_display_name", "CaseCopilot"), "actor_role": "BANK_AGENT",
        "content": source["content"], "channel": "TEAM", "audience": "BANK_INTERNAL",
        "visibility": "BANK_INTERNAL", "message_kind": "AI_RESPONSE", "mentions": ["CaseCopilot"],
        "reply_to_message_id": message_id, "shared_by_user_id": request.shared_by_user_id,
        "shared_by_display_name": request.shared_by_display_name, "log_event": True,
    })
    return to_public_message(shared)


@app.patch("/api/cases/{case_id}/verifications/{verification_task_id}", response_model=PublicVerificationResponse)
async def update_case_verification(case_id: str, verification_task_id: str, request: PublicUpdateVerificationRequest) -> PublicVerificationResponse:
    await require_case(case_id)
    try:
        return to_public_verification(await repository.update_verification(case_id, verification_task_id, request.expected_version, request.status, request.model_dump(exclude={"expected_version", "status"}, exclude_none=True)))
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
    if view == "customer":
        messages = [item for item in messages if item.get("visibility") == "CUSTOMER"]
        actions, verifications, events, voice = [], [], [], None
    return PublicCaseBundleResponse(
        case=to_public_case_summary_response(record).model_dump(mode="json"),
        live_report=None if view == "customer" else record.get("initial_report"),
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
