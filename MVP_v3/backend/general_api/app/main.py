from __future__ import annotations

import asyncio
import io
import json
import os
import hashlib
import logging
import mimetypes
import re
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator
from .domains.cases.context_items import Section, ContextItemChange, ContextItemConflictError
from .domains.cases.context_item_repository import ContextItemRepository, InMemoryContextItemRepository
from .core.actor_context import normalize_legacy_actor

from contracts.diagnosis import AnalyzeTextRequest
from contracts.ai_internal.context_fact_extraction import ContextFactExtractionInput, ContextFactExtractionMessage, ExistingContextFact
from contracts.ai_internal.mvp_workflow import TargetField
from ai_api.app.domains.case_support.answer_service import CustomerAnswerStructuringService
from contracts.public_api.customer_progress import CustomerProgressItem, ProgressStep, UpdateCustomerProgress
from .domains.cases.customer_progress import PREFIX as PROGRESS_PREFIX, ProgressConflict, progress_items as build_customer_progress, progress_ai_context, actions_for_ai
from request_trace import install_request_trace
from contracts.ai_internal.work_card import CaseWorkCardOutput, WorkCardType
from contracts.user_text import user_text
from .domains.cases.context_workspace import build_workspace, legacy_gap_details
from .domains.cases.case_retrieval import SEMANTIC_FIELDS, collect_records, retrieve_context, similar_question, staff_context, workspace_records, merge_support_records
from contracts.public_api.case_analyze import (
    PublicAnalyzeCaseRequest,
    PublicAnalyzeCaseResponse,
    PublicAnalyzeError,
    PublicInitialReportReference,
)
from contracts.public_api.case_read import PublicCaseReadResponse, to_public_case_read_response, to_public_case_summary_response
from contracts.public_api.case_transition import PublicCasePatchRequest
from contracts.public_api.case_context_v2 import (
    PublicAiSuggestionV2,
    PublicCancelTaskV2Request,
    PublicCaseContextResourcesV2,
    PublicCaseFactV2,
    PublicCaseGapV2,
    PublicCaseTaskV2,
    PublicContextPanelV3,
    PublicCompleteTaskV2Request,
    PublicCreateDecisionV2Request,
    PublicCreateFactV2Request,
    PublicCreateGapV2Request,
    PublicCreateTaskV2Request,
    PublicDecisionRecordV2,
    PublicReviewFactV2Request,
    PublicReviewSuggestionV2Request,
    PublicSuggestionReviewResultV2,
    PublicUpdateGapV2Request,
    PublicUpdateTaskV2Request,
)
from contracts.public_api.case_activity import (
    PublicCaseEventResponse,
    PublicAttachmentResponse,
    PublicCreateMessageRequest,
    PublicCustomerEmergencyRequest,
    PublicMessageResponse,
    to_public_event,
    to_public_attachment,
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
    PublicUpdateActionRequest,
    PublicActionCommandRequest,
    PublicCreateVoiceSessionRequest,
    PublicUpdateVoiceSessionRequest,
    PublicVoiceSessionResponse,
    PublicCreateTranscriptRequest,
    PublicTranscriptResponse,
    PublicReportResponse,
    PublicCreateVerificationRequest,
    PublicCustomerQuestionResponse,
    PublicCustomerQuestionView,
    PublicCustomerVerificationResult,
    PublicQuestionCandidateResponse,
    PublicCaseContextProjection,
    PublicCaseSupportBrief,
    PublicCaseSupportSnapshotResponse,
    PublicUnresolvedItemResponse,
    PublicQueueCustomerQuestionsRequest,
    PublicUpdateVerificationRequest,
    PublicVerificationResponse,
    to_public_customer_question,
    to_public_customer_question_view,
    question_option_items,
    to_public_action,
    to_public_verification,
)
from contracts.public_api.collaboration import (
    MessageChannel,
    PublicAiInvocationRequest,
    PublicAiInvocationResponse,
    PublicAiShareRequest,
    PublicCustomerAiReplyRequest,
    PublicCaseMemberResponse,
    PublicCaseMemberUpsertRequest,
    PublicCasePresenceResponse,
    PublicPresenceHeartbeatRequest,
    PublicPrimaryAssigneeRequest,
    PublicPrimaryAssigneeResponse,
)

from .clients.diagnosis_ai import AiServiceAuthenticationError, AiServiceError, AiServiceQuotaError, HttpDiagnosisAiClient
from .domains.cases.repository import CasePersistenceError, CaseVersionConflictError, normalize_target_field
from .domains.cases.context_projection_repository import ContextProjectionRepository
from .domains.cases.case_context_v2_repository import (
    ContextV2ConflictError,
    ContextV2TransitionError,
    InMemoryCaseContextV2Repository,
    MySqlCaseContextV2Repository,
)
from .domains.cases.mysql_repository import MySqlCaseRepository
from .domains.cases.context_v3.semantic_keys import ALLOWED_SEMANTIC_KEYS, SEMANTIC_LABELS, proposal_dedupe_key
from .domains.cases.context_v3.panel import build_context_panel_v3
from .domains.cases.context_v3.atom_fact_projection import project_semantic_atoms_to_fact_candidates
from .domains.cases.service import AnalyzeCaseService, InvalidCaseTransitionError, transition_case


load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)


def build_repository():
    repository_type = os.getenv("CASE_REPOSITORY", "mysql").lower()
    if repository_type == "mysql":
        return MySqlCaseRepository()
    raise RuntimeError(f"Unsupported CASE_REPOSITORY: {repository_type}. Use mysql in deployed environments.")

app = FastAPI(title="AI Independent Verification - General API", version="0.1.0")
install_request_trace(app, "general-api")
logger = logging.getLogger(__name__)

AUTONOMOUS_P0_QUESTION_FIELDS = {
    "transfer_status",
    "personal_information_exposure",
    "authentication_information_exposure",
    "remote_control_app",
}
BASELINE_QUESTION_FIELDS = AUTONOMOUS_P0_QUESTION_FIELDS | {"impersonated_institution"}
AI_CHECKLIST_ACTION_PREFIX = "AI_CHECKLIST:"
STAFF_JUDGMENT_ACTION_TYPE = "STAFF_JUDGMENT"
CHECKLIST_FIELD_LABELS = {
    "transfer_status": "실제 송금 여부",
    "transfer_purpose": "송금 목적",
    "claimed_organization": "사칭 기관",
    "incident_claim": "상대방 주장",
    "personal_information_exposure": "개인정보 제공 여부",
    "authentication_information_exposure": "인증정보 제공 여부",
    "remote_control_app": "원격제어 앱 설치 여부",
}
PROACTIVE_CASE_POLL_SECONDS = max(1.0, float(os.getenv("PROACTIVE_CASE_POLL_SECONDS", "3")))
_proactive_case_revisions: dict[str, str] = {}
_proactive_worker_task: asyncio.Task | None = None


class AdminCaseDeleteRequest(BaseModel):
    password: str


class AdminCaseFinalizeRequest(BaseModel):
    expected_version: int = Field(ge=1)
    password: str
    note: str = Field(default="", max_length=10_000)


class AdminCaseReopenRequest(BaseModel):
    expected_version: int = Field(ge=1)
    password: str


class CaseOutcomeRequest(BaseModel):
    expected_version: int
    victim_transfer_status: Literal["UNKNOWN", "YES", "NO"]
    actual_loss_amount_krw: float | None = None


class PublicWorkCardGenerateRequest(BaseModel):
    card_type: WorkCardType
    question_drafts: list[PublicQuestionCandidateResponse] = Field(default_factory=list, max_length=20)


default_cors_origins = (
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:5174,http://127.0.0.1:5174,"
    "http://localhost:5175,http://127.0.0.1:5175,"
    "http://localhost:5176,http://127.0.0.1:5176"
)
cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", default_cors_origins).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
repository = build_repository()

ATTACHMENT_STORAGE_ROOT = Path(os.getenv("ATTACHMENT_STORAGE_ROOT", str(Path(__file__).resolve().parents[2] / "data" / "uploads"))).resolve()
MAX_ATTACHMENT_BYTES = int(os.getenv("MAX_ATTACHMENT_BYTES", str(10 * 1024 * 1024)))
ALLOWED_ATTACHMENT_TYPES = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif", "image/webp": ".webp",
    "application/pdf": ".pdf", "text/plain": ".txt", "text/csv": ".csv", "application/json": ".json",
    "application/msword": ".doc", "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}


def _clean_file_name(value: str) -> str:
    name = Path(value).name
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()
    return name[:160] or "attachment"


def _resolve_attachment_type(file_name: str, content_type: str | None) -> tuple[str, str]:
    candidate = (content_type or "").split(";", 1)[0].strip().lower()
    if candidate not in ALLOWED_ATTACHMENT_TYPES:
        candidate = (mimetypes.guess_type(file_name)[0] or "").lower()
    extension = ALLOWED_ATTACHMENT_TYPES.get(candidate)
    if not extension:
        raise HTTPException(status_code=415, detail={"code": "ATTACHMENT_TYPE_NOT_ALLOWED", "message": "지원하지 않는 파일 형식입니다."})
    return candidate, extension


def _has_valid_signature(mime_type: str, content: bytes) -> bool:
    signatures = {
        "image/jpeg": lambda value: value.startswith(b"\xff\xd8\xff"),
        "image/png": lambda value: value.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/gif": lambda value: value.startswith((b"GIF87a", b"GIF89a")),
        "image/webp": lambda value: len(value) >= 12 and value[:4] == b"RIFF" and value[8:12] == b"WEBP",
        "application/pdf": lambda value: value.startswith(b"%PDF-"),
        "application/msword": lambda value: value.startswith(b"\xd0\xcf\x11\xe0"),
        "application/vnd.ms-excel": lambda value: value.startswith(b"\xd0\xcf\x11\xe0"),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": lambda value: value.startswith(b"PK\x03\x04"),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": lambda value: value.startswith(b"PK\x03\x04"),
    }
    validator = signatures.get(mime_type)
    if validator:
        return validator(content)
    if mime_type.startswith("text/") or mime_type == "application/json":
        try:
            content.decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False
    return True
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


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "general-api", "status": "ok", "health": "/health"}


@app.get("/health")
async def health() -> dict[str, str]:
    repository_type = os.getenv("CASE_REPOSITORY", "mysql").lower()
    ping = getattr(repository, "ping", None)
    if callable(ping):
        try:
            await ping()
        except Exception as error:
            logger.exception("Database health check failed")
            raise HTTPException(
                status_code=503,
                detail={"code": "DATABASE_UNAVAILABLE", "message": "데이터베이스에 연결할 수 없습니다."},
            ) from error
    return {"status": "ok", "database": repository_type}


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
        result = await service.analyze(internal_request)
        if result.disposition == "CASE_CREATED" and result.case_id:
            try:
                await seed_initial_context_facts(result.case_id)
            except Exception:
                logger.exception("Case was committed but initial Context V3 facts could not be seeded")
        return to_public_analyze_response(result)
    except ValueError as exc:
        failure = public_failed_response("INVALID_INPUT", str(exc), retryable=False)
        return JSONResponse(status_code=400, content=failure.model_dump(mode="json"))
    except AiServiceQuotaError as exc:
        failure = public_failed_response("OPENAI_QUOTA_EXHAUSTED", str(exc), retryable=False)
        return JSONResponse(status_code=429, content=failure.model_dump(mode="json"))
    except AiServiceAuthenticationError as exc:
        failure = public_failed_response("OPENAI_AUTHENTICATION_FAILED", str(exc), retryable=False)
        return JSONResponse(status_code=401, content=failure.model_dump(mode="json"))
    except AiServiceError as exc:
        failure = public_failed_response("AI_ANALYSIS_FAILED", str(exc), retryable=True)
        return JSONResponse(status_code=503, content=failure.model_dump(mode="json"))
    except CasePersistenceError:
        failure = public_failed_response("CASE_SAVE_FAILED", "AI 분석 후 사건 저장을 완료하지 못했습니다.", retryable=True)
        return JSONResponse(status_code=503, content=failure.model_dump(mode="json"))
    except Exception as exc:
        failure = public_failed_response("AI_ANALYSIS_FAILED", "진단을 완료하지 못했습니다.", retryable=True)
        return JSONResponse(status_code=503, content=failure.model_dump(mode="json"))


async def to_case_read(record: dict) -> PublicCaseReadResponse:
    members = await repository.list_members(record["case_id"])
    primary = next((item.get("display_name") for item in members if item.get("role") == "CASE_OWNER"), None)
    deleted_at = record.get("deleted_at")
    trash_expires_at = None
    if deleted_at:
        deleted_instant = datetime.fromisoformat(str(deleted_at).replace("Z", "+00:00"))
        if deleted_instant.tzinfo is None:
            deleted_instant = deleted_instant.replace(tzinfo=timezone.utc)
        trash_expires_at = (deleted_instant + timedelta(days=30)).isoformat()
    return to_public_case_read_response({
        **record,
        "primary_assignee": primary,
        "trash_expires_at": trash_expires_at,
    })


@app.get("/api/cases", response_model=list[PublicCaseReadResponse], response_model_exclude_none=True)
async def list_cases() -> list[PublicCaseReadResponse]:
    return [await to_case_read(record) for record in await repository.list()]


def require_admin_password(password: str) -> None:
    configured_password = os.getenv("CASE_ADMIN_DELETE_PASSWORD")
    if not configured_password:
        raise HTTPException(status_code=503, detail={"code": "ADMIN_AUTH_NOT_CONFIGURED", "message": "관리자 인증 설정이 필요합니다."})
    if not secrets.compare_digest(password, configured_password):
        raise HTTPException(status_code=403, detail={"code": "ADMIN_AUTH_FAILED", "message": "관리자 비밀번호가 올바르지 않습니다."})


@app.post("/api/cases/admin/verify-password", status_code=204)
async def verify_admin_password(request: AdminCaseDeleteRequest) -> None:
    require_admin_password(request.password)


@app.get("/api/cases/trash", response_model=list[PublicCaseReadResponse], response_model_exclude_none=True)
async def list_trashed_cases() -> list[PublicCaseReadResponse]:
    return [await to_case_read(record) for record in await repository.list_trashed_cases()]


@app.post("/api/cases/{case_id}/trash", status_code=204)
async def move_case_to_trash(case_id: str, request: AdminCaseDeleteRequest) -> None:
    """Keep a Case in trash for 30 days after administrator verification."""
    require_admin_password(request.password)
    try:
        await repository.delete_case(case_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found."}) from exc


@app.delete("/api/cases/{case_id}", status_code=204)
async def move_case_to_trash_legacy(case_id: str, request: AdminCaseDeleteRequest) -> None:
    """Backward-compatible alias for moving a Case to trash."""
    await move_case_to_trash(case_id, request)


@app.post("/api/cases/{case_id}/restore", status_code=204)
async def restore_case_from_trash(case_id: str, request: AdminCaseDeleteRequest) -> None:
    require_admin_password(request.password)
    try:
        await repository.restore_case(case_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found in trash."}) from exc


@app.delete("/api/cases/trash/{case_id}", status_code=204)
async def permanently_delete_trashed_case(case_id: str, request: AdminCaseDeleteRequest) -> None:
    require_admin_password(request.password)
    attachments = await repository.list_attachments(case_id)
    try:
        await repository.purge_case(case_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found in trash."}) from exc
    for attachment in attachments:
        stored_path = (ATTACHMENT_STORAGE_ROOT / attachment["storage_path"]).resolve()
        if ATTACHMENT_STORAGE_ROOT not in stored_path.parents:
            logger.error("Skipped unsafe attachment path during Case purge: %s", stored_path)
            continue
        try:
            stored_path.unlink(missing_ok=True)
        except OSError:
            logger.exception("Failed to remove attachment after Case purge: %s", stored_path)


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
            case_name=request.case_name,
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


def _message_is_context_extractable(message: dict) -> bool:
    return (
        message.get("actor_type") in {"CUSTOMER", "BANK_STAFF"}
        and message.get("message_kind", "CHAT") == "CHAT"
        and message.get("visibility") != "AI_PRIVATE"
        and bool(str(message.get("content", "")).strip())
    )


async def process_message_context_extraction(case_id: str, message_id: str) -> None:
    """Process one durable extraction job; failures remain available for bounded retry."""
    job = await repository.claim_message_extraction(message_id)
    if job is None:
        return
    try:
        message = next((item for item in await repository.list_messages(case_id) if item.get("message_id") == message_id), None)
        if message is None or not _message_is_context_extractable(message):
            await repository.complete_message_extraction(message_id, "not-applicable", "context-fact-v1")
            return
        store = case_context_v2_repository()
        resources = await store.list_resources(case_id)
        existing = [
            ExistingContextFact(fact_id=item.fact_id, semantic_key=item.semantic_key, value=item.value, status=item.status)
            for item in resources.facts if item.semantic_key in ALLOWED_SEMANTIC_KEYS
        ]
        output = await service.ai_client.extract_context_facts(ContextFactExtractionInput(
            message=ContextFactExtractionMessage(
                message_id=message_id, case_id=case_id, actor_type=message["actor_type"],
                content=message["content"], created_at=message.get("created_at"),
            ), existing_facts=existing,
        ))
        for proposal in output.proposals:
            if proposal.semantic_key not in ALLOWED_SEMANTIC_KEYS or proposal.evidence_message_id != message_id:
                raise ValueError("AI extraction returned an out-of-contract proposal")
            await store.create_fact(case_id, {
                "client_request_id": proposal_dedupe_key(message_id, proposal.semantic_key, proposal.value),
                "semantic_key": proposal.semantic_key, "display_label": proposal.display_label,
                "value": proposal.value, "display_value": proposal.display_value,
                "confidence": proposal.confidence,
                "evidence_refs": [{"type": "MESSAGE", "id": message_id}], "visibility": "BANK_INTERNAL",
            }, message.get("actor_user_id") or "context-extractor",
                source_kind="CUSTOMER_STATEMENT" if message["actor_type"] == "CUSTOMER" else "STAFF_OBSERVATION")
        await repository.complete_message_extraction(message_id, output.model_version, output.prompt_version)
    except Exception as exc:
        logger.exception("Context fact extraction failed for message %s", message_id)
        await repository.fail_message_extraction(message_id, str(exc))


async def enqueue_context_extraction(record: dict, background_tasks: BackgroundTasks | None = None) -> None:
    if not _message_is_context_extractable(record):
        return
    await repository.enqueue_message_extraction(record["case_id"], record["message_id"])
    if background_tasks is not None:
        background_tasks.add_task(process_message_context_extraction, record["case_id"], record["message_id"])


async def seed_initial_context_facts(case_id: str) -> None:
    """Seed reviewable canonical facts from the persisted diagnosis, never from discarded raw input."""
    case = await repository.get(case_id)
    if not case:
        return
    diagnosis = case.get("diagnosis") or {}
    context = diagnosis.get("context") or {}
    diagnosis_signals = diagnosis.get("context_signals") or []
    diagnosis_atoms = diagnosis.get("semantic_atoms") or []
    if diagnosis_signals:
        base_evidence_ref = {"type": "STRUCTURED_SIGNAL", "id": str(diagnosis_signals[0].get("signal_id"))}
    elif diagnosis_atoms:
        base_evidence_ref = {"type": "STRUCTURED_ATOM", "id": str(diagnosis_atoms[0].get("atom_id"))}
    else:
        base_evidence_ref = {"type": "STAFF_RECORD", "id": str((case.get("initial_report") or {}).get("report_id") or case_id)}
    candidates: list[tuple[str, str, dict, str]] = []
    transfer = case.get("victim_transfer_status")
    if transfer in {"YES", "NO"}:
        candidates.append(("transfer.actual.status", "실제 이체 여부", {"status": "TRANSFERRED" if transfer == "YES" else "NOT_TRANSFERRED"}, "이체함" if transfer == "YES" else "이체하지 않음"))
    features = diagnosis.get("features") or {}
    context_features = diagnosis.get("case_context_features") or {}
    amount_values: list[int] = []
    raw_amount_values = [
        *(context_features.get("requested_amount_values_krw") or []),
        *[
            atom.get("amount_value_krw")
            for atom in diagnosis_atoms
            if atom.get("amount_value_krw") is not None and atom.get("action_state") == "REQUESTED"
        ],
    ]
    for raw_amount in raw_amount_values:
        try:
            amount = int(float(raw_amount))
        except (TypeError, ValueError):
            continue
        if amount > 0 and amount not in amount_values:
            amount_values.append(amount)
    if not amount_values:
        fallback_amount = int(float(features.get("requested_amount_max") or 0))
        if fallback_amount > 0:
            amount_values.append(fallback_amount)
    for amount in amount_values:
        candidates.append(("transfer.requested.amount", "요구 금액", {"amount_krw": amount, "currency": "KRW"}, f"{amount:,}원 요구"))
    actual_amount = int(float(case.get("actual_loss_amount_krw") or 0))
    if transfer == "YES" and actual_amount > 0:
        candidates.append(("transfer.actual.amount", "실제 이체 금액", {"amount_krw": actual_amount, "currency": "KRW"}, f"{actual_amount:,}원 이체"))
    requested_codes = {str(code).upper() for code in context_features.get("requested_action_codes", [])}
    requested_action_facts = {
        "REQUEST_AUTH_INFO": ("exposure.authentication_information", "인증정보 노출", {"status": "REQUESTED"}, "인증정보 제공 요구"),
        "REQUEST_PERSONAL_INFO": ("exposure.personal_information", "개인정보 노출", {"status": "REQUESTED"}, "개인정보 제공 요구"),
        "REQUEST_INSTALL_APP": ("device.remote_control_app", "원격제어 앱", {"status": "REQUESTED"}, "원격제어 앱 설치 요구"),
        "REQUEST_TRANSFER": ("circumstance.demand", "상대방 요구", {"text": "송금·이체 요구"}, "송금·이체 요구"),
        "REQUEST_KEEP_CALL": ("circumstance.demand", "상대방 요구", {"text": "통화 유지 요구"}, "통화 유지 요구"),
        "REQUEST_SECRECY": ("circumstance.demand", "상대방 요구", {"text": "외부 확인 제한 요구"}, "외부 확인 제한 요구"),
    }
    for code in sorted(requested_codes):
        fact = requested_action_facts.get(code)
        if fact:
            candidates.append(fact)
    for key, label, values in (
        ("offender.incident_claim", "상대방 주장", context.get("offender_claims", [])),
        ("circumstance.demand", "상대방 요구", context.get("offender_demands", [])),
        ("circumstance.tactic", "압박·조작 수법", context.get("manipulation_tactics", [])),
    ):
        for value in values[:8]:
            text = str(value).strip()
            if text:
                candidates.append((key, label, {"text": text}, text))

    # Context features and LLM atoms are complementary. The former is a safe
    # grouped summary; the latter preserves fine-grained facts that must also
    # become reviewable Context V3 items.
    candidate_keys = {(key, json.dumps(value, ensure_ascii=False, sort_keys=True), display) for key, _, value, display in candidates}
    def add_structured_candidate(key: str, label: str, value: dict[str, Any], display: str) -> None:
        if key == "circumstance.tactic":
            family = (
                {"고립", "연락", "가족", "상의를", "알리"} if value.get("kind") == "ISOLATION"
                else {"긴급", "재촉", "압박", "시한"} if value.get("kind") in {"URGENCY", "DEADLINE_TODAY", "DEADLINE_IMMEDIATE"}
                else {"불안", "공포", "처벌", "피해"} if value.get("kind") == "FEAR" else set()
            )
            if family and any(any(word in existing.casefold() for word in family) for existing_key, _, _, existing in candidates if existing_key == key):
                return
        marker = (key, json.dumps(value, ensure_ascii=False, sort_keys=True), display)
        if marker not in candidate_keys:
            candidates.append((key, label, value, display))
            candidate_keys.add(marker)

    organization_labels = {
        "PROSECUTION_SERVICE": "수사기관", "POLICE_SERVICE": "경찰", "FINANCIAL_SUPERVISORY_SERVICE": "금융기관",
        "COURT": "법원", "BANK": "은행", "CARD_COMPANY": "카드사", "LOAN_COMPANY": "대출기관",
    }
    def organization_display(atom: dict[str, Any], fallback: str) -> str:
        """Prefer the privacy-safe observed organization phrase over a broad code label."""
        for term in atom.get("observed_terms") or []:
            surface = str(term.get("surface_form") or "").strip() if isinstance(term, dict) else str(term).strip()
            if surface and len(surface) <= 120:
                return surface
        return fallback
    for atom in diagnosis_atoms:
        predicate = str(atom.get("predicate") or "").upper()
        atom_class = str(atom.get("atom_class") or "").upper()
        cues = {str(cue).upper() for cue in atom.get("lexical_cues", [])}
        if predicate == "CLAIMS_ORGANIZATION":
            organization_code = str(atom.get("claimed_organization") or "")
            organization = organization_display(atom, organization_labels.get(organization_code, "특정 기관"))
            add_structured_candidate("offender.claimed_organization", "사칭 기관", {
                "organization": organization, "organization_code": organization_code or None,
            }, f"상대방이 {organization}을(를) 사칭한 정황")
        elif predicate == "TRANSFER_FUNDS":
            add_structured_candidate("circumstance.demand", "상대방 요구", {"kind": "TRANSFER", "text": "송금·이체 요구"}, "송금·이체 요구")
        elif predicate == "OPEN_URL" or "OPEN_URL" in cues:
            add_structured_candidate("circumstance.demand", "상대방 요구", {"kind": "LINK_OR_APP", "text": "링크·앱 실행 요구"}, "링크·앱 실행 요구")
        elif predicate in {"AVOID_EXTERNAL_CONTACT", "KEEP_CALL"} or atom.get("communication_control"):
            add_structured_candidate("circumstance.tactic", "압박·조작 수법", {"kind": "ISOLATION", "text": "외부 연락 제한"}, "외부 연락 제한")
        elif atom.get("urgency") not in {None, "NONE", "UNKNOWN", "UNKNOWN_DEADLINE"}:
            add_structured_candidate("circumstance.tactic", "압박·조작 수법", {"kind": "URGENCY", "text": "긴급 처리 압박"}, "긴급 처리 압박")
        elif atom.get("fear_pressure") not in {None, "NONE"} or atom.get("threat_type"):
            add_structured_candidate("circumstance.tactic", "압박·조작 수법", {"kind": "FEAR", "text": "불안·공포 유발"}, "불안·공포 유발")

    observation_candidates = {
        "PURPOSE_SAFE_ACCOUNT": ("circumstance.demand", "안전계좌로 자금 이동을 유도한 정황", {"kind": "SAFE_ACCOUNT"}),
        "DEADLINE_TODAY": ("circumstance.tactic", "오늘 안에 처리하도록 재촉한 정황", {"kind": "DEADLINE_TODAY"}),
        "DEADLINE_IMMEDIATE": ("circumstance.tactic", "즉시 처리하도록 재촉한 정황", {"kind": "DEADLINE_IMMEDIATE"}),
    }
    for observation in context_features.get("observations", []):
        code = str(observation.get("code") or "").upper()
        if str(observation.get("status") or "").upper() == "DENIED":
            continue
        candidate = observation_candidates.get(code)
        if candidate:
            key, display, value = candidate
            add_structured_candidate(key, "상대방 요구" if key.endswith("demand") else "압박·조작 수법", value, display)
    # Keep grouped legacy candidates, then add one reviewable candidate per
    # fine-grained Atom so values are not collapsed into one panel row.
    for atom_candidate in project_semantic_atoms_to_fact_candidates(diagnosis_atoms):
        candidates.append((
            atom_candidate["semantic_key"], atom_candidate["display_label"],
            atom_candidate["value"], atom_candidate["display_value"],
        ))
    store = case_context_v2_repository()
    amount_atom_ids = {
        int(float(atom["amount_value_krw"])): str(atom["atom_id"])
        for atom in diagnosis_atoms
        if atom.get("amount_value_krw") is not None
    }
    def relevant_atom_id(key: str, display: str) -> str | None:
        text = display.casefold()
        for atom in diagnosis_atoms:
            predicate = str(atom.get("predicate") or "").upper()
            cues = {str(cue).upper() for cue in atom.get("lexical_cues", [])}
            if key == "offender.claimed_organization" and predicate == "CLAIMS_ORGANIZATION":
                return str(atom["atom_id"])
            if key == "offender.incident_claim" and predicate.startswith("CLAIMS_"):
                return str(atom["atom_id"])
            if key == "exposure.authentication_information" and (
                atom.get("auth_secret_type") or predicate in {"DISCLOSE_OTP", "REQUEST_AUTH_INFO"}
            ):
                return str(atom["atom_id"])
            if key == "exposure.personal_information" and (
                "PERSONAL" in predicate or "SENSITIVE_INFO" in cues
            ):
                return str(atom["atom_id"])
            if key == "device.remote_control_app" and (
                "DEVICE" in predicate or "DEVICE_CONTROL" in cues or "REMOTE" in predicate
            ):
                return str(atom["atom_id"])
            if key == "transfer.requested.amount" and atom.get("amount_value_krw") is not None:
                continue
            if key == "circumstance.demand":
                if "송금" in text or "이체" in text:
                    if predicate in {"TRANSFER_FUNDS", "OTHER"} or "TRANSFER" in cues:
                        return str(atom["atom_id"])
                if "링크" in text or "앱" in text:
                    if predicate in {"OPEN_URL", "OPEN_APP"} or "OPEN_URL" in cues or "DEVICE" in predicate:
                        return str(atom["atom_id"])
                if "통화" in text or "외부" in text:
                    if atom.get("communication_control") or predicate in {"AVOID_EXTERNAL_CONTACT", "KEEP_CALL"}:
                        return str(atom["atom_id"])
            if key == "circumstance.tactic":
                if "고립" in text or "연락" in text:
                    if atom.get("communication_control") or atom.get("isolation_pressure"):
                        return str(atom["atom_id"])
                if "긴급" in text or "압박" in text:
                    if atom.get("urgency") not in {None, "NONE", "UNKNOWN", "UNKNOWN_DEADLINE"} or atom.get("financial_pressure") not in {None, "NONE"}:
                        return str(atom["atom_id"])
                if "불안" in text or "공포" in text:
                    if atom.get("fear_pressure") not in {None, "NONE"} or atom.get("threat_type"):
                        return str(atom["atom_id"])
        return None
    for key, label, value, display in candidates:
        # Include typed value/Atom lineage in the idempotency key so two
        # separate mentions of the same amount remain separate events.
        digest = hashlib.sha256(f"{case_id}|{key}|{json.dumps(value, ensure_ascii=False, sort_keys=True)}|{display}".encode()).hexdigest()[:36]
        amount_atom_id = amount_atom_ids.get(int(value.get("amount_krw", 0))) if key == "transfer.requested.amount" else None
        support_atom_id = value.get("atom_id") or amount_atom_id or relevant_atom_id(key, display)
        evidence_refs = [{"type": "STRUCTURED_ATOM", "id": support_atom_id}] if support_atom_id else [dict(base_evidence_ref)]
        await store.create_fact(case_id, {
            "client_request_id": f"initial-{digest}", "semantic_key": key, "display_label": label,
            "value": value, "display_value": display, "confidence": None,
            "evidence_refs": evidence_refs, "visibility": "BANK_INTERNAL",
        }, "system:initial-diagnosis", source_kind="AI_EXTRACTION")


def build_customer_question_candidates(case: dict, queued: list[dict]) -> list[PublicQuestionCandidateResponse]:
    """Deterministic MVP candidates. AI may replace this source, not the queue contract."""
    already_handled = {item["target_field"] for item in queued if item.get("status") in {"PENDING", "ASKED", "ANSWERED"}}
    fields = [
        ("victim_transfer_status", "현재 송금하거나 이체한 금액이 있나요?", "피해 여부와 피해 금액을 먼저 확인해야 합니다.", "안전을 위해 피해 발생 여부를 가장 먼저 확인합니다.", "P0", ["없음", "있음", "잘 모르겠어요"]),
        ("remote_control_app", "휴대폰에 원격 제어 또는 화면 공유 앱을 설치하라는 안내를 받으셨나요?", "추가 피해 가능성을 확인해야 합니다.", "휴대폰 제어 가능성을 확인해 추가 피해를 막기 위한 질문입니다.", "P0", ["설치함", "설치하지 않음", "잘 모르겠어요"]),
        ("personal_information_exposure", "주민등록번호나 계좌번호 등 개인정보를 제공하셨나요?", "개인정보 노출 여부는 추가 보호 조치 판단에 필요합니다.", "개인정보 보호 조치가 필요한지 확인하는 질문입니다.", "P0", ["제공하지 않았어요", "일부 제공했어요", "제공했어요", "잘 모르겠어요"]),
        ("authentication_information_exposure", "인증번호, 비밀번호 또는 OTP를 제공하셨나요?", "인증정보 노출 여부는 계정 보호 판단에 필요합니다.", "계정과 금융정보를 보호하기 위해 인증정보 노출 여부를 확인합니다.", "P0", ["제공하지 않았어요", "제공했어요", "잘 모르겠어요"]),
        ("impersonated_institution", "상대방이 어느 기관이나 은행을 사칭했는지 알려주실 수 있나요?", "공식 채널 검증 대상을 정해야 합니다.", "상대방의 주장을 공식 채널에서 확인하기 위한 질문입니다.", "P1", []),
    ]
    if case.get("victim_transfer_status") != "UNKNOWN":
        already_handled.add("victim_transfer_status")
    return [
        PublicQuestionCandidateResponse(
            question_id=f"candidate-{target_field}", target_field=target_field,
            question_text=text, reason=reason, customer_explanation=customer_explanation,
            priority=priority, options=options, answer_mode="CHOICE_OR_TEXT", allow_free_text=True,
        )
        for target_field, text, reason, customer_explanation, priority, options in fields
        if target_field not in already_handled
    ]


def build_question_recommendation_context(facts: list[dict], questions: list[dict], case: dict | None = None) -> dict:
    """답변 수신과 사실 확정을 분리하되 질문 이력이 있는 항목은 다시 묻지 않는다."""
    valid_fields = {
        "transfer_status", "transfer_purpose", "claimed_organization", "incident_claim",
        "personal_information_exposure", "authentication_information_exposure",
        "remote_control_app",
    }
    confirmed_fields = [normalize_target_field(item["field"]) for item in facts if item.get("status") == "CONFIRMED" and normalize_target_field(item.get("field", "")) in valid_fields]
    if case and case.get("victim_transfer_status") in {"YES", "NO"}:
        confirmed_fields.append("transfer_status")
    return {
        "confirmed_fields": list(dict.fromkeys(confirmed_fields)),
        "pending_question_fields": [normalize_target_field(item["target_field"]) for item in questions if item.get("status") in {"PENDING", "ASKED"} and normalize_target_field(item.get("target_field", "")) in valid_fields],
        "answered_question_fields": [normalize_target_field(item["target_field"]) for item in questions if item.get("status") == "ANSWERED" and normalize_target_field(item.get("target_field", "")) in valid_fields],
        "answered_question_ids": [item["question_id"] for item in questions if item.get("status") == "ANSWERED"],
    }


def question_fields_answered_by_messages(messages: list[dict]) -> set[str]:
    """Conservative pre-extraction guard against asking for an answer already stated by a human."""
    answered: set[str] = set()
    for message in messages:
        if message.get("actor_type") not in {"CUSTOMER", "BANK_STAFF"} or message.get("message_kind", "CHAT") != "CHAT":
            continue
        text = re.sub(r"\s+", "", str(message.get("content", ""))).casefold()
        asserted = any(term in text for term in ("했", "보냈", "알려", "제공", "설치", "깔았", "안했", "않았", "없어요", "없습니다"))
        if not asserted:
            continue
        if any(term in text for term in ("송금", "이체", "입금", "돈을보")):
            answered.add("transfer_status")
        if any(term in text for term in ("원격제어", "원격앱", "애니데스크", "팀뷰어")):
            answered.add("remote_control_app")
        if any(term in text for term in ("otp", "인증번호", "비밀번호", "보안코드")):
            answered.add("authentication_information_exposure")
        if any(term in text for term in ("주민등록번호", "계좌번호", "개인정보")):
            answered.add("personal_information_exposure")
        if any(term in text for term in ("검찰", "경찰", "금감원", "금융감독원", "은행직원")) and any(term in text for term in ("사칭", "이라고", "라며", "전화")):
            answered.add("claimed_organization")
    return answered


def normalize_question_text(value: str) -> str:
    """Whitespace/case differences must not bypass the duplicate-question guard."""
    return " ".join(value.split()).casefold()


CONTEXTUAL_QUESTION_PREFIX = "ai-context-"


def _same_question(left: str, right: str) -> bool:
    return normalize_question_text(left) == normalize_question_text(right) or similar_question(left, right)


def _unsafe_contextual_question(question_text: str) -> bool:
    """Reject obvious requests for secrets or customer actions before a draft reaches staff."""
    compact = re.sub(r"\s+", "", question_text).casefold()
    sensitive = ("비밀번호", "패스워드", "pin", "otp", "인증번호", "보안코드", "주민등록번호")
    value_requests = ("입력", "적어", "써", "말해", "알려", "보내", "무엇", "뭔가", "몇번")
    if any(term in compact for term in sensitive) and any(term in compact for term in value_requests):
        return True
    money_actions = ("송금", "이체", "결제", "입금")
    action_requests = ("하세요", "해주", "진행하", "보내세요", "실행하", "설치하")
    return any(term in compact for term in money_actions) and any(term in compact for term in action_requests)


def _contextual_target_field(question_text: str) -> str:
    digest = hashlib.sha256(normalize_question_text(question_text).encode("utf-8")).hexdigest()[:20]
    return f"{CONTEXTUAL_QUESTION_PREFIX}{digest}"


def filter_contextual_questions(
    generated: list,
    baseline: list[PublicQuestionCandidateResponse],
    persisted: list[dict],
    drafts: list[PublicQuestionCandidateResponse],
) -> list:
    """Keep only safe, novel QUESTION_PLAN drafts and assign non-canonical fields."""
    baseline_fields = BASELINE_QUESTION_FIELDS | {normalize_target_field(item.target_field) for item in baseline}
    covered = [*baseline, *drafts]
    covered.extend(
        PublicQuestionCandidateResponse(
            question_id=str(item.get("question_id", "persisted")),
            target_field=str(item.get("target_field", "")),
            question_text=str(item.get("question_text", "")),
            reason=str(item.get("reason") or "이미 처리된 고객 질문"),
            priority=item.get("priority", "P1"),
        )
        for item in persisted
        if item.get("status") in {"PENDING", "ASKED", "ANSWERED"}
    )
    covered_fields = {normalize_target_field(item.target_field) for item in covered}
    accepted = []
    for question in generated:
        text = question.question_text.strip()
        reason = question.reason.strip()
        source_field = normalize_target_field(question.target_field)
        if not text or not reason or _unsafe_contextual_question(text):
            continue
        if source_field in baseline_fields or source_field in covered_fields:
            continue
        if any(_same_question(text, item.question_text) for item in covered):
            continue
        if any(_same_question(text, item.question_text) for item in accepted):
            continue
        target_field = _contextual_target_field(text)
        accepted.append(question.model_copy(update={
            "question_id": target_field,
            "target_field": target_field,
        }))
        if len(accepted) == 3:
            break
    return accepted


def exclude_handled_question_candidates(
    candidates: list[PublicQuestionCandidateResponse], questions: list[dict]
) -> list[PublicQuestionCandidateResponse]:
    handled = [item for item in questions if item.get("status") in {"PENDING", "ASKED", "ANSWERED"}]
    handled_fields = {normalize_target_field(str(item.get("target_field", ""))) for item in handled}
    handled_texts = {normalize_question_text(str(item.get("question_text", ""))) for item in handled}
    return [
        candidate for candidate in candidates
        if normalize_target_field(candidate.target_field) not in handled_fields
        and normalize_question_text(candidate.question_text) not in handled_texts
        and not any(similar_question(candidate.question_text, str(q.get("question_text", ""))) for q in handled
                    if not q.get("target_field") or normalize_target_field(q["target_field"]) == normalize_target_field(candidate.target_field))
    ]


def to_public_case_support_snapshot(
    case_id: str, payload: dict, *, available: bool, source_revision: int | None = None,
    projection_revision: int | None = None, projection_status: str = "UNCACHED",
) -> PublicCaseSupportSnapshotResponse:
    brief = payload.get("case_brief") or None
    context = payload.get("case_context") or None
    return PublicCaseSupportSnapshotResponse(
        case_id=case_id, available=available,
        case_brief=PublicCaseSupportBrief(
            summary=brief["summary"], incident_type=brief["incident_type"],
            risk_level=brief["risk_level"], risk_score=brief["risk_score"], next_checks=brief.get("next_checks", []),
        ) if brief else None,
        case_context=PublicCaseContextProjection.model_validate(context) if context else None,
        recommended_questions=[PublicQuestionCandidateResponse(
            question_id=item["question_id"], target_field=item["target_field"],
            question_text=item["question"], reason=item["reason"], priority=item["priority"],
            options={
                "transfer_status": ["아직 송금하지 않았어요", "이미 송금했어요", "잘 모르겠어요"],
                "personal_information_exposure": ["제공하지 않았어요", "일부 제공했어요", "제공했어요", "잘 모르겠어요"],
                "authentication_information_exposure": ["제공하지 않았어요", "제공했어요", "잘 모르겠어요"],
            }.get(item["target_field"], []),
            customer_explanation={
                "transfer_status": "추가 피해를 막고 필요한 조치를 안내하기 위해 실제 송금 여부를 먼저 확인합니다.",
                "personal_information_exposure": "개인정보 보호 조치가 필요한지 확인하는 질문입니다.",
                "authentication_information_exposure": "계정과 금융정보를 보호하기 위해 인증정보 노출 여부를 확인합니다.",
            }.get(item["target_field"]),
        ) for item in payload.get("recommended_questions", [])],
        unresolved_items=[PublicUnresolvedItemResponse.model_validate(item) for item in payload.get("unresolved_items", [])],
        warnings=payload.get("warnings", []),
        source_revision=source_revision, projection_revision=projection_revision,
        projection_status=projection_status,
    )


async def _read_case_support_source(case_id: str, *, attempts: int = 3) -> tuple[int, dict, list[dict], list[dict], list[dict], list[dict]]:
    """Read a source set whose semantic revision did not change mid-read."""
    for _ in range(attempts):
        case = await repository.get(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."})
        before = int(case.get("context_revision", 1))
        facts, questions, verifications, actions = await asyncio.gather(
            repository.list_case_facts(case_id), repository.list_customer_questions(case_id),
            repository.list_verifications(case_id), repository.list_actions(case_id),
        )
        resources = await case_context_v2_repository().list_resources(case_id)
        facts, actions = merge_support_records(resources, facts, actions)
        latest = await repository.get(case_id)
        if latest is None:
            raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."})
        after = int(latest.get("context_revision", 1))
        if before == after:
            return after, latest, facts, questions, verifications, actions
    raise RuntimeError("CASE_CONTEXT_SOURCE_CHANGED")


def _case_support_ai_input(case_id: str, case: dict, facts: list[dict], questions: list[dict], verifications: list[dict], actions: list[dict]) -> dict:
    actions = actions_for_ai(actions)
    return {
        "case_id": case_id, "diagnosis": case.get("diagnosis"),
        "question_context": build_question_recommendation_context(facts, questions, case),
        "questions": [{
            "question_id": item["question_id"],
            "target_field": normalize_target_field(str(item.get("target_field", ""))),
            "question_text": item.get("question_text", ""), "priority": item.get("priority", "P1"),
            "status": item.get("status", "PENDING"), "answer_text": item.get("answer_text"),
        } for item in questions],
        "facts": [{
            "fact_id": item["fact_id"], "field": normalize_target_field(str(item.get("field", item.get("field_name", "")))),
            "value": str(item.get("value", "")), "status": item.get("status", "UNRESOLVED"),
        } for item in facts],
        "verifications": [{
            "verification_task_id": item["verification_task_id"], "target": item.get("target", ""),
            "claim": item.get("claim", ""), "status": item.get("status", "PENDING"),
            "result_summary": item.get("result_summary"),
        } for item in verifications],
        "actions": [{
            "action_id": item["action_id"], "action_type": item.get("action_type", "OTHER"),
            "status": item.get("status", "PENDING"), "note": item.get("note", ""),
        } for item in actions],
    }


async def get_case_support_snapshot(case_id: str) -> PublicCaseSupportSnapshotResponse:
    # Mock/in-memory repositories keep the original uncached path. Production
    # MySQL uses durable revision + DB lease so multiple workers share one result.
    if isinstance(repository, MySqlCaseRepository):
        projections = ContextProjectionRepository(repository)
        for _ in range(3):
            try:
                revision, case, facts, questions, verifications, actions = await _read_case_support_source(case_id)
            except RuntimeError:
                continue
            claim = await projections.claim(case_id, revision)
            if claim.outcome == "STALE":
                continue
            if claim.outcome == "CACHED":
                return to_public_case_support_snapshot(case_id, claim.last_success_payload or {}, available=True,
                    source_revision=revision, projection_revision=claim.last_success_revision, projection_status="CURRENT")
            if claim.outcome == "IN_PROGRESS":
                if claim.last_success_payload is not None:
                    cached = {**claim.last_success_payload, "warnings": [
                        *claim.last_success_payload.get("warnings", []), "최신 변경사항을 반영 중이며 직전 정상 사건 맥락을 표시합니다.",
                    ]}
                    return to_public_case_support_snapshot(case_id, cached, available=True,
                        source_revision=revision, projection_revision=claim.last_success_revision, projection_status="UPDATING")
                return PublicCaseSupportSnapshotResponse(case_id=case_id, available=False,
                    warnings=["사건 맥락을 처음 정리하고 있습니다."], source_revision=revision, projection_status="UPDATING")
            try:
                payload = await service.ai_client.build_case_support_snapshot(
                    _case_support_ai_input(case_id, case, facts, questions, verifications, actions)
                )
            except AiServiceError as exc:
                await projections.fail(case_id, revision, claim.lease_token or "", type(exc).__name__)
                if claim.last_success_payload is not None:
                    cached = {**claim.last_success_payload, "warnings": [
                        *claim.last_success_payload.get("warnings", []), str(exc), "최신 반영에 실패해 직전 정상 사건 맥락을 표시합니다.",
                    ]}
                    return to_public_case_support_snapshot(case_id, cached, available=True,
                        source_revision=revision, projection_revision=claim.last_success_revision, projection_status="STALE")
                return PublicCaseSupportSnapshotResponse(case_id=case_id, available=False, warnings=[str(exc)],
                    source_revision=revision, projection_status="FAILED")
            if await projections.complete(case_id, revision, claim.lease_token or "", payload):
                return to_public_case_support_snapshot(case_id, payload, available=True,
                    source_revision=revision, projection_revision=revision, projection_status="CURRENT")
            # Data changed during generation; never publish this obsolete result.
        return PublicCaseSupportSnapshotResponse(case_id=case_id, available=False,
            warnings=["사건 정보가 연속으로 변경되어 최신 맥락 반영을 다시 시도합니다."], projection_status="UPDATING")

    case = await repository.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."})
    facts = await repository.list_case_facts(case_id)
    questions = await repository.list_customer_questions(case_id)
    verifications = await repository.list_verifications(case_id)
    actions = await repository.list_actions(case_id)
    try:
        resources = await case_context_v2_repository().list_resources(case_id)
        facts, actions = merge_support_records(resources, facts, actions)
        payload = await service.ai_client.build_case_support_snapshot(
            _case_support_ai_input(case_id, case, facts, questions, verifications, actions)
        )
        return to_public_case_support_snapshot(case_id, payload, available=True)
    except AiServiceError as exc:
        return PublicCaseSupportSnapshotResponse(case_id=case_id, available=False, warnings=[str(exc)])


@app.get("/api/cases/{case_id}/ai/case-support", response_model=PublicCaseSupportSnapshotResponse)
async def read_case_support_snapshot(case_id: str) -> PublicCaseSupportSnapshotResponse:
    return await get_case_support_snapshot(case_id)


@app.get("/api/cases/{case_id}/customer-question-candidates", response_model=list[PublicQuestionCandidateResponse])
async def list_customer_question_candidates(case_id: str) -> list[PublicQuestionCandidateResponse]:
    case = await repository.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."})
    queued, messages = await asyncio.gather(repository.list_customer_questions(case_id), repository.list_messages(case_id))
    # Some compatibility repositories may not expose message history while upgrading.
    messages = messages if isinstance(messages, list) else []
    snapshot = await get_case_support_snapshot(case_id)
    # AI 장애 시에도 기존 deterministic 후보로 고객 확인 흐름을 멈추지 않는다.
    fallback_candidates = build_customer_question_candidates(case, queued)
    candidates = list(snapshot.recommended_questions) if snapshot.available else []
    represented = {normalize_target_field(item.target_field) for item in candidates}
    candidates.extend(item for item in fallback_candidates if normalize_target_field(item.target_field) not in represented)
    # AI 결과를 그대로 신뢰하지 않는다. 질문 이력 기반 최종 중복 방지는 General API가 담당한다.
    facts = await repository.list_case_facts(case_id)
    resources = await case_context_v2_repository().list_resources(case_id)
    facts, _ = merge_support_records(resources, facts, [])
    confirmed = set(build_question_recommendation_context(facts, queued, case)["confirmed_fields"])
    review_first = {
        normalize_target_field(SEMANTIC_FIELDS[item.semantic_key])
        for item in resources.facts
        if item.status == "PROPOSED" and item.source_kind in {"CUSTOMER_STATEMENT", "STAFF_OBSERVATION"} and item.semantic_key in SEMANTIC_FIELDS
    }
    already_stated = question_fields_answered_by_messages(messages)
    return [candidate for candidate in exclude_handled_question_candidates(candidates, queued)
            if normalize_target_field(candidate.target_field) not in confirmed | review_first | already_stated]


@app.get("/api/cases/{case_id}/customer-questions", response_model=list[PublicCustomerQuestionResponse | PublicCustomerQuestionView])
async def list_customer_questions(case_id: str, view: Literal["bank", "customer"] = "bank") -> list[PublicCustomerQuestionResponse | PublicCustomerQuestionView]:
    await require_case(case_id)
    items = await repository.list_customer_questions(case_id)
    if view == "customer":
        return [to_public_customer_question_view(item) for item in items]
    return [to_public_customer_question(item) for item in items]


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
    return [to_public_customer_question(item) for item in items]


async def sync_ai_checklist_items(case_id: str, snapshot: PublicCaseSupportSnapshotResponse) -> list[dict]:
    """Persist each AI-recommended check once so unfinished staff work accumulates."""
    existing = await repository.list_actions(case_id)
    known_fields = {
        normalize_target_field(str(item.get("action_type", "")).split(":")[-1])
        for item in existing
        if str(item.get("action_type", "")).startswith(AI_CHECKLIST_ACTION_PREFIX)
    }
    candidates = [
        (normalize_target_field(item.target_field), item.priority, item.description)
        for item in snapshot.unresolved_items[:12]
    ] if snapshot.available else []
    facts = await repository.list_case_facts(case_id)
    candidates.extend(
        (
            normalize_target_field(str(item.get("field", ""))),
            "P0" if normalize_target_field(str(item.get("field", ""))) in AUTONOMOUS_P0_QUESTION_FIELDS else "P1",
            f"{CHECKLIST_FIELD_LABELS.get(normalize_target_field(str(item.get('field', ''))), '추가 확인 사항')}에 대한 고객 답변 “{item.get('value', '')}”을 사실로 확정할지 검토하세요.",
        )
        for item in facts
        if item.get("status") == "PROPOSED"
    )
    created: list[dict] = []
    for field, priority, description in candidates:
        if not field or field in known_fields:
            continue
        created.append(await repository.create_action(case_id, {
            "action_type": f"{AI_CHECKLIST_ACTION_PREFIX}{priority}:{field}",
            "actor_type": "SYSTEM",
            "note": description,
        }))
        known_fields.add(field)
    return created


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
    await repository.link_customer_question_message(case_id, question["question_id"], message["message_id"])
    question["question_message_id"] = message["message_id"]
    return to_public_message(message)


def _structured_answer_fact_payload(question: dict, answer_text: str, answer_message_id: str | None) -> dict | None:
    """Map only deterministic, unambiguous answers to an unconfirmed Context V2 Fact."""
    if not answer_message_id:
        return None
    try:
        target_field = TargetField(normalize_target_field(str(question["target_field"])))
    except (KeyError, ValueError):
        # Contextual questions and unsupported fields retain the existing raw-answer path.
        return None

    structured = CustomerAnswerStructuringService().structure_answer(target_field, answer_text)
    if structured.unresolved or structured.structured_value is None:
        return None

    mappings = {
        TargetField.TRANSFER_STATUS: (
            "transfer.actual.status",
            {"status": structured.structured_value},
            {"TRANSFERRED": "송금함", "NOT_TRANSFERRED": "송금하지 않음"},
        ),
        TargetField.PERSONAL_INFORMATION_EXPOSURE: (
            "exposure.personal_information",
            {"status": structured.structured_value},
            {"EXPOSED": "노출됨", "PARTIALLY_EXPOSED": "일부 노출됨", "NOT_EXPOSED": "노출되지 않음"},
        ),
        TargetField.AUTHENTICATION_INFORMATION_EXPOSURE: (
            "exposure.authentication_information",
            {"status": structured.structured_value},
            {"EXPOSED": "노출됨", "NOT_EXPOSED": "노출되지 않음"},
        ),
        TargetField.REMOTE_CONTROL_APP: (
            "device.remote_control_app",
            {"status": structured.structured_value},
            {"INSTALLED": "설치됨", "NOT_INSTALLED": "설치되지 않음"},
        ),
    }
    mapping = mappings.get(target_field)
    if mapping is None:
        return None
    semantic_key, value, display_values = mapping
    return {
        "client_request_id": proposal_dedupe_key(answer_message_id, semantic_key, value),
        "semantic_key": semantic_key,
        "display_label": SEMANTIC_LABELS[semantic_key],
        "value": value,
        "display_value": display_values[structured.structured_value],
        "confidence": structured.confidence,
        "evidence_refs": [{"type": "QUESTION_ANSWER", "id": answer_message_id}],
        "visibility": "BANK_INTERNAL",
    }


async def _persist_structured_answer_fact(question: dict, answered: dict, answer_text: str) -> None:
    """Keep raw-answer persistence authoritative if this additive proposal cannot be stored."""
    payload = _structured_answer_fact_payload(question, answer_text, answered.get("answer_message_id"))
    if payload is None:
        return
    await case_context_v2_repository().create_fact(
        answered["case_id"], payload, "customer-answer-structurer", source_kind="CUSTOMER_STATEMENT",
    )


@app.post("/api/cases/{case_id}/customer-questions/{question_id}/answer", response_model=PublicCustomerQuestionResponse)
async def answer_customer_question(case_id: str, question_id: str, request: PublicAnswerCustomerQuestionRequest, background_tasks: BackgroundTasks) -> PublicCustomerQuestionResponse:
    await require_case(case_id)
    question = next((item for item in await repository.list_customer_questions(case_id) if item["question_id"] == question_id), None)
    if question is None:
        raise HTTPException(status_code=404, detail={"code": "CUSTOMER_QUESTION_NOT_FOUND", "message": "답변할 질문을 찾을 수 없습니다."})
    current_version = int(question.get("question_version", 1))
    if request.raw_answer is None and request.question_version is not None and request.question_version != current_version:
        raise HTTPException(status_code=409, detail={"code": "QUESTION_VERSION_CONFLICT", "message": "질문이 변경되었습니다.", "current_version": current_version})
    answer_payload = None
    answer_text = request.raw_answer
    if request.raw_answer is None:
        option_map = {item["option_id"]: item["label"] for item in question_option_items(question_id, (question or {}).get("options", []))}
        if any(item not in option_map for item in request.selected_option_ids):
            raise HTTPException(status_code=422, detail={"code": "INVALID_QUESTION_OPTION", "message": "현재 질문에 없는 선택지입니다."})
        if len(request.selected_option_ids) > 1 and not (question or {}).get("allow_multi_select", False):
            raise HTTPException(status_code=422, detail={"code": "MULTI_SELECT_NOT_ALLOWED", "message": "이 질문은 복수 선택을 지원하지 않습니다."})
        labels = [option_map[item] for item in request.selected_option_ids]
        free_text = (request.free_text or "").strip() or None
        answer_payload = {"selected_option_ids": request.selected_option_ids, "selected_option_labels": labels, "free_text": free_text}
        answer_text = "\n".join([*labels, *([free_text] if free_text else [])])
    try:
        if request.raw_answer is not None:
            answered = await repository.submit_customer_answer(case_id, question_id, answer_text, request.actor_user_id, request.actor_display_name)
        else:
            answered = await repository.submit_customer_answer(case_id, question_id, answer_text or "", request.actor_user_id, request.actor_display_name, answer_payload, request.question_version or current_version)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CUSTOMER_QUESTION_NOT_FOUND", "message": "응답 대기 중인 질문을 찾을 수 없습니다."}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "CUSTOMER_ANSWER_CONFLICT", "message": "이미 다른 답변이 저장된 질문입니다. 최신 내용을 확인해 주세요."}) from exc
    try:
        await _persist_structured_answer_fact(question, answered, answer_text or "")
    except Exception:
        # The committed customer answer and legacy Fact remain usable if this additive proposal fails.
        logger.exception("Could not persist structured customer answer fact for question %s", question_id)
    try:
        message = next((item for item in await repository.list_messages(case_id) if item.get("message_id") == answered.get("answer_message_id")), None)
        if message:
            await enqueue_context_extraction(message, background_tasks)
    except Exception:
        logger.exception("Could not enqueue customer answer context extraction")
    if _answer_reports_customer_loss(answered, answer_text or ""):
        await _activate_customer_recovery(
            case_id,
            request.actor_user_id,
            request.actor_display_name,
            add_customer_acknowledgement=False,
        )
    await dispatch_next_customer_question_message(case_id)
    return to_public_customer_question(answered)


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


@app.post("/api/cases/{case_id}/attachments", response_model=PublicAttachmentResponse, status_code=201)
async def upload_case_attachment(
    case_id: str,
    request: Request,
    file_name: str,
    uploaded_by: str,
    visibility: Literal["BANK_INTERNAL", "CUSTOMER", "AI_PRIVATE"] = "CUSTOMER",
) -> PublicAttachmentResponse:
    await require_case(case_id)
    if not uploaded_by.strip():
        raise HTTPException(status_code=422, detail={"code": "UPLOADER_REQUIRED", "message": "업로드 사용자가 필요합니다."})
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_ATTACHMENT_BYTES:
                raise HTTPException(status_code=413, detail={"code": "ATTACHMENT_TOO_LARGE", "message": f"파일은 최대 {MAX_ATTACHMENT_BYTES // (1024 * 1024)}MB까지 업로드할 수 있습니다."})
        except ValueError as exc:
            raise HTTPException(status_code=400, detail={"code": "INVALID_CONTENT_LENGTH", "message": "잘못된 파일 크기 정보입니다."}) from exc
    content = await request.body()
    if not content:
        raise HTTPException(status_code=422, detail={"code": "ATTACHMENT_EMPTY", "message": "빈 파일은 업로드할 수 없습니다."})
    if len(content) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(status_code=413, detail={"code": "ATTACHMENT_TOO_LARGE", "message": f"파일은 최대 {MAX_ATTACHMENT_BYTES // (1024 * 1024)}MB까지 업로드할 수 있습니다."})

    original_name = _clean_file_name(file_name)
    mime_type, extension = _resolve_attachment_type(original_name, request.headers.get("content-type"))
    if not _has_valid_signature(mime_type, content):
        raise HTTPException(status_code=415, detail={"code": "ATTACHMENT_SIGNATURE_MISMATCH", "message": "파일 내용과 형식이 일치하지 않습니다."})

    case_directory = ATTACHMENT_STORAGE_ROOT / hashlib.sha256(case_id.encode("utf-8")).hexdigest()[:24]
    case_directory.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}{extension}"
    stored_path = (case_directory / stored_name).resolve()
    if not stored_path.is_relative_to(ATTACHMENT_STORAGE_ROOT):
        raise HTTPException(status_code=400, detail={"code": "INVALID_ATTACHMENT_PATH", "message": "잘못된 파일 경로입니다."})
    stored_path.write_bytes(content)
    try:
        record = await repository.create_attachment(case_id, {
            "original_name": original_name,
            "stored_name": stored_name,
            "storage_path": stored_path.relative_to(ATTACHMENT_STORAGE_ROOT).as_posix(),
            "mime_type": mime_type,
            "size_bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "uploaded_by": uploaded_by.strip()[:80],
            "status": "UPLOADED",
            "visibility": visibility,
            "ai_readable": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        stored_path.unlink(missing_ok=True)
        raise
    return to_public_attachment(record)


@app.get("/api/cases/{case_id}/attachments", response_model=list[PublicAttachmentResponse])
async def list_case_attachments(case_id: str, view: Literal["bank", "customer"] = "bank") -> list[PublicAttachmentResponse]:
    await require_case(case_id)
    records = await repository.list_attachments(case_id)
    if view == "customer":
        records = [item for item in records if item.get("visibility") == "CUSTOMER"]
    return [to_public_attachment(item) for item in records]


@app.get("/api/internal/cases/{case_id}/attachments", response_model=list[PublicAttachmentResponse])
async def list_case_attachments_for_ai(case_id: str) -> list[PublicAttachmentResponse]:
    """AI 서비스용 메타데이터 목록. 서비스 인증은 배포 게이트웨이에서 적용한다."""
    await require_case(case_id)
    return [to_public_attachment(item, download_view="bank") for item in await repository.list_attachments(case_id) if item.get("ai_readable", True)]


@app.get("/api/cases/{case_id}/attachments/{attachment_id}/content")
async def download_case_attachment(case_id: str, attachment_id: str, view: Literal["bank", "customer"] = "customer") -> FileResponse:
    await require_case(case_id)
    record = await repository.get_attachment(case_id, attachment_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"code": "ATTACHMENT_NOT_FOUND", "message": "첨부 파일을 찾을 수 없습니다."})
    if view == "customer" and record.get("visibility") != "CUSTOMER":
        raise HTTPException(status_code=403, detail={"code": "ATTACHMENT_FORBIDDEN", "message": "이 첨부 파일을 열 권한이 없습니다."})
    stored_path = (ATTACHMENT_STORAGE_ROOT / record["storage_path"]).resolve()
    if not stored_path.is_relative_to(ATTACHMENT_STORAGE_ROOT) or not stored_path.is_file():
        raise HTTPException(status_code=410, detail={"code": "ATTACHMENT_CONTENT_MISSING", "message": "첨부 파일 원본을 찾을 수 없습니다."})
    return FileResponse(stored_path, media_type=record["mime_type"], filename=None if record["mime_type"].startswith("image/") else record["original_name"])


@app.get("/api/cases/{case_id}/messages", response_model=list[PublicMessageResponse])
async def list_case_messages(case_id: str, channel: MessageChannel | None = None, view: Literal["bank", "customer"] = "bank") -> list[PublicMessageResponse]:
    await require_case(case_id)
    visible_channel = "CUSTOMER" if view == "customer" else channel
    messages = await repository.list_messages(case_id, visible_channel)
    if view == "customer":
        messages = [record for record in messages if record.get("visibility", record.get("audience")) == "CUSTOMER"]
    return [to_public_message(record) for record in messages]


def _customer_reports_loss(text: str) -> bool:
    """Route explicit customer loss statements to the recovery workflow.

    Negative expressions take precedence so phrases such as ``아직 송금 안 했어요``
    never activate recovery. Ambiguous messages remain in the normal AI chat.
    """
    compact = re.sub(r"\s+", "", text).lower()
    if not compact:
        return False
    if any(token in compact for token in (
        "송금안", "이체안", "보내지않", "송금하지않", "이체하지않", "아직안",
        "제공하지않", "알려주지않", "설치하지않", "아니요", "없어요", "없음",
    )):
        return False
    return any(token in compact for token in (
        "이미송금", "송금했", "이체했", "입금했", "돈을보냈", "돈보냈",
        "개인정보를제공", "개인정보알려", "계좌번호를알려", "주민번호를알려",
        "비밀번호를알려", "인증번호를알려", "otp를알려", "원격앱을설치", "원격제어앱설치",
        "사기당했", "피해를입었",
    ))


def _answer_reports_customer_loss(question: dict, raw_answer: str) -> bool:
    if _customer_reports_loss(raw_answer):
        return True
    target = normalize_target_field(str(question.get("target_field", "")))
    loss_fields = {
        "transfer_status", "personal_information_exposure",
        "authentication_information_exposure", "remote_control_app",
    }
    compact = re.sub(r"\s+", "", raw_answer).lower()
    return target in loss_fields and compact in {
        "예", "네", "있음", "있어요", "제공함", "제공했어요", "설치함", "설치했어요",
        "이미송금했어요", "이미이체했어요",
    }


async def _activate_customer_recovery(
    case_id: str,
    actor_user_id: str,
    actor_display_name: str,
    *,
    add_customer_acknowledgement: bool,
) -> PublicMessageResponse:
    """Idempotently activate recovery and publish one private bank alert."""
    case = await repository.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."})
    all_messages = await repository.list_messages(case_id)
    acknowledgement = next((item for item in all_messages
                            if item.get("channel") == "CUSTOMER"
                            and item.get("actor_user_id") == actor_user_id
                            and item.get("content") == "이미 사기 피해를 입었습니다. 피해구제 안내를 확인합니다."), None)
    if add_customer_acknowledgement and acknowledgement is None:
        await repository.append_message(case_id, {
            "actor_type": "CUSTOMER", "actor_user_id": actor_user_id,
            "actor_display_name": actor_display_name, "actor_role": "CUSTOMER",
            "content": "이미 사기 피해를 입었습니다. 피해구제 안내를 확인합니다.",
            "channel": "CUSTOMER", "audience": "CUSTOMER", "visibility": "CUSTOMER",
            "message_kind": "CHAT", "mentions": [], "log_event": False, "customer_emergency_ack": True,
        })
    alert = next((item for item in all_messages
                  if item.get("channel") == "AI_INTERNAL"
                  and item.get("actor_user_id") == "case-copilot"
                  and item.get("actor_display_name") == "CaseCopilot 긴급 알림"), None)
    if alert is None:
        alert = await repository.append_message(case_id, {
            "actor_type": "BANK_AGENT", "actor_user_id": "case-copilot",
            "actor_display_name": "CaseCopilot 긴급 알림", "actor_role": "BANK_AGENT",
            "content": "고객이 직접 사기 피해 발생을 신고했습니다. 피해 금액과 송금 정보를 확인하고 즉시 보호 조치를 검토해 주세요.",
            "channel": "AI_INTERNAL", "audience": "BANK_INTERNAL", "visibility": "AI_PRIVATE",
            "message_kind": "SYSTEM_EVENT", "mentions": ["CaseCopilot"],
            "private_owner_user_id": None, "log_event": False, "customer_emergency_alert": True,
            "customer_reported_by_user_id": actor_user_id,
            "customer_reported_by_display_name": actor_display_name,
        })
    if case.get("mode") != "RECOVERY" or case.get("victim_transfer_status") != "YES":
        latest = await repository.get(case_id) or case
        try:
            await repository.update_case(case_id, int(latest.get("version", 1)), {
                "victim_transfer_status": "YES", "mode": "RECOVERY",
            })
        except CaseVersionConflictError as exc:
            raise HTTPException(status_code=409, detail={"code": "VERSION_CONFLICT", "message": "Case가 변경되었습니다. 다시 시도해 주세요.", "current_version": exc.current_version}) from exc
    return to_public_message(alert)


@app.post("/api/cases/{case_id}/customer-emergency", response_model=PublicMessageResponse, status_code=201)
async def start_customer_emergency(case_id: str, request: PublicCustomerEmergencyRequest) -> PublicMessageResponse:
    """Persist one customer acknowledgement, one case-wide AI alert, and a linked Recovery event."""
    return await _activate_customer_recovery(
        case_id,
        request.actor_user_id,
        request.actor_display_name,
        add_customer_acknowledgement=True,
    )


@app.post("/api/cases/{case_id}/messages", response_model=PublicMessageResponse, status_code=201)
async def create_case_message(case_id: str, request: PublicCreateMessageRequest, background_tasks: BackgroundTasks) -> PublicMessageResponse:
    await require_case(case_id)
    if request.client_request_id:
        existing = await repository.find_message_by_client_request_id(case_id, request.client_request_id)
        if isinstance(existing, dict):
            return to_public_message(existing)
    try:
        record = await repository.append_message(case_id, request.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "ATTACHMENT_NOT_FOUND", "message": "메시지에 연결할 첨부 파일을 찾을 수 없습니다."}) from exc
    try:
        await enqueue_context_extraction(record, background_tasks)
    except Exception:
        logger.exception("Message was committed but its context extraction could not be queued")
    if (
        request.actor_type == "CUSTOMER"
        and request.channel == "CUSTOMER"
        and _customer_reports_loss(request.content)
    ):
        await _activate_customer_recovery(
            case_id,
            request.actor_user_id,
            request.actor_display_name,
            add_customer_acknowledgement=False,
        )
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


@app.post("/api/cases/{case_id}/ai/work-cards", response_model=CaseWorkCardOutput)
async def generate_case_work_card(case_id: str, request: PublicWorkCardGenerateRequest) -> CaseWorkCardOutput:
    case = await repository.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."})
    facts = await repository.list_case_facts(case_id)
    verifications = await repository.list_verifications(case_id)
    actions = await repository.list_actions(case_id)
    messages = await repository.list_messages(case_id)
    attachments = await repository.list_attachments(case_id)
    support = await get_case_support_snapshot(case_id)
    staff = await read_staff_context_records(case_id)
    previous_questions = await repository.list_customer_questions(case_id)
    candidates = await list_customer_question_candidates(case_id)
    retrieved = retrieve_context(case_id, " ".join(q.question_text for q in candidates[:6]) or "기관 확인 담당자 다음 업무", collect_records(
        case_id, messages=messages, questions=previous_questions, facts=facts, verifications=verifications, staff=staff,
    ))
    try:
        known_facts = [
            f"{item.get('field')}: {item.get('value')} ({item.get('status')})" for item in facts[:30]
        ]
        if request.card_type == "QUESTION_PLAN":
            case_context = support.case_context.model_dump(mode="python") if support.case_context else {}
            contextual_facts = [
                f"사건 맥락 {key}: {value}"
                for key, value in case_context.items()
                if value
            ]
            question_state = [
                f"기존 고객 질문 [{item.get('status', 'PENDING')}] {item.get('target_field', '')}: {item.get('question_text', '')}"
                + (f" / 답변: {item.get('answer_text')}" if item.get("answer_text") else "")
                for item in previous_questions[-10:]
            ]
            draft_state = [
                f"현재 미발송 직원 검토 초안 {item.target_field}: {item.question_text}"
                for item in request.question_drafts[:10]
            ]
            known_facts = (known_facts[:15] + contextual_facts + question_state + draft_state)[:30]
        payload = await service.ai_client.generate_work_card({
            "case_id": case_id,
            "card_type": request.card_type,
            "staff_context": staff_context(staff),
            "retrieved_context": retrieved,
            "case_summary": case.get("initial_brief", ""),
            "workflow_status": case.get("status", "TRIAGE"),
            "case_mode": case.get("mode", "PREVENT"),
            "fraud_type": case.get("fraud_type"),
            "known_facts": known_facts,
            "recent_conversation": [
                f"{item.get('actor_display_name', item.get('actor_type', '작성자'))}: {item.get('content', '')[:500]}"
                for item in messages[-20:]
                if item.get("channel") in {"TEAM", "CUSTOMER"}
            ],
            "pending_actions": [
                f"{item.get('action_type')}: {item.get('note') or '상세 내용 없음'} ({item.get('status', 'REQUESTED')})"
                for item in actions_for_ai(actions) if item.get("status") not in {"COMPLETED", "CANCELLED"}
            ][:20],
            "attachment_summaries": [
                f"{item.get('original_name', '첨부 파일')} ({item.get('mime_type', '형식 미상')}, {item.get('visibility', '공개 범위 미상')})"
                for item in attachments[-10:]
            ],
            "unresolved_items": [f"{item.priority}: {item.description}" for item in support.unresolved_items[:20]],
            "pending_verifications": [f"{item.get('target')}: {item.get('claim')}" for item in verifications if item.get("status") != "COMPLETED"][:20],
            "question_candidates": [item.model_dump(mode="python") for item in candidates[:10]],
        })
        card = CaseWorkCardOutput.model_validate(payload)
        if request.card_type == "QUESTION_PLAN":
            card.questions = filter_contextual_questions(
                card.questions, candidates, previous_questions, request.question_drafts
            )
        return card
    except AiServiceQuotaError as exc:
        raise HTTPException(status_code=429, detail={"code": "OPENAI_QUOTA_EXHAUSTED", "message": str(exc)}) from exc
    except AiServiceAuthenticationError as exc:
        raise HTTPException(status_code=401, detail={"code": "OPENAI_AUTHENTICATION_FAILED", "message": str(exc)}) from exc
    except AiServiceError as exc:
        raise HTTPException(status_code=503, detail={"code": "AI_WORK_CARD_FAILED", "message": str(exc)}) from exc


@app.post("/api/cases/{case_id}/ai/invocations", response_model=PublicAiInvocationResponse, status_code=201)
async def invoke_case_copilot(case_id: str, request: PublicAiInvocationRequest) -> PublicAiInvocationResponse:
    case = await repository.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."})
    verifications = await repository.list_verifications(case_id)
    facts = await repository.list_case_facts(case_id)
    actions = await repository.list_actions(case_id)
    attachments = await repository.list_attachments(case_id)
    all_messages = await repository.list_messages(case_id)
    members = await repository.list_members(case_id)
    primary_assignee = next(
        (item.get("display_name") for item in members if item.get("role") == "CASE_OWNER"),
        None,
    )
    member_role_labels = {
        "CASE_OWNER": "메인 담당자",
        "CHAT_OPERATOR": "상담 담당자",
        "REVIEWER": "검토자",
        "VIEWER": "열람자",
    }
    unresolved = [item.get("claim", "추가 확인 항목") for item in verifications if item.get("status") != "COMPLETED"]
    staff = await read_staff_context_records(case_id)
    questions = await repository.list_customer_questions(case_id)
    retrieved = retrieve_context(case_id, request.prompt, collect_records(
        case_id, messages=all_messages, questions=questions, facts=facts, verifications=verifications, staff=staff,
    ))
    try:
        ai_reply = await service.ai_client.generate_case_copilot_reply({
            "case_id": case_id,
            "prompt": request.prompt,
            "case_summary": case.get("initial_brief", ""),
            "workflow_status": case.get("status", "TRIAGE"),
            "fraud_type": case.get("fraud_type"),
            "transfer_status": case.get("victim_transfer_status"),
            "primary_assignee": primary_assignee,
            "participants": [
                f"{item.get('display_name', '이름 미상')} ({member_role_labels.get(item.get('role'), item.get('role', '역할 미상'))})"
                for item in members
            ][:30],
            "staff_context": staff_context(staff),
            "retrieved_context": retrieved,
            "known_facts": [f"{item.get('field')}: {item.get('value')} ({item.get('status')})" for item in facts[:30]],
            "recent_conversation": [
                f"{item.get('actor_display_name', item.get('actor_type', '작성자'))}: {item.get('content', '')[:500]}"
                for item in all_messages[-30:]
                if item.get("channel") in {"TEAM", "CUSTOMER"}
                or (request.channel != "TEAM" and item.get("channel") == "AI_INTERNAL" and item.get("private_owner_user_id") == request.requester_user_id)
            ][-20:],
            "pending_actions": [
                f"{item.get('action_type')}: {item.get('note') or '상세 내용 없음'} ({item.get('status', 'REQUESTED')})"
                for item in actions_for_ai(actions) if item.get("status") not in {"COMPLETED", "CANCELLED"}
            ][:20],
            "attachment_summaries": [
                f"{item.get('original_name', '첨부 파일')} ({item.get('mime_type', '형식 미상')}, {item.get('visibility', '공개 범위 미상')})"
                for item in attachments[-10:]
            ],
            "unresolved_verifications": unresolved[:10],
            "assistant_mode": "BANK_INTERNAL",
            "customer_progress": progress_ai_context(build_customer_progress(actions)),
            "response_style": request.response_style,
        })
    except AiServiceQuotaError as exc:
        raise HTTPException(status_code=429, detail={"code": "OPENAI_QUOTA_EXHAUSTED", "message": str(exc)}) from exc
    except AiServiceAuthenticationError as exc:
        raise HTTPException(status_code=401, detail={"code": "OPENAI_AUTHENTICATION_FAILED", "message": str(exc)}) from exc
    except AiServiceError as exc:
        raise HTTPException(status_code=503, detail={"code": "AI_CASE_COPILOT_FAILED", "message": str(exc)}) from exc
    content = ai_reply["content"]
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
        channel="TEAM" if is_team_request else "AI_INTERNAL", content=content, model_mode=ai_reply["model_mode"], created_at=message["created_at"],
    )


@app.post("/api/cases/{case_id}/ai/customer-replies", response_model=PublicMessageResponse, status_code=201)
async def invoke_customer_support_ai(case_id: str, request: PublicCustomerAiReplyRequest) -> PublicMessageResponse:
    """Generate a customer-safe reply without exposing the bank-only Case bundle."""
    case = await repository.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."})
    all_messages = await repository.list_messages(case_id, "CUSTOMER")
    questions = await repository.list_customer_questions(case_id)
    progress = build_customer_progress(await repository.list_actions(case_id))
    verifications = await repository.list_verifications(case_id)
    published_results = [f"{item.get('target')}: {item.get('result_summary')} (공개 확인 결과)"
                         for item in verifications if item.get('customer_visible') and item.get('status') == 'COMPLETED' and item.get('result_summary')][-10:]
    attachments = await repository.list_attachments(case_id)
    customer_history = [
        f"{item.get('actor_display_name', '상담 참여자')}: {item.get('content', '')[:500]}"
        for item in all_messages[-20:]
        if item.get("visibility") == "CUSTOMER"
    ]
    answered = [
        f"질문: {item.get('question_text', '')} / 고객 답변: {item.get('answer_text', '')}"
        for item in questions
        if item.get("status") == "ANSWERED" and item.get("answer_text")
    ][-10:]
    # Always include visible unanswered cards, even when retrieval cannot match a vague "이 질문".
    service_questions = [
        {
            'source': 'CSR_QUESTION_CARD', 'status': 'ASKED',
            'question_text': str(item.get('question_text', ''))[:1000],
            'customer_explanation': str(item.get('customer_explanation') or '')[:1000],
            'options': [str(option)[:160] for option in (item.get('options') or [])[:10]],
        }
        for item in questions
        if item.get('status') == 'ASKED' and item.get('question_text')
        and item.get('case_id', case_id) == case_id
    ][:5]
    retrieved = retrieve_context(case_id, request.prompt, collect_records(
        case_id, messages=all_messages, questions=questions, verifications=verifications, customer=True,
    ), customer=True)
    try:
        ai_reply = await service.ai_client.generate_case_copilot_reply({
            "case_id": case_id,
            "prompt": request.prompt,
            "case_summary": "",
            "workflow_status": case.get("status", "TRIAGE"),
            "fraud_type": case.get("fraud_type"),
            "transfer_status": case.get("victim_transfer_status"),
            "known_facts": answered,
            "retrieved_context": retrieved,
            "recent_conversation": customer_history,
            "pending_actions": [],
            "unresolved_verifications": [],
            "assistant_mode": "CUSTOMER_SUPPORT",
            "primary_assignee": case.get('primary_assignee'),
            "customer_progress": progress_ai_context(progress),
            "customer_service_questions": service_questions,
            "published_verification_results": published_results,
            "attachment_summaries": [str(item.get('original_name', '첨부 자료')) for item in attachments
                                     if item.get('visibility') == 'CUSTOMER'][-10:],
        })
    except AiServiceQuotaError as exc:
        raise HTTPException(status_code=429, detail={"code": "OPENAI_QUOTA_EXHAUSTED", "message": str(exc)}) from exc
    except AiServiceAuthenticationError as exc:
        raise HTTPException(status_code=401, detail={"code": "OPENAI_AUTHENTICATION_FAILED", "message": str(exc)}) from exc
    except AiServiceError as exc:
        raise HTTPException(status_code=503, detail={"code": "AI_CUSTOMER_SUPPORT_FAILED", "message": str(exc)}) from exc
    message = await repository.append_message(case_id, {
        "actor_type": "CUSTOMER_AGENT", "actor_user_id": "customer-agent",
        "actor_display_name": "서비스 이용 안내" if ai_reply.get('model_mode') == 'SERVICE_UI_GUIDANCE' else "안전 상담 AI", "actor_role": "CUSTOMER_AGENT",
        "content": ai_reply["content"], "channel": "CUSTOMER", "audience": "CUSTOMER",
        "visibility": "CUSTOMER", "message_kind": "AI_RESPONSE", "mentions": [],
        "reply_to_message_id": request.reply_to_message_id, "client_request_id": request.client_request_id,
        "log_event": False,
    })
    return to_public_message(message)


async def run_proactive_case_automation(case_id: str) -> bool:
    """Refresh AI support and staff checklist without contacting the customer.

    The automation is deliberately fail-open for the rest of the Case API:
    an AI outage must not prevent staff or customer messages from being saved.
    """
    try:
        snapshot = await get_case_support_snapshot(case_id)
        await sync_ai_checklist_items(case_id, snapshot)
        return True
    except HTTPException as exc:
        if exc.status_code != 404:
            logger.warning("Proactive question reconciliation failed for %s: %s", case_id, exc.detail)
    except Exception as exc:
        error_number = exc.args[0] if exc.args and isinstance(exc.args[0], int) else None
        logger.warning("Proactive question reconciliation failed for %s: %s errno=%s", case_id, type(exc).__name__, error_number)
    return False


async def proactive_case_worker() -> None:
    """Observe durable Case revisions and reconcile automation only on changes."""
    while True:
        try:
            await reconcile_changed_cases_once()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Proactive Case worker iteration failed: %s", type(exc).__name__)
        await asyncio.sleep(PROACTIVE_CASE_POLL_SECONDS)


async def reconcile_changed_cases_once() -> int:
    """Run one durable-revision scan; exposed separately for contract tests."""
    reconciled = 0
    for job in await repository.list_retryable_message_extractions():
        await process_message_context_extraction(str(job["case_id"]), str(job["message_id"]))
    for case in await repository.list():
        case_id = str(case.get("case_id", ""))
        if not case_id or case.get("status") == "CLOSED" or case.get("mode") == "CLOSED":
            continue
        revision = str(case.get("updated_at", ""))
        if revision and _proactive_case_revisions.get(case_id) == revision:
            continue
        if await run_proactive_case_automation(case_id):
            latest = await repository.get(case_id)
            _proactive_case_revisions[case_id] = str((latest or case).get("updated_at", revision))
            reconciled += 1
    return reconciled


@app.on_event("startup")
async def start_proactive_case_worker() -> None:
    global _proactive_worker_task
    ping = getattr(repository, "ping", None)
    if callable(ping):
        await ping()
    if os.getenv("PROACTIVE_QUESTION_AUTOMATION", "1").lower() not in {"0", "false", "off"}:
        _proactive_worker_task = asyncio.create_task(proactive_case_worker())


@app.on_event("shutdown")
async def stop_proactive_case_worker() -> None:
    global _proactive_worker_task
    if _proactive_worker_task is not None:
        _proactive_worker_task.cancel()
        try:
            await _proactive_worker_task
        except asyncio.CancelledError:
            pass
        _proactive_worker_task = None
    close = getattr(repository, "close", None)
    if callable(close):
        await close()


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
        updated = await repository.update_verification(case_id, verification_task_id, request.expected_version, request.status, request.model_dump(exclude={"expected_version", "status"}, exclude_none=True))
        if request.status == "COMPLETED" and updated.get("result_summary"):
            await case_context_v2_repository().create_fact(case_id, {
                "client_request_id": f"verification-result-{verification_task_id}-{updated.get('version', 1)}",
                "semantic_key": "offender.claimed_organization", "display_label": "기관 확인 결과",
                "value": {"target": updated.get("target"), "result": updated.get("result_summary")},
                "display_value": f"{updated.get('target')}: {updated.get('result_summary')}",
                "evidence_refs": [{"type": "VERIFICATION_RESULT", "id": verification_task_id, "revision": updated.get("version", 1)}],
                "visibility": "BANK_INTERNAL", "confidence": 1.0,
            }, request.verified_by or "verification-reviewer", source_kind="OFFICIAL_VERIFICATION")
        return to_public_verification(updated)
    except CaseVersionConflictError as exc:
        raise HTTPException(status_code=409, detail={"code": "VERSION_CONFLICT", "message": "기관 확인 내용이 변경되었습니다. 최신 내용을 확인해 주세요.", "current_version": exc.current_version}) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "VERIFICATION_NOT_FOUND", "message": "기관 확인 항목을 찾을 수 없습니다."}) from exc


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
async def list_case_actions(case_id: str, actor_user_id: str | None = None) -> list[PublicActionResponse]:
    await require_context_v2_member(case_id, actor_user_id or "", access="READ")
    return [to_public_action(record) for record in await repository.list_actions(case_id) if not record['action_type'].startswith(PROGRESS_PREFIX)]


@app.get('/api/cases/{case_id}/customer-progress', response_model=list[CustomerProgressItem])
async def get_customer_progress(case_id: str, actor_user_id: str | None = None):
    await require_case(case_id)
    await require_customer_context_member(case_id, actor_user_id)
    return build_customer_progress(await repository.list_actions(case_id))


class DisplayEditRequest(BaseModel):
    expected_version: int = Field(ge=0)
    operation: Literal['EDIT', 'DELETE', 'RESTORE', 'RESET', 'ARCHIVE', 'RESTORE_ARCHIVE']
    text: str | None = Field(default=None, max_length=4000)
    archived_text: str | None = Field(default=None, min_length=1, max_length=4000)
    archive_index: int | None = Field(default=None, ge=0)
    archive_item_id: str | None = Field(default=None, min_length=1, max_length=64)
    archive_version: int | None = Field(default=None, ge=1)

    @model_validator(mode='after')
    def validate_change(self):
        if self.operation in {'EDIT', 'DELETE', 'RESTORE', 'RESET'}:
            ContextItemChange(expected_version=max(1, self.expected_version), operation=self.operation, text=self.text)
            if any(value is not None for value in (self.archived_text, self.archive_index, self.archive_item_id, self.archive_version)):
                raise ValueError('편집 요청에 보관 필드를 함께 보낼 수 없습니다.')
        elif self.operation == 'ARCHIVE':
            if not self.archived_text or not self.archived_text.strip() or self.archive_index is None:
                raise ValueError('삭제 보관 내용과 원래 위치가 필요합니다.')
            if self.text is not None and not self.text.strip():
                raise ValueError('남은 내용은 비어 있지 않아야 합니다.')
            if self.archive_item_id is not None or self.archive_version is not None:
                raise ValueError('삭제 보관 요청에 복원 필드를 함께 보낼 수 없습니다.')
        elif not self.archive_item_id or self.archive_version is None or any(value is not None for value in (self.text, self.archived_text, self.archive_index)):
            raise ValueError('복원할 삭제 항목과 버전이 필요합니다.')
        return self


async def context_display_repository(case_id):
    await require_case(case_id)
    return ContextItemRepository(repository) if isinstance(repository, MySqlCaseRepository) else InMemoryContextItemRepository(repository)


def mvp_open_permissions() -> bool:
    """Explicit local-demo override only; never changes stored member roles."""
    return os.getenv("MVP_OPEN_PERMISSIONS", "0").strip().lower() in {"1", "true", "yes", "on"}


def mvp_context_permissions(actor_user_id: str) -> bool:
    # Human bank-workspace access only. This is not authentication: keep the
    # known customer/AI identities out, and never widen customer projections.
    actor = actor_user_id.strip().lower()
    return mvp_open_permissions() and bool(actor) and actor not in {
        "mvp-v3-customer", "customer", "customer-agent", "case-copilot", "ai", "system:context-ai",
    } and not actor.startswith("system:")


@app.get("/api/runtime-config")
async def read_runtime_config() -> dict:
    # Deliberately expose only the UI mode, never environment values or secrets.
    return {"permissions_mode": "MVP_OPEN" if mvp_open_permissions() else "ROLE_BASED"}


async def bank_display_repository(case_id, actor_user_id):
    await require_context_v2_member(case_id, actor_user_id, access="WRITE")
    return await context_display_repository(case_id)


def case_context_v2_repository():
    if isinstance(repository, MySqlCaseRepository):
        return MySqlCaseContextV2Repository(repository)
    return InMemoryCaseContextV2Repository(repository)


@app.get("/api/cases/{case_id}/context-v2/panel", response_model=PublicContextPanelV3)
async def get_context_panel_v3(case_id: str, view: Literal["bank", "customer"] = "bank", actor_user_id: str | None = None) -> PublicContextPanelV3:
    case = await repository.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "사건을 찾을 수 없습니다."})
    if view == "bank":
        if not actor_user_id:
            raise HTTPException(status_code=401, detail={"code": "ACTOR_REQUIRED", "message": "은행 화면 조회자 정보가 필요합니다."})
        await require_context_v2_member(case_id, actor_user_id, access="READ")
    else:
        await require_customer_context_member(case_id, actor_user_id)
    display_store = await context_display_repository(case_id)
    resources, verifications, actions, messages, display_items = await asyncio.gather(
        case_context_v2_repository().list_resources(case_id), repository.list_verifications(case_id),
        repository.list_actions(case_id), repository.list_messages(case_id), display_store.list_items(case_id, include_deleted=True),
    )
    return build_context_panel_v3(
        case, resources, view=view, verifications=verifications, actions=actions,
        messages=messages, progress=build_customer_progress(actions), display_items=display_items,
    )


@app.get("/api/cases/{case_id}/context-extractions/{message_id}")
async def get_context_extraction_status(case_id: str, message_id: str, actor_user_id: str) -> dict:
    """Return extraction state without exposing message content."""
    await require_context_v2_member(case_id, actor_user_id, access="READ")
    job = await repository.get_message_extraction(case_id, message_id)
    if job is None:
        raise HTTPException(status_code=404, detail={"code": "EXTRACTION_NOT_FOUND", "message": "추출 작업을 찾을 수 없습니다."})
    return {key: job.get(key) for key in (
        "extraction_id", "case_id", "message_id", "status", "attempts", "last_error",
        "model_version", "prompt_version", "created_at", "updated_at", "completed_at",
    )}


async def read_staff_context_records(case_id: str):
    # Internal call only: never put these records in a customer response/prompt.
    resources = await case_context_v2_repository().list_resources(case_id)
    return workspace_records(case_id, resources)


async def require_context_v2_member(
    case_id: str,
    actor_user_id: str,
    *,
    access: Literal["READ", "WRITE", "REVIEW"] = "WRITE",
):
    """Authorize a context operation through the shared ActorContext adapter."""
    await require_case(case_id)
    try:
        actor = normalize_legacy_actor(actor_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail={"code": "ACTOR_REQUIRED", "message": "actor_user_id is required"}) from exc
    members = await repository.list_members(case_id)
    member = next((item for item in members if item.get("user_id") == actor.actor_id and item.get("status", "ACTIVE") == "ACTIVE"), None)
    if actor.actor_type != "BANK_STAFF" or (member and member.get("role") == "CUSTOMER"):
        raise HTTPException(
            status_code=403,
            detail={"code": "CASE_CONTEXT_FORBIDDEN", "message": "이 사건에 대한 작업 권한이 없습니다."},
        )
    if mvp_context_permissions(actor.actor_id):
        return case_context_v2_repository()
    scoped_actor = actor.for_case(case_id, str(member.get("role"))) if member else actor
    if not scoped_actor.can(access):
        raise HTTPException(
            status_code=403,
            detail={"code": "CASE_CONTEXT_FORBIDDEN", "message": "이 사건에 대한 작업 권한이 없습니다."},
        )
    return case_context_v2_repository()


async def require_customer_context_member(case_id: str, actor_user_id: str | None):
    if not actor_user_id:
        raise HTTPException(status_code=401, detail={"code": "ACTOR_REQUIRED", "message": "customer actor_user_id is required"})
    actor = normalize_legacy_actor(actor_user_id, actor_type="CUSTOMER")
    members = await repository.list_members(case_id)
    member = next(
        (
            item for item in members
            if item.get("user_id") == actor.actor_id
            and item.get("status", "ACTIVE") == "ACTIVE"
            and item.get("role") == "CUSTOMER"
        ),
        None,
    )
    scoped_actor = actor.for_case(case_id, "CUSTOMER") if member else actor
    if actor.actor_type != "CUSTOMER" or not scoped_actor.can("READ"):
        raise HTTPException(
            status_code=403,
            detail={"code": "CUSTOMER_CASE_FORBIDDEN", "message": "customer is not a member of this case"},
        )
    return case_context_v2_repository()


def raise_context_v2_error(exc: Exception) -> None:
    if isinstance(exc, ContextV2ConflictError):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "CONTEXT_VERSION_CONFLICT",
                "message": "다른 사용자가 먼저 변경했습니다. 최신 내용을 다시 확인해 주세요.",
                "current_version": exc.current_version,
            },
        ) from exc
    if isinstance(exc, ContextV2TransitionError):
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_CONTEXT_TRANSITION", "message": str(exc)},
        ) from exc
    if isinstance(exc, KeyError):
        raise HTTPException(
            status_code=404,
            detail={"code": "CONTEXT_RESOURCE_NOT_FOUND", "message": "요청한 사건 맥락 항목을 찾을 수 없습니다."},
        ) from exc
    raise exc


@app.get("/api/cases/{case_id}/context-v2/resources", response_model=PublicCaseContextResourcesV2)
async def read_case_context_v2_resources(case_id: str, actor_user_id: str) -> PublicCaseContextResourcesV2:
    store = await require_context_v2_member(case_id, actor_user_id, access="READ")
    try:
        return await store.list_resources(case_id)
    except (KeyError, ContextV2TransitionError, ContextV2ConflictError) as exc:
        raise_context_v2_error(exc)


@app.get("/api/cases/{case_id}/context-v2/workspace")
async def read_context_workspace(case_id: str, actor_user_id: str):
    store = await require_context_v2_member(case_id, actor_user_id, access="READ")
    resources = await store.list_resources(case_id)
    facts, actions, questions, members, gap_history = await asyncio.gather(
        repository.list_case_facts(case_id), repository.list_actions(case_id),
        repository.list_customer_questions(case_id), repository.list_members(case_id), store.list_gap_history(case_id),
    )
    result = build_workspace(resources, facts, actions, questions, gap_history)
    role = next((m.get("role") for m in members if m.get("user_id") == actor_user_id and m.get("status", "ACTIVE") == "ACTIVE"), None)
    allow_all = mvp_context_permissions(actor_user_id)
    result["permissions_mode"] = "MVP_OPEN" if allow_all else "ROLE_BASED"
    result["can_write"] = allow_all or role in {"CASE_OWNER", "CHAT_OPERATOR", "REVIEWER"}
    result["can_review"] = allow_all or role in {"CASE_OWNER", "REVIEWER"}
    result["can_review_suggestions"] = allow_all or role in {"CASE_OWNER", "CHAT_OPERATOR", "REVIEWER"}
    return result


@app.post("/api/cases/{case_id}/context-v2/legacy-suggestions/{action_id}/review", response_model=PublicSuggestionReviewResultV2)
async def review_legacy_context_suggestion(case_id: str, action_id: str, actor_user_id: str, request: PublicReviewSuggestionV2Request):
    store = await require_context_v2_member(case_id, actor_user_id, access="WRITE")
    try:
        action = next((a for a in await repository.list_actions(case_id) if a["action_id"] == action_id), None)
        if not action or not action.get("action_type", "").startswith("AI_CHECKLIST:"):
            raise KeyError(action_id)
        if action.get("status") in {"COMPLETED", "CANCELLED"}:
            raise ContextV2TransitionError("이미 완료하거나 제외한 기존 제안입니다. 최신 상태를 확인해 주세요.")
        suggestion = await store.propose_suggestion(case_id, {
            "suggestion_type": "STAFF_REVIEW", "title": user_text(action.get("note") or "기존 확인 항목 검토")[:300],
            "rationale": "기존 AI 확인 항목을 직원이 검토했습니다. 업무 채택은 사실 확정이나 고객 질문 발송을 의미하지 않습니다.",
            "priority": "HIGH", "dedupe_key": f"legacy-checklist:{action_id}",
            "evidence_refs": [{"type": "STAFF_RECORD", "id": action_id}],
        })
        reviewed, task = await store.review_suggestion(case_id, suggestion.suggestion_id, request.model_dump(mode="json"), actor_user_id)
        return PublicSuggestionReviewResultV2(suggestion=reviewed, created_task=task)
    except (KeyError, ContextV2TransitionError, ContextV2ConflictError) as exc:
        raise_context_v2_error(exc)


@app.post("/api/cases/{case_id}/context-v2/facts", response_model=PublicCaseFactV2, status_code=201)
async def create_case_context_v2_fact(case_id: str, actor_user_id: str, request: PublicCreateFactV2Request) -> PublicCaseFactV2:
    store = await require_context_v2_member(case_id, actor_user_id)
    try:
        # A staff entry is still a proposal until an owner/reviewer confirms it.
        return await store.create_fact(case_id, request.model_dump(mode="json"), actor_user_id)
    except (KeyError, ContextV2TransitionError, ContextV2ConflictError) as exc:
        raise_context_v2_error(exc)


@app.delete("/api/cases/{case_id}/context-v2/facts/{fact_id}", status_code=204)
async def delete_rejected_case_context_v2_fact(case_id: str, fact_id: str, actor_user_id: str, expected_version: int) -> None:
    """Hard-delete a rejected/archive fact only; the repository writes an audit tombstone."""
    store = await require_context_v2_member(case_id, actor_user_id, access="REVIEW")
    try:
        await store.delete_rejected_fact(case_id, fact_id, expected_version, actor_user_id)
    except (KeyError, ContextV2TransitionError, ContextV2ConflictError) as exc:
        raise_context_v2_error(exc)


@app.patch("/api/cases/{case_id}/context-v2/facts/{fact_id}/review", response_model=PublicCaseFactV2)
async def review_case_context_v2_fact(case_id: str, fact_id: str, actor_user_id: str, request: PublicReviewFactV2Request) -> PublicCaseFactV2:
    store = await require_context_v2_member(case_id, actor_user_id, access="REVIEW")
    try:
        fact = await store.review_fact(case_id, fact_id, request.expected_version, request.decision, request.reason, actor_user_id, request.supersedes_fact_id)
        if fact.status == "CONFIRMED":
            resources = await store.list_resources(case_id)
            for gap in resources.gaps:
                if gap.semantic_key == fact.semantic_key and gap.status not in {"RESOLVED", "DISMISSED"}:
                    await store.update_gap(case_id, gap.gap_id, gap.version, "RESOLVED", "확정 사실로 해소", fact.fact_id, actor_user_id)
        return fact
    except (KeyError, ContextV2TransitionError, ContextV2ConflictError) as exc:
        raise_context_v2_error(exc)


@app.post("/api/cases/{case_id}/context-v2/gaps", response_model=PublicCaseGapV2, status_code=201)
async def create_case_context_v2_gap(case_id: str, actor_user_id: str, request: PublicCreateGapV2Request) -> PublicCaseGapV2:
    store = await require_context_v2_member(case_id, actor_user_id)
    try:
        return await store.create_gap(case_id, request.model_dump(mode="json"), actor_user_id)
    except (KeyError, ContextV2TransitionError, ContextV2ConflictError) as exc:
        raise_context_v2_error(exc)


@app.patch("/api/cases/{case_id}/context-v2/gaps/{gap_id}", response_model=PublicCaseGapV2)
async def update_case_context_v2_gap(case_id: str, gap_id: str, actor_user_id: str, request: PublicUpdateGapV2Request) -> PublicCaseGapV2:
    store = await require_context_v2_member(case_id, actor_user_id)
    try:
        return await store.update_gap(case_id, gap_id, request.expected_version, request.status, request.reason, request.resolution_fact_id, actor_user_id, request.edited_title, request.edited_reason)
    except (KeyError, ContextV2TransitionError, ContextV2ConflictError) as exc:
        raise_context_v2_error(exc)


@app.post("/api/cases/{case_id}/context-v2/legacy-gaps/{action_id}", response_model=PublicCaseGapV2)
async def update_legacy_context_gap(case_id: str, action_id: str, actor_user_id: str, request: PublicUpdateGapV2Request) -> PublicCaseGapV2:
    store = await require_context_v2_member(case_id, actor_user_id)
    try:
        action = next((item for item in await repository.list_actions(case_id) if item["action_id"] == action_id), None)
        if not action or not action.get("action_type", "").startswith("AI_CHECKLIST:"):
            raise KeyError(action_id)
        if action.get("status") in {"COMPLETED", "CANCELLED"}:
            raise ContextV2TransitionError("이미 완료하거나 제외한 기존 확인 항목입니다. 최신 상태를 확인해 주세요.")
        details = legacy_gap_details(action)
        resources = await store.list_resources(case_id)
        gap = next((item for item in resources.gaps if item.semantic_key == details["semantic_key"]), None)
        if gap is None:
            gap = await store.create_gap(case_id, {
                "client_request_id": f"legacy-gap-{action_id}", **details,
                "evidence_refs": [{"type": "STAFF_RECORD", "id": action_id}],
            }, actor_user_id, source="AI")
        return await store.update_gap(case_id, gap.gap_id, request.expected_version, request.status, request.reason, request.resolution_fact_id, actor_user_id, request.edited_title, request.edited_reason)
    except (KeyError, ContextV2TransitionError, ContextV2ConflictError) as exc:
        raise_context_v2_error(exc)


@app.patch("/api/cases/{case_id}/context-v2/suggestions/{suggestion_id}/review", response_model=PublicSuggestionReviewResultV2)
async def review_case_context_v2_suggestion(case_id: str, suggestion_id: str, actor_user_id: str, request: PublicReviewSuggestionV2Request) -> PublicSuggestionReviewResultV2:
    # Chat operators are the staffed AI-suggestion review queue role; this
    # operation uses their existing WRITE permission without granting them
    # Fact review or final Task completion authority.
    store = await require_context_v2_member(case_id, actor_user_id, access="WRITE")
    try:
        suggestion, task = await store.review_suggestion(case_id, suggestion_id, request.model_dump(mode="json"), actor_user_id)
        return PublicSuggestionReviewResultV2(suggestion=suggestion, created_task=task)
    except (KeyError, ContextV2TransitionError, ContextV2ConflictError) as exc:
        raise_context_v2_error(exc)


@app.post("/api/cases/{case_id}/context-v2/tasks", response_model=PublicCaseTaskV2, status_code=201)
async def create_case_context_v2_task(case_id: str, actor_user_id: str, request: PublicCreateTaskV2Request) -> PublicCaseTaskV2:
    store = await require_context_v2_member(case_id, actor_user_id)
    try:
        return await store.create_task(case_id, request.model_dump(), actor_user_id)
    except (KeyError, ContextV2TransitionError, ContextV2ConflictError) as exc:
        raise_context_v2_error(exc)


@app.patch("/api/cases/{case_id}/context-v2/tasks/{task_id}", response_model=PublicCaseTaskV2)
async def update_case_context_v2_task(case_id: str, task_id: str, actor_user_id: str, request: PublicUpdateTaskV2Request) -> PublicCaseTaskV2:
    store = await require_context_v2_member(case_id, actor_user_id)
    try:
        return await store.update_task(case_id, task_id, request.model_dump(), actor_user_id)
    except (KeyError, ContextV2TransitionError, ContextV2ConflictError) as exc:
        raise_context_v2_error(exc)


@app.post("/api/cases/{case_id}/context-v2/tasks/{task_id}/complete", response_model=PublicCaseTaskV2)
async def complete_case_context_v2_task(case_id: str, task_id: str, actor_user_id: str, request: PublicCompleteTaskV2Request) -> PublicCaseTaskV2:
    store = await require_context_v2_member(case_id, actor_user_id, access="REVIEW")
    try:
        return await store.complete_task(case_id, task_id, request.model_dump(mode="json"), actor_user_id)
    except (KeyError, ContextV2TransitionError, ContextV2ConflictError) as exc:
        raise_context_v2_error(exc)


@app.post("/api/cases/{case_id}/context-v2/tasks/{task_id}/cancel", response_model=PublicCaseTaskV2)
async def cancel_case_context_v2_task(case_id: str, task_id: str, actor_user_id: str, request: PublicCancelTaskV2Request) -> PublicCaseTaskV2:
    store = await require_context_v2_member(case_id, actor_user_id, access="REVIEW")
    try:
        return await store.cancel_task(case_id, task_id, request.model_dump(mode="json"), actor_user_id)
    except (KeyError, ContextV2TransitionError, ContextV2ConflictError) as exc:
        raise_context_v2_error(exc)


@app.post("/api/cases/{case_id}/context-v2/decisions", response_model=PublicDecisionRecordV2, status_code=201)
async def create_case_context_v2_decision(case_id: str, actor_user_id: str, request: PublicCreateDecisionV2Request) -> PublicDecisionRecordV2:
    store = await require_context_v2_member(case_id, actor_user_id, access="REVIEW")
    try:
        return await store.create_decision(case_id, request.model_dump(mode="json"), actor_user_id)
    except (KeyError, ContextV2TransitionError, ContextV2ConflictError) as exc:
        raise_context_v2_error(exc)


@app.get('/api/cases/{case_id}/context-display')
async def read_context_display(case_id: str, actor_user_id: str):
    # 사건 화면을 여는 순간 프론트가 현재 직원을 참여자로 등록한다. 새 Case에서는
    # 그 등록과 이 조회가 동시에 도착할 수 있다. 아직 역할이 준비되지 않았다면
    # 오류나 다른 직원의 수정본을 내보내지 않고 빈 편집본으로 응답한다.
    # 로컬 MVP 모드에서만 은행 업무 권한을 개방하고, 그 외에는 PATCH도 역할을 검증한다.
    store = await context_display_repository(case_id)
    try:
        actor = normalize_legacy_actor(actor_user_id)
    except ValueError:
        return []
    members = await repository.list_members(case_id)
    member = next((item for item in members if item.get('user_id') == actor.actor_id and item.get('status', 'ACTIVE') == 'ACTIVE'), None)
    if actor.actor_type != 'BANK_STAFF' or (member and member.get('role') == 'CUSTOMER'):
        return []
    if not mvp_context_permissions(actor.actor_id) and not (
        member and actor.for_case(case_id, str(member.get('role'))).can('WRITE')
    ):
        return []
    return [item for item in await store.list_items(case_id, include_deleted=True)
            if item.semantic_key == 'display' or (item.semantic_key.startswith('display-archive:') and item.deleted_by)]


@app.patch('/api/cases/{case_id}/context-display/{section}')
async def edit_context_display(case_id: str, section: Section, actor_user_id: str, request: DisplayEditRequest):
    store = await bank_display_repository(case_id, actor_user_id)
    try:
        if request.operation == 'ARCHIVE':
            display, archive = await store.archive_line(
                case_id, section, request.expected_version, request.text,
                request.archived_text, request.archive_index, actor_user_id,
            )
            return {'display': display, 'archive': archive}
        if request.operation == 'RESTORE_ARCHIVE':
            display, archive = await store.restore_archive(
                case_id, section, request.expected_version, request.archive_item_id,
                request.archive_version, actor_user_id,
            )
            return {'display': display, 'archive': archive}
        return await store.edit_section(case_id, section, request.expected_version, request.operation, request.text, actor_user_id)
    except ContextItemConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail='삭제 항목을 찾을 수 없습니다.') from exc


@app.put('/api/cases/{case_id}/customer-progress/{step}', response_model=list[CustomerProgressItem])
async def update_customer_progress(case_id: str, step: ProgressStep, request: UpdateCustomerProgress):
    await require_case(case_id)
    try:
        await repository.create_action(case_id, {'_progress_command': {
            'step': step, 'request_confirmation': False, 'values': request.model_dump(mode='json'),
        }})
    except ProgressConflict as exc:
        raise HTTPException(status_code=409, detail={'code': 'PROGRESS_CONFLICT', 'message': str(exc)}) from exc
    return build_customer_progress(await repository.list_actions(case_id))


@app.post('/api/cases/{case_id}/customer-progress/{step}/confirmation-request', response_model=list[CustomerProgressItem])
async def request_progress_confirmation(case_id: str, step: ProgressStep):
    await require_case(case_id)
    await repository.create_action(case_id, {'_progress_command': {'step': step, 'request_confirmation': True}})
    progress = build_customer_progress(await repository.list_actions(case_id))
    item = next(value for value in progress if value.step == step)
    # Keep the request visible in both conversations. Stable request IDs make
    # retries idempotent and repair a partial notification failure on retry.
    notification_key = f"progress-confirmation-{step}-{item.revision}"
    await repository.append_message(case_id, {
        "actor_type": "CUSTOMER_AGENT", "actor_user_id": "customer-progress",
        "actor_display_name": "서비스 알림", "actor_role": "CUSTOMER_AGENT",
        "content": f"‘{item.label}’ 처리 결과 확인 요청을 담당자에게 전달했습니다.",
        "channel": "CUSTOMER", "audience": "CUSTOMER", "visibility": "CUSTOMER",
        "message_kind": "SYSTEM_EVENT", "mentions": [],
        "client_request_id": f"{notification_key}-customer", "log_event": False,
    })
    await repository.append_message(case_id, {
        "actor_type": "CUSTOMER", "actor_user_id": "customer-progress",
        "actor_display_name": "고객 확인 요청", "actor_role": "CUSTOMER",
        "content": f"고객이 ‘{item.label}’ 처리 결과 확인을 요청했습니다. 담당자 결과 등록이 필요합니다.",
        "channel": "TEAM", "audience": "BANK_INTERNAL", "visibility": "BANK_INTERNAL",
        "message_kind": "SYSTEM_EVENT", "mentions": [],
        "client_request_id": f"{notification_key}-bank", "log_event": True,
    })
    return progress


@app.post("/api/cases/{case_id}/actions", response_model=PublicActionResponse, status_code=201)
async def create_case_action(case_id: str, actor_user_id: str, request: PublicCreateActionRequest) -> PublicActionResponse:
    await require_context_v2_member(case_id, actor_user_id, access="WRITE")
    if request.action_type.startswith(PROGRESS_PREFIX):
        raise HTTPException(status_code=422, detail='고객 처리 상태는 전용 처리 결과 화면에서 기록해 주세요.')
    try:
        return to_public_action(await repository.create_action(case_id, request.model_dump()))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."}) from exc


@app.patch("/api/cases/{case_id}/actions/{action_id}", response_model=PublicActionResponse)
async def update_case_action(case_id: str, action_id: str, actor_user_id: str, request: PublicUpdateActionRequest) -> PublicActionResponse:
    await require_context_v2_member(case_id, actor_user_id, access="WRITE")
    actions = await repository.list_actions(case_id)
    current = next((item for item in actions if item['action_id'] == action_id), None)
    if current and current['action_type'].startswith(PROGRESS_PREFIX):
        raise HTTPException(status_code=422, detail='고객 처리 상태 이력은 일반 체크리스트로 변경할 수 없습니다.')
    try:
        if current is None and request.status is None:
            raise KeyError(action_id)
        next_status = request.status or current.get('status', 'REQUESTED')
        if request.note is None:
            updated = await repository.update_action(case_id, action_id, next_status, request.updated_by)
        else:
            updated = await repository.update_action(case_id, action_id, next_status, request.updated_by, request.note)
        return to_public_action(updated)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CASE_ACTION_NOT_FOUND", "message": "체크리스트 항목을 찾을 수 없습니다."}) from exc


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
    action_records = await repository.list_actions(case_id)
    customer_progress = build_customer_progress(action_records)
    actions = [to_public_action(item) for item in action_records if not item['action_type'].startswith(PROGRESS_PREFIX)]
    verifications = [to_public_verification(item) for item in await repository.list_verifications(case_id)]
    question_records = await repository.list_customer_questions(case_id)
    questions = [to_public_customer_question(item).model_dump(mode="json") for item in question_records]
    progress_items = [
        {"key": "customer_questions", "total": len(question_records), "answered": sum(item.get("status") == "ANSWERED" for item in question_records)},
        {"key": "verification_tasks", "total": len(verifications), "completed": sum(item.status == "COMPLETED" for item in verifications)},
    ]
    customer_verification_results: list[PublicCustomerVerificationResult] = []
    events = [to_public_event(item).model_dump(mode="json") for item in await repository.list_events(case_id)]
    # Customer view hides event details, but still needs the Case activity cursor
    # to identify the latest synchronized state.
    cursor = str(events[-1]["event_id"]) if events else None
    voice = await repository.get_voice_session(case_id)
    final_report = None
    if view != "customer" and (record.get("status") == "CLOSED" or record.get("mode") == "CLOSED"):
        stored_final_report = await repository.get_final_report(case_id)
        if stored_final_report:
            final_report = PublicReportResponse.model_validate(stored_final_report)
    if view == "customer":
        questions = [to_public_customer_question_view(item).model_dump(mode="json") for item in question_records]
        customer_verification_results = [
            PublicCustomerVerificationResult(
                verification_task_id=item.verification_task_id,
                target=item.target,
                result_summary=item.result_summary,
                published_at=item.updated_at,
            )
            for item in verifications
            if item.status == "COMPLETED" and item.customer_visible and item.result_summary
        ]
        messages = [item for item in messages if item.get("visibility") == "CUSTOMER"]
        actions, verifications, events, voice = [], [], [], None
    return PublicCaseBundleResponse(
        customer_progress=customer_progress,
        case=to_public_case_summary_response(record).model_dump(mode="json"),
        live_report=None if view == "customer" else record.get("initial_report"),
        questions=questions, progress_items=progress_items, verification_tasks=verifications,
        customer_verification_results=customer_verification_results,
        recent_messages=messages[-50:], recent_actions=actions if view == "bank" else actions[-50:], recent_events=events[-50:],
        voice_session=PublicVoiceSessionResponse.model_validate(voice) if voice else None,
        final_report=final_report,
        cursor=cursor,
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
async def finalize_case_report(case_id: str, request: AdminCaseFinalizeRequest) -> PublicReportResponse:
    require_admin_password(request.password)
    try:
        case = await repository.get(case_id)
        if case is None:
            raise KeyError(case_id)
        facts, verifications, actions, messages, questions = await asyncio.gather(
            repository.list_case_facts(case_id),
            repository.list_verifications(case_id),
            repository.list_actions(case_id),
            repository.list_messages(case_id),
            repository.list_customer_questions(case_id),
        )
        staff = await read_staff_context_records(case_id)
        ai_report = await service.ai_client.generate_final_report({
            "case_id": case_id,
            "case_summary": case.get("initial_brief", ""),
            "workflow_status": case.get("status", "TRIAGE"),
            "case_mode": case.get("mode", "PREVENT"),
            "staff_context": staff_context(staff),
            "known_facts": [user_text(f"{item.get('field')}: {item.get('value')} ({item.get('status')})") for item in facts[:40]],
            "recent_conversation": [
                f"{item.get('actor_display_name', item.get('actor_type', '작성자'))}: {item.get('content', '')[:500]}"
                for item in messages[-30:] if item.get("message_kind") != "REPORT_CARD" and item.get("visibility") != "AI_PRIVATE"
            ],
            "verification_results": [
                f"{item.get('target')}: {item.get('result_summary') or item.get('claim')} ({item.get('status')})"
                for item in verifications[:30]
            ],
            "action_results": [
                user_text(f"{item.get('action_type')}: {item.get('note') or '상세 내용 없음'} ({item.get('status')})")
                for item in actions_for_ai(actions)[:30]
            ],
            "customer_answers": [
                f"질문: {item.get('question_text')} / 고객 답변: {item.get('answer_text')}"
                for item in questions if item.get("answer_text")
            ][:30],
            "closure_note": request.note,
        })
        report_card = {
            "title": ai_report["title"],
            "executive_summary": ai_report["executive_summary"],
            "incident_summary": ai_report["incident_summary"],
            "customer_impact_summary": ai_report.get("customer_impact_summary", "확인된 고객 피해·노출 정보가 없습니다."),
            "verified_facts": ai_report.get("verified_facts", []),
            "verification_results": ai_report.get("verification_results", []),
            "actions_taken": ai_report.get("actions_taken", []),
            "unresolved_items": ai_report.get("unresolved_items", []),
            "decision_basis": ai_report.get("decision_basis", []),
            "resolution": ai_report["resolution"],
            "follow_up": ai_report.get("follow_up", []),
            "cautions": ai_report.get("cautions", []),
            "model_mode": ai_report.get("model_mode", "AI"),
        }
        sections = [
            {"section_key": "title", "content": {"text": report_card["title"]}},
            {"section_key": "executive_summary", "content": {"text": report_card["executive_summary"]}},
            {"section_key": "incident_summary", "content": {"text": report_card["incident_summary"]}},
            {"section_key": "customer_impact_summary", "content": {"text": report_card["customer_impact_summary"]}},
            {"section_key": "verified_facts", "content": {"items": report_card["verified_facts"]}},
            {"section_key": "verification_results", "content": {"items": report_card["verification_results"]}},
            {"section_key": "actions_taken", "content": {"items": report_card["actions_taken"]}},
            {"section_key": "unresolved_items", "content": {"items": report_card["unresolved_items"]}},
            {"section_key": "decision_basis", "content": {"items": report_card["decision_basis"]}},
            {"section_key": "resolution", "content": {"text": report_card["resolution"], "closure_note": request.note}},
            {"section_key": "follow_up", "content": {"items": report_card["follow_up"]}},
            {"section_key": "cautions", "content": {"items": report_card["cautions"]}},
        ]
        report = await repository.finalize_report(case_id, request.expected_version, request.note, sections, report_card)
    except AiServiceQuotaError as exc:
        raise HTTPException(status_code=429, detail={"code": "OPENAI_QUOTA_EXHAUSTED", "message": str(exc)}) from exc
    except AiServiceAuthenticationError as exc:
        raise HTTPException(status_code=401, detail={"code": "OPENAI_AUTHENTICATION_FAILED", "message": str(exc)}) from exc
    except AiServiceError as exc:
        raise HTTPException(status_code=503, detail={"code": "AI_FINAL_REPORT_FAILED", "message": str(exc)}) from exc
    except CaseVersionConflictError as exc:
        raise HTTPException(status_code=409, detail={"code": "VERSION_CONFLICT", "message": "Case has changed.", "current_version": exc.current_version}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": str(exc), "message": "현재 사건 상태에서는 요청한 변경을 수행할 수 없습니다."}) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found."}) from exc
    return PublicReportResponse.model_validate(report)


@app.post("/api/cases/{case_id}/reopen", response_model=PublicCaseReadResponse, response_model_exclude_none=True)
async def reopen_closed_case(case_id: str, request: AdminCaseReopenRequest) -> PublicCaseReadResponse:
    require_admin_password(request.password)
    try:
        record = await repository.reopen_case(case_id, request.expected_version)
    except CaseVersionConflictError as exc:
        raise HTTPException(status_code=409, detail={"code": "VERSION_CONFLICT", "message": "Case has changed.", "current_version": exc.current_version}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": str(exc), "message": "종결된 사건만 다시 진행할 수 있습니다."}) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found."}) from exc
    return await to_case_read(record)


@app.get("/api/cases/{case_id}/reports/final", response_model=PublicReportResponse)
async def get_final_case_report(case_id: str) -> PublicReportResponse:
    await require_case(case_id)
    report = await repository.get_final_report(case_id)
    if report is None:
        raise HTTPException(status_code=404, detail={"code": "FINAL_REPORT_NOT_FOUND", "message": "Final report not found."})
    return PublicReportResponse.model_validate(report)


def _report_export_lines(case_id: str, report: dict) -> list[tuple[str, list[str]]]:
    labels = {
        "title": "보고서 제목", "executive_summary": "종합 요약", "incident_summary": "사건 개요",
        "customer_impact_summary": "고객 피해·노출 상태", "verified_facts": "확인된 사실",
        "verification_results": "기관 확인 결과", "actions_taken": "대응 및 처리 내역",
        "unresolved_items": "남은 미확인 사항", "decision_basis": "종결 판단 근거",
        "resolution": "최종 처리 결과", "follow_up": "후속 업무", "cautions": "유의사항",
    }
    blocks: list[tuple[str, list[str]]] = [("보고서 정보", [f"Case ID: {case_id}", f"보고서 버전: {report.get('report_version', 1)}", f"생성 시각: {report.get('created_at', '')}"])]
    for section in report.get("sections", []):
        content = section.get("content") or {}
        lines: list[str] = []
        if content.get("text"):
            lines.append(user_text(str(content["text"])))
        lines.extend(user_text(str(item)) for item in content.get("items", []) if str(item).strip())
        if content.get("closure_note"):
            lines.append(f"담당자 종결 메모: {content['closure_note']}")
        if lines:
            blocks.append((labels.get(section.get("section_key"), "추가 보고 내용"), lines))
    return blocks


@app.get("/api/cases/{case_id}/reports/final/export")
async def export_final_case_report(case_id: str, format: Literal["pdf", "docx"] = "pdf") -> StreamingResponse:
    await require_case(case_id)
    report = await repository.get_final_report(case_id)
    if report is None:
        raise HTTPException(status_code=404, detail={"code": "FINAL_REPORT_NOT_FOUND", "message": "Final report not found."})
    blocks = _report_export_lines(case_id, report)
    output = io.BytesIO()
    if format == "docx":
        from docx import Document

        document = Document()
        document.add_heading("CSR | Case Share Room 최종 결과 보고서", 0)
        for heading, lines in blocks:
            document.add_heading(heading, level=1)
            for line in lines:
                document.add_paragraph(line, style="List Bullet" if len(lines) > 1 else None)
        document.save(output)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.pdfgen import canvas

        pdfmetrics.registerFont(UnicodeCIDFont("HYSMyeongJo-Medium"))
        page = canvas.Canvas(output)
        page.setTitle(f"CSR {case_id} 최종 결과 보고서")
        width, height = page._pagesize
        y = height - 48
        page.setFont("HYSMyeongJo-Medium", 16)
        page.drawString(44, y, "CSR | Case Share Room 최종 결과 보고서")
        y -= 30
        for heading, lines in blocks:
            if y < 90:
                page.showPage(); y = height - 48
            page.setFont("HYSMyeongJo-Medium", 12); page.drawString(44, y, heading); y -= 20
            page.setFont("HYSMyeongJo-Medium", 9)
            for line in lines:
                chunks = [line[index:index + 64] for index in range(0, len(line), 64)] or [""]
                for chunk in chunks:
                    if y < 58:
                        page.showPage(); page.setFont("HYSMyeongJo-Medium", 9); y = height - 48
                    page.drawString(54, y, f"• {chunk}"); y -= 15
            y -= 8
        page.save()
        media_type = "application/pdf"
    output.seek(0)
    file_name = f"CSR-{case_id}-final-report.{format}"
    return StreamingResponse(output, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{file_name}"'})
