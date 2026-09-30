from __future__ import annotations

import asyncio
import io
import json
import os
import hashlib
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator
from .domains.cases.context_items import (
    Section, RightPanelSection, ContextItem, ContextItemChange, ContextItemConflictError,
)
from .domains.cases.context_item_repository import ContextItemRepository, InMemoryContextItemRepository
from .domains.cases.right_panel_projection import build_right_panel_projection
from .domains.cases.copilot_state import read_operational_state, digest
from .domains.cases.copilot_jobs import CopilotJobs
from .domains.cases.copilot_tasks import apply_task_intents
from contracts.public_api.collaboration import PublicGuidanceRequest
from .core.actor_context import normalize_legacy_actor

from contracts.diagnosis import AnalyzeTextRequest
from contracts.ai_internal.context_fact_extraction import ContextFactExtractionInput, ContextFactExtractionMessage, ExistingContextFact
from contracts.ai_internal.mvp_workflow import TargetField
from ai_api.app.domains.case_support.answer_service import CustomerAnswerStructuringService
from ai_api.app.domains.case_support.case_snapshot_adapter import CaseSnapshotAiAdapter
from ai_api.app.domains.case_support.question_policy import validate_follow_up_question
from contracts.question_target import canonical_question_scope, is_follow_up_target
from contracts.public_api.customer_progress import CustomerProgressItem, ProgressStep, UpdateCustomerProgress
from .domains.cases.customer_progress import PREFIX as PROGRESS_PREFIX, ProgressConflict, progress_items as build_customer_progress, progress_ai_context, actions_for_ai
from request_trace import install_request_trace
from audio_upload import MAX_AUDIO_BYTES, read_audio_upload
from contracts.ai_internal.work_card import CaseWorkCardOutput, WorkCardType
from contracts.user_text import user_text
from .domains.cases.context_workspace import build_workspace, legacy_gap_details
from .domains.cases.case_retrieval import SEMANTIC_FIELDS, collect_records, retrieve_context, similar_question, staff_context, workspace_records, merge_support_records, bank_source_context
from contracts.public_api.case_analyze import (
    PublicAnalyzeCaseRequest,
    PublicAnalyzeCaseResponse,
    PublicAnalyzeError,
    PublicInitialReportReference,
)
from contracts.public_api.case_read import PublicCaseReadResponse, to_public_case_read_response, to_public_case_summary_response
from contracts.public_api.case_transition import PublicCasePatchRequest
from contracts.public_api.case_transactions import (
    PublicCaseTransactionCreateRequest,
    PublicCaseTransactionPatchRequest,
    PublicCaseTransactionResponse,
)
from contracts.public_api.case_context_v2 import (
    PublicAiSuggestionV2,
    PublicCancelTaskV2Request,
    PublicCaseContextResourcesV2,
    PublicCaseFactV2,
    PublicCaseGapV2,
    PublicCaseTaskV2,
    PublicContextWorkspaceResponse,
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
    PublicCreateMessageRequest,
    PublicCustomerEmergencyRequest,
    PublicMessageResponse,
    to_public_event,
    to_public_message,
)
from contracts.public_api.case_workflow import (
    PublicActionResponse,
    PublicAnswerCustomerQuestionRequest,
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
    PublicReportResponse,
    PublicCreateVerificationRequest,
    PublicCustomerQuestionResponse,
    PublicCustomerQuestionView,
    PublicCustomerVerificationResult,
    PublicQuestionCandidateResponse,
    PublicCaseContextProjection,
    PublicRightPanelProjection,
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
    PublicRecommendedChatAction,
    PublicAiShareRequest,
    PublicCustomerAiReplyRequest,
    PublicCaseMemberResponse,
    PublicCaseMemberUpsertRequest,
    PublicCasePresenceResponse,
    PublicPresenceHeartbeatRequest,
    PublicPrimaryAssigneeRequest,
    PublicPrimaryAssigneeResponse,
)
from contracts.public_api.bank_staff import (
    PublicBankStaffCreateRequest,
    PublicBankStaffResponse,
    PublicBankStaffUpdateRequest,
)

from .clients.diagnosis_ai import AiServiceAuthenticationError, AiServiceBudgetError, AiServiceError, AiServiceQuotaError, HttpDiagnosisAiClient
from .domains.cases.repository import CasePersistenceError, CaseVersionConflictError, normalize_target_field
from .domains.cases.member_roles import case_role_for_member
from .domains.cases.context_projection_repository import ContextProjectionRepository
from .domains.cases.case_context_v2_repository import (
    ContextV2ConflictError,
    ContextV2TransitionError,
    InMemoryCaseContextV2Repository,
    MySqlCaseContextV2Repository,
)
from .domains.cases.mysql_repository import MySqlCaseRepository
from .domains.cases.context_v3.semantic_keys import ALLOWED_SEMANTIC_KEYS, SEMANTIC_LABELS, proposal_dedupe_key
from .domains.cases.context_v3.panel import build_context_panel_v3, build_summary_projection
from .domains.cases.context_v3.atom_fact_projection import project_semantic_atoms_to_fact_candidates
from .domains.cases.transaction_conflict import (
    TRANSACTION_AMOUNT_CONFLICT_TARGET,
    conflict_client_request_id,
    detect_transfer_amount_conflict,
)


def normalize_public_recommended_actions(raw: object, channel: str) -> list[PublicRecommendedChatAction]:
    """Expose only bank-internal, allowlisted action metadata to the frontend."""
    if channel != "TEAM" or not isinstance(raw, list):
        return []
    result: list[PublicRecommendedChatAction] = []
    seen: set[str] = set()
    preference = {"CUSTOMER_QUESTION": 0, "OFFICIAL_VERIFICATION": 1, "RESPONSE_ACTION": 2,
                  "DRAFT_REPLY": 3, "TRANSACTION_LOOKUP": 4}
    for candidate in raw[:12]:
        try:
            action = PublicRecommendedChatAction.model_validate(candidate)
        except Exception:
            continue
        if action.action_key in seen:
            continue
        if action.kind == "TOOL" and action.target_channel != "TEAM":
            continue
        # TRANSACTION_LOOKUP is a demo-only flow. Keep it out of AI suggestions.
        if action.action_key == "TRANSACTION_LOOKUP":
            continue
        if action.kind == "REPLY_DRAFT":
            if action.action_key != "DRAFT_REPLY" or action.target_channel != "CUSTOMER" or not action.draft_text or not action.draft_text.strip():
                continue
        elif action.action_key == "DRAFT_REPLY":
            continue
        seen.add(action.action_key)
        result.append(action)
    return sorted(result, key=lambda action: preference.get(action.action_key, 99))[:3]


def fallback_case_recommendations(content: str, prompt: str, state) -> list[dict]:
    """Fill missing relevant bank tools when the model omits them or suggests demo lookup."""
    candidates: list[dict] = []
    active_tasks = [task for task in state.tasks
                    if task.get("status") not in {"COMPLETED", "CANCELLED"}]
    task_action_keys = {
        "CUSTOMER_CONTACT": "CUSTOMER_QUESTION",
        "INSTITUTION_VERIFICATION": "OFFICIAL_VERIFICATION",
        "PROTECTIVE_ACTION": "RESPONSE_ACTION",
        "DOCUMENT_REVIEW": "RESPONSE_ACTION",
    }
    task_priority = {"CUSTOMER_CONTACT": 0, "INSTITUTION_VERIFICATION": 1,
                     "PROTECTIVE_ACTION": 2, "DOCUMENT_REVIEW": 3}
    for task in sorted(active_tasks, key=lambda item: task_priority.get(item.get("task_type"), 99)):
        action_key = task_action_keys.get(task.get("task_type"))
        if not action_key:
            continue
        candidates.append({
            "action_key": action_key,
            "kind": "TOOL",
            "target_channel": "TEAM",
            "target_type": "TASK",
            "target_id": task.get("task_id"),
            "expected_version": task.get("version"),
        })

    answer_and_prompt = f"{content}\n{prompt}".lower()
    diagnosis = state.case.get("diagnosis") or {}
    case_context = f"{state.summary}\n{json.dumps(diagnosis, ensure_ascii=False, default=str)}".lower()
    combined = f"{answer_and_prompt}\n{case_context}"
    actionable = any(term in answer_and_prompt for term in (
        "확인", "미확인", "질문", "필요", "해야", "안내", "조치", "대응", "검토", "진행", "중단",
    ))
    if not actionable:
        return []
    customer_uncertain = any(term in combined for term in (
        "미확인", "아직 확인되지", "확인되지 않았", "여부", "고객에게 확인", "고객 확인", "질문해야",
    ))
    pending_questions = any(question.get("status") == "PENDING" for question in state.questions)
    waiting_for_customer = any(question.get("status") == "ASKED" for question in state.questions)
    if customer_uncertain and pending_questions:
        candidates.append({"action_key": "CUSTOMER_QUESTION", "kind": "TOOL", "target_channel": "TEAM"})
    elif customer_uncertain and not waiting_for_customer:
        candidates.append({"action_key": "CUSTOMER_QUESTION", "kind": "TOOL", "target_channel": "TEAM"})

    institution_uncertain = any(term in combined for term in (
        "사칭", "소속 미확인", "공식 확인", "기관 확인", "담당자 확인",
    ))
    active_verifications = [item for item in state.verifications
                            if item.get("status") not in {"COMPLETED", "CANCELLED", "SKIPPED"}]
    institution_terms = ("기관", "담당자", "소속", "대출", "경찰", "검찰", "금융")
    completed_institution_verification = any(
        item.get("status") == "COMPLETED"
        and any(term in " ".join(str(item.get(key, "")) for key in ("claim", "target", "result_summary"))
                for term in institution_terms)
        for item in state.verifications
    )
    if institution_uncertain and (active_verifications or not completed_institution_verification):
        candidates.append({"action_key": "OFFICIAL_VERIFICATION", "kind": "TOOL", "target_channel": "TEAM"})

    protection_needed = any(term in answer_and_prompt for term in (
        "추가 송금 중단", "연락 중단", "앱 삭제", "원격 제어 차단", "계정 보호", "지급정지",
    ))
    has_active_protective_task = any(task.get("task_type") == "PROTECTIVE_ACTION" for task in active_tasks)
    if protection_needed and has_active_protective_task:
        candidates.append({"action_key": "RESPONSE_ACTION", "kind": "TOOL", "target_channel": "TEAM"})
    return candidates
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
BASELINE_QUESTION_FIELDS = AUTONOMOUS_P0_QUESTION_FIELDS | {"claimed_organization", "impersonated_institution"}
MANUAL_BASIC_QUESTION_FIELDS = AUTONOMOUS_P0_QUESTION_FIELDS | {
    "transfer_purpose", "claimed_organization", "incident_claim",
    TRANSACTION_AMOUNT_CONFLICT_TARGET,
}
AI_CHECKLIST_ACTION_PREFIX = "AI_CHECKLIST:"
CURRENT_BANK_USER_ID = os.getenv("CURRENT_BANK_USER_ID", "mvp-v3-bank-operator")
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

ATTACHMENTS_DISABLED_MESSAGE = "데모에서는 메시지 첨부파일을 지원하지 않습니다. 텍스트로 입력해 주세요."
service = AnalyzeCaseService(HttpDiagnosisAiClient(), repository)
BACKGROUND_ANALYSIS_THRESHOLD = 12_000
BACKGROUND_ANALYSIS_PREVIEW_CHARS = 4_500
_background_analysis_tasks: dict[str, asyncio.Task] = {}


def initial_analysis_excerpt(text: str) -> str:
    """Keep the first pass small, but end on a turn/sentence boundary when possible."""
    if len(text) <= BACKGROUND_ANALYSIS_PREVIEW_CHARS:
        return text
    excerpt = text[:BACKGROUND_ANALYSIS_PREVIEW_CHARS]
    newline = excerpt.rfind("\n")
    punctuation = max(excerpt.rfind("."), excerpt.rfind("?"), excerpt.rfind("!"), excerpt.rfind("다."))
    boundary = max(newline, punctuation)
    if boundary >= BACKGROUND_ANALYSIS_PREVIEW_CHARS // 2:
        excerpt = excerpt[:boundary + 1]
    return excerpt.strip()


async def _run_background_case_analysis(case_id: str) -> None:
    try:
        record = await repository.get(case_id)
        if not record or record.get("analysis_status") != "IN_PROGRESS":
            return
        await seed_initial_context_facts(case_id)
        source_text = str(record.get("input_text") or "").strip()
        if not source_text:
            raise ValueError("전체 분석 원문이 없어 후속 분석을 진행할 수 없습니다.")
        result = await service.complete_background_analysis(case_id, source_text)
        if result.analysis_status in {"COMPLETED", "NO_CASE"}:
            await seed_initial_context_facts(case_id)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Background Case analysis failed", extra={"case_id": case_id})
        current = await repository.get(case_id)
        if current and current.get("analysis_status") == "IN_PROGRESS":
            try:
                await repository.update_case(case_id, int(current.get("version", 1)), {"analysis_status": "FAILED"})
            except Exception:
                logger.exception("Could not persist failed analysis status", extra={"case_id": case_id})
    finally:
        _background_analysis_tasks.pop(case_id, None)


def schedule_background_case_analysis(case_id: str) -> None:
    if case_id in _background_analysis_tasks:
        return
    _background_analysis_tasks[case_id] = asyncio.create_task(_run_background_case_analysis(case_id))


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or f"req-{uuid4().hex}"
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


def public_failed_response(code: str, message: str, *, retryable: bool) -> PublicAnalyzeCaseResponse:
    return PublicAnalyzeCaseResponse(
        disposition="FAILED",
        analysis_status=None,
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
            analysis_status="NO_CASE",
        )

    report = result.initial_report
    return PublicAnalyzeCaseResponse(
        disposition="CASE_CREATED",
        case_id=result.case_id,
        risk=result.risk.value if hasattr(result.risk, "value") else result.risk,
        mode=result.mode,
        status=result.status,
        initial_brief=result.initial_brief,
        analysis_status=result.analysis_status or "COMPLETED",
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


@app.post("/api/audio/transcriptions")
async def proxy_audio_transcription(request: Request) -> StreamingResponse:
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

    ai_base_url = os.getenv("AI_API_BASE_URL", "http://127.0.0.1:8101").rstrip("/")
    client = httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=15.0))
    try:
        outbound = client.build_request(
            "POST",
            f"{ai_base_url}/ai/audio/transcriptions/stream",
            content=upload.content,
            headers={
                "Content-Type": upload.content_type,
                "Content-Length": str(len(upload.content)),
                "X-Audio-Filename": request.headers.get("X-Audio-Filename", ""),
            },
        )
        upstream = await client.send(outbound, stream=True)
    except httpx.TimeoutException as exc:
        await client.aclose()
        raise HTTPException(status_code=504, detail={"code": "AI_PROVIDER_TIMEOUT", "message": "음성 전사 서버 응답 시간이 초과되었습니다."}) from exc
    except httpx.HTTPError as exc:
        await client.aclose()
        raise HTTPException(status_code=503, detail={"code": "AI_PROVIDER_UNAVAILABLE", "message": "AI 음성 전사 서버에 연결할 수 없습니다."}) from exc

    if upstream.is_error:
        body = await upstream.aread()
        await upstream.aclose()
        await client.aclose()
        try:
            detail = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            detail = {"code": "AI_PROVIDER_UNAVAILABLE", "message": "음성 전사를 처리하지 못했습니다."}
        raise HTTPException(status_code=upstream.status_code, detail=detail.get("detail", detail))

    async def events():
        try:
            async for chunk in upstream.aiter_raw():
                yield chunk
        finally:
            await upstream.aclose()
            await client.aclose()

    return StreamingResponse(events(), status_code=upstream.status_code, media_type="text/event-stream", headers={
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
    })


@app.exception_handler(RequestValidationError)
async def public_analyze_validation_error(request: Request, exc: RequestValidationError):
    if request.url.path == "/api/cases/analyze":
        failure = public_failed_response("INVALID_INPUT", "요청 형식을 확인해 주세요.", retryable=False)
        return JSONResponse(status_code=400, content=failure.model_dump(mode="json"))
    return await request_validation_exception_handler(request, exc)


@app.post("/api/cases/analyze", response_model=PublicAnalyzeCaseResponse, status_code=201)
async def analyze_case(request: PublicAnalyzeCaseRequest) -> PublicAnalyzeCaseResponse | JSONResponse:
    full_text = request.text.strip()
    use_background_completion = request.background_completion and len(full_text) >= BACKGROUND_ANALYSIS_THRESHOLD
    first_pass_text = initial_analysis_excerpt(full_text) if use_background_completion else full_text
    internal_request = AnalyzeTextRequest(text=first_pass_text, client_request_id=request.client_request_id)
    try:
        result = await service.analyze(
            internal_request,
            source_text=full_text,
            provisional=use_background_completion,
        )
        if result.disposition == "CASE_CREATED" and result.case_id:
            if result.analysis_status == "IN_PROGRESS":
                schedule_background_case_analysis(result.case_id)
            else:
                try:
                    await seed_initial_context_facts(result.case_id)
                except Exception:
                    logger.exception("Case was committed but initial Context V3 facts could not be seeded")
        return to_public_analyze_response(result)
    except ValueError as exc:
        failure = public_failed_response("INVALID_INPUT", str(exc), retryable=False)
        return JSONResponse(status_code=400, content=failure.model_dump(mode="json"))
    except AiServiceBudgetError as exc:
        failure = public_failed_response("AI_BUDGET_LIMIT_REACHED", str(exc), retryable=False)
        return JSONResponse(status_code=429, content=failure.model_dump(mode="json"))
    except AiServiceQuotaError as exc:
        failure = public_failed_response("OPENAI_QUOTA_EXHAUSTED", str(exc), retryable=False)
        return JSONResponse(status_code=429, content=failure.model_dump(mode="json"))
    except AiServiceAuthenticationError as exc:
        failure = public_failed_response("OPENAI_AUTHENTICATION_FAILED", str(exc), retryable=False)
        return JSONResponse(status_code=401, content=failure.model_dump(mode="json"))
    except AiServiceError as exc:
        # Preserve the AI API's actionable runtime code when it is part of
        # the public analyze contract. Unknown/legacy client errors keep the
        # existing generic code for backwards compatibility.
        public_codes = {"AI_PROVIDER_UNAVAILABLE", "AI_PROVIDER_TIMEOUT"}
        code = exc.code if exc.code in public_codes else "AI_ANALYSIS_FAILED"
        failure = public_failed_response(code, str(exc), retryable=exc.retryable)
        return JSONResponse(status_code=503, content=failure.model_dump(mode="json"))
    except CasePersistenceError:
        failure = public_failed_response("CASE_SAVE_FAILED", "AI 분석 후 사건 저장을 완료하지 못했습니다.", retryable=True)
        return JSONResponse(status_code=503, content=failure.model_dump(mode="json"))
    except Exception as exc:
        failure = public_failed_response("AI_ANALYSIS_FAILED", "진단을 완료하지 못했습니다.", retryable=True)
        return JSONResponse(status_code=503, content=failure.model_dump(mode="json"))


async def to_case_read(record: dict) -> PublicCaseReadResponse:
    members = await repository.list_members(record["case_id"])
    primary = next((item.get("display_name") for item in members if case_role_for_member(item) == "CASE_OWNER"), None)
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

@app.get("/api/cases/{case_id}/transactions", response_model=list[PublicCaseTransactionResponse])
async def list_case_transactions(case_id: str):
    if await repository.get(case_id) is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found"})
    return await repository.list_transactions(case_id)

@app.post("/api/cases/{case_id}/transactions", response_model=PublicCaseTransactionResponse, status_code=201)
async def create_case_transaction(case_id: str, request: PublicCaseTransactionCreateRequest):
    if await repository.get(case_id) is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found"})
    return await repository.create_transaction(case_id, request.model_dump())

@app.patch("/api/cases/{case_id}/transactions/{transaction_id}", response_model=PublicCaseTransactionResponse)
async def update_case_transaction(case_id: str, transaction_id: int, request: PublicCaseTransactionPatchRequest):
    if await repository.get(case_id) is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found"})
    changes = request.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail={"code": "EMPTY_PATCH", "message": "At least one field is required"})
    updated = await repository.update_transaction(case_id, transaction_id, changes)
    if updated is None:
        raise HTTPException(status_code=404, detail={"code": "TRANSACTION_NOT_FOUND", "message": "Transaction not found"})
    return updated


def _bank_staff_response(item: dict) -> PublicBankStaffResponse:
    return PublicBankStaffResponse.model_validate({**item, "is_self": item.get("linked_user_id") == CURRENT_BANK_USER_ID})


@app.get("/api/bank/staff", response_model=list[PublicBankStaffResponse])
async def list_bank_staff() -> list[PublicBankStaffResponse]:
    return [_bank_staff_response(item) for item in await repository.list_bank_staff()]


@app.post("/api/bank/staff", response_model=PublicBankStaffResponse, status_code=201)
async def create_bank_staff(request: PublicBankStaffCreateRequest) -> PublicBankStaffResponse:
    return _bank_staff_response(await repository.create_bank_staff(request.model_dump()))


@app.patch("/api/bank/staff/{staff_id}", response_model=PublicBankStaffResponse)
async def update_bank_staff(staff_id: str, request: PublicBankStaffUpdateRequest) -> PublicBankStaffResponse:
    updated = await repository.update_bank_staff(staff_id, request.model_dump())
    if updated is None:
        raise HTTPException(status_code=404, detail={"code": "BANK_STAFF_NOT_FOUND", "message": "은행 담당자를 찾을 수 없습니다."})
    return _bank_staff_response(updated)


@app.delete("/api/bank/staff/{staff_id}", status_code=204)
async def delete_bank_staff(staff_id: str) -> None:
    existing = next((item for item in await repository.list_bank_staff() if item.get("staff_id") == staff_id), None)
    if existing is None:
        raise HTTPException(status_code=404, detail={"code": "BANK_STAFF_NOT_FOUND", "message": "은행 담당자를 찾을 수 없습니다."})
    await repository.delete_bank_staff(staff_id)


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
    try:
        await repository.purge_case(case_id)
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
                "supersedes_fact_id": proposal.supersedes_fact_id,
                "evidence_refs": [{"type": "MESSAGE", "id": message_id}], "visibility": "BANK_INTERNAL",
            }, message.get("actor_user_id") or "context-extractor",
                source_kind="CUSTOMER_STATEMENT" if message["actor_type"] == "CUSTOMER" else "STAFF_OBSERVATION")
        for observation in getattr(output, "unmapped_observations", []):
            await store.create_unmapped_observation(
                case_id,
                observation.model_dump(mode="json"),
                message.get("actor_user_id") or "context-extractor",
            )
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


async def settle_copilot_source_extractions(case_id: str, requester_user_id: str | None,
                                            source_message_ids: list[str], messages: list[dict]) -> bool:
    """Prefer a persisted extraction before Copilot reads the just-sent staff message."""
    message_by_id = {item.get("message_id"): item for item in messages if item.get("message_id")}
    relevant = [message_by_id.get(message_id) for message_id in source_message_ids[-20:]]
    relevant = [item for item in relevant if item
                and item.get("case_id", case_id) == case_id
                and item.get("actor_type") == "BANK_STAFF"
                and item.get("actor_user_id") == requester_user_id
                and item.get("message_kind", "CHAT") == "CHAT"
                and item.get("visibility") == "BANK_INTERNAL"]
    pending = False
    for message in relevant:
        try:
            job = await repository.get_message_extraction(case_id, message["message_id"])
            if not job:
                continue
            if job.get("status") == "PENDING":
                await process_message_context_extraction(case_id, message["message_id"])
                job = await repository.get_message_extraction(case_id, message["message_id"])
            # A POST /messages background task may already own the lease. Wait
            # briefly for it rather than reading a known-stale Fact snapshot.
            for _ in range(10):
                if not job or job.get("status") != "PROCESSING":
                    break
                await asyncio.sleep(.1)
                job = await repository.get_message_extraction(case_id, message["message_id"])
            pending = pending or bool(job and job.get("status") in {"PENDING", "PROCESSING", "FAILED"})
        except Exception:
            logger.exception("Could not settle source-message extraction before Copilot invocation")
            pending = True
    return pending


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
        candidates.append((
            "transfer.actual.amount", "실제 이체 금액",
            {"amount_krw": actual_amount, "currency": "KRW", "direction": "OUT", "amount_role": "TRANSFER_OUT"},
            f"{actual_amount:,}원 이체",
        ))
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
    already_handled = {item["target_field"] for item in queued if item.get("status") in {"PENDING", "ASKED", "SKIPPED"}}
    fields = [
        ("victim_transfer_status", "상대방의 요구대로 실제로 송금하거나 이체하셨나요?", "실제 송금 여부를 먼저 확인해야 합니다.", "피해 발생 여부를 확인하기 위한 질문입니다.", "P0", ["송금하지 않았어요", "송금했어요", "잘 모르겠어요"]),
        ("remote_control_app", "원격 제어 또는 화면 공유 앱을 실제로 설치하셨나요?", "실제 앱 설치 여부를 확인해야 합니다.", "기기에 앱이 설치됐는지 확인해 추가 피해 가능성을 살펴보기 위한 질문입니다.", "P0", ["설치했어요", "설치하지 않았어요", "잘 모르겠어요"]),
        ("personal_information_exposure", "주민등록번호나 계좌번호 등 개인정보를 제공하셨나요?", "개인정보 노출 여부는 추가 보호 조치 판단에 필요합니다.", "개인정보 보호 조치가 필요한지 확인하는 질문입니다.", "P0", ["제공하지 않았어요", "일부 제공했어요", "제공했어요", "잘 모르겠어요"]),
        ("authentication_information_exposure", "인증번호, 비밀번호 또는 OTP를 제공하셨나요?", "인증정보 노출 여부는 계정 보호 판단에 필요합니다.", "계정과 금융정보를 보호하기 위해 인증정보 노출 여부를 확인합니다.", "P0", ["제공하지 않았어요", "제공했어요", "잘 모르겠어요"]),
        ("claimed_organization", "상대방은 어느 기관이나 회사 소속이라고 말했나요?", "상대방이 주장한 소속을 확인해야 합니다.", "상대방의 주장을 공식 채널에서 확인하기 위한 질문입니다.", "P1", []),
    ]
    return [
        PublicQuestionCandidateResponse(
            question_id=f"candidate-{target_field}", target_field=target_field,
            question_text=text, reason=reason, customer_explanation=customer_explanation,
            priority=priority, options=options, answer_mode="CHOICE_OR_TEXT", allow_free_text=True,
        )
        for target_field, text, reason, customer_explanation, priority, options in fields
        if target_field not in already_handled
    ]


def build_transaction_amount_conflict_candidate(
    conflict: dict,
) -> PublicQuestionCandidateResponse:
    """Build a clarification question; it never changes the transaction ledger."""
    reported = int(conflict["reported_amount_krw"])
    existing = ", ".join(f"{int(amount):,}원" for amount in conflict["existing_amounts_krw"])
    same_amount = conflict.get("conflict_kind") == "SAME_AMOUNT_AMBIGUOUS"
    question_text = (
        f"기존에 {reported:,}원 송금 기록이 있습니다. 이번 말씀은 기존 송금을 다시 말한 건가요, "
        f"아니면 같은 금액 {reported:,}원을 추가로 송금한 건가요?"
        if same_amount else
        f"앞서 {existing} 송금 기록이 확인됐습니다. 이번에 말씀하신 {reported:,}원은 "
        "별도로 추가 송금한 금액인가요, 아니면 금액을 잘못 말씀하신 건가요?"
    )
    options = (
        ["기존 송금을 다시 말했어요", "같은 금액을 추가로 송금했어요", "잘 모르겠어요"]
        if same_amount else
        ["별도로 추가 송금했어요", "금액을 잘못 말했어요", "잘 모르겠어요"]
    )
    return PublicQuestionCandidateResponse(
        question_id="candidate-transaction-amount-conflict",
        target_field=TRANSACTION_AMOUNT_CONFLICT_TARGET,
        question_text=question_text,
        reason=(
            "기존 송금과 같은 금액이어서 기존 거래 재진술인지 추가 송금인지 확인이 필요합니다."
            if same_amount else
            "기존 송금 기록과 고객 발화의 금액이 달라 추가 확인이 필요합니다."
        ),
        customer_explanation="기존 기록을 보존한 채 추가 송금인지 금액 착오인지 확인합니다.",
        priority="P0",
        options=options,
        answer_mode="CHOICE_OR_TEXT",
        allow_free_text=True,
    )


def build_question_recommendation_context(facts: list[dict], questions: list[dict], case: dict | None = None) -> dict:
    """답변 수신과 사실 확정을 분리하되 질문 이력이 있는 항목은 다시 묻지 않는다."""
    valid_fields = {
        "transfer_status", "transfer_purpose", "claimed_organization", "incident_claim",
        "personal_information_exposure", "authentication_information_exposure",
        "remote_control_app",
    }
    confirmed_fields = [normalize_target_field(item["field"]) for item in facts if item.get("status") == "CONFIRMED" and normalize_target_field(item.get("field", "")) in valid_fields]
    return {
        "confirmed_fields": list(dict.fromkeys(confirmed_fields)),
        "pending_question_fields": [normalize_target_field(item["target_field"]) for item in questions if item.get("status") in {"PENDING", "ASKED"} and normalize_target_field(item.get("target_field", "")) in valid_fields],
        "answered_question_fields": [normalize_target_field(item["target_field"]) for item in questions if item.get("status") == "ANSWERED" and normalize_target_field(item.get("target_field", "")) in valid_fields],
        "answered_question_ids": [item["question_id"] for item in questions if item.get("status") == "ANSWERED"],
    }


def question_fields_answered_by_messages(messages: list[dict]) -> set[str]:
    """Suppress a basic question only when a human message contains a clear answer.

    Keyword overlap is not enough: e.g. ``송금했는지 모르겠어요`` contains the
    same verb as a completed transfer, but is explicitly unresolved. Reuse the
    case-support answer parser so this guard follows the same conservative
    polarity/uncertainty rules as the typed question policy.
    """
    answered: set[str] = set()
    answerable_targets = {
        "transfer_status": TargetField.TRANSFER_STATUS,
        "remote_control_app": TargetField.REMOTE_CONTROL_APP,
        "authentication_information_exposure": TargetField.AUTHENTICATION_INFORMATION_EXPOSURE,
        "personal_information_exposure": TargetField.PERSONAL_INFORMATION_EXPOSURE,
    }
    target_markers = {
        "transfer_status": ("송금", "이체", "입금", "돈을보"),
        "remote_control_app": ("원격제어", "원격앱", "애니데스크", "팀뷰어", "화면공유", "원격지원"),
        "authentication_information_exposure": ("otp", "인증번호", "인증정보", "비밀번호", "보안코드"),
        "personal_information_exposure": ("주민등록번호", "계좌번호", "개인정보", "민감정보"),
    }
    for message in messages:
        if message.get("actor_type") not in {"CUSTOMER", "BANK_STAFF"} or message.get("message_kind", "CHAT") != "CHAT":
            continue
        text = re.sub(r"\s+", "", str(message.get("content", ""))).casefold()
        for field, target in answerable_targets.items():
            if not any(term in text for term in target_markers[field]):
                continue
            if CaseSnapshotAiAdapter.is_clear_customer_answer(field, text):
                answered.add(field)
        if any(term in text for term in ("검찰", "경찰", "금감원", "금융감독원", "은행직원")) and any(term in text for term in ("사칭", "이라고", "라며", "전화")):
            answered.add("claimed_organization")
    return answered


def question_fields_covered_by_case(facts: list[dict], messages: list[dict]) -> set[str]:
    """Return canonical question scopes already covered by facts or human messages.

    This is intentionally limited to baseline question fields.  A contextual AI
    question still has to pass the prompt and text-level duplicate guards, while
    canonical questions are suppressed only by a clear human answer or a
    confirmed, semantically sufficient fact. PROPOSED facts are leads, not
    answers, and a confirmed request to install an app is not proof of install.
    """
    covered = question_fields_answered_by_messages(messages)
    for fact in facts:
        if fact.get("status") != "CONFIRMED" and not fact.get('staff_reported'):
            continue
        try:
            field = normalize_target_field(str(fact.get("field", "")))
        except ValueError:
            continue
        if field not in BASELINE_QUESTION_FIELDS:
            continue
        if field in AUTONOMOUS_P0_QUESTION_FIELDS:
            # Status confirms the recorded statement, not automatically the
            # underlying event. Parse its display value to distinguish an
            # actual answer (including a clear negative) from a demand/request.
            if not CaseSnapshotAiAdapter.is_clear_customer_answer(field, str(fact.get("value", ""))):
                continue
        covered.add(field)
    return covered


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
    follow_up_parents: dict | None = None,
    covered_fields: set[str] | None = None,
) -> list:
    """Keep only safe, novel QUESTION_PLAN drafts and assign non-canonical fields."""
    baseline_fields = BASELINE_QUESTION_FIELDS | {normalize_target_field(item.target_field) for item in baseline}
    baseline_fields.update(covered_fields or set())
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
        try:
            source_field = normalize_target_field(question.target_field)
        except ValueError:
            continue
        if not text or not reason or _unsafe_contextual_question(text):
            continue
        if is_follow_up_target(source_field):
            parent = (follow_up_parents or {}).get(source_field)
            if parent is None or source_field in covered_fields:
                continue
            try:
                normalized = validate_follow_up_question(question.model_dump(mode="python"), parent)
            except ValueError:
                continue
            if any(_same_question(text, item.question_text) for item in [*covered, *accepted]):
                continue
            if any(canonical_question_scope(item.target_field) == canonical_question_scope(source_field)
                   for item in [*drafts, *accepted]):
                continue
            accepted.append(question.model_copy(update={
                **normalized.model_dump(exclude={"source", "allow_multi_select"}), "question_id": source_field,
            }))
            if len(accepted) == 3:
                break
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
    candidates: list[PublicQuestionCandidateResponse], questions: list[dict],
    covered_fields: set[str] | None = None,
) -> list[PublicQuestionCandidateResponse]:
    handled = [item for item in questions if item.get("status") in {"PENDING", "ASKED", "ANSWERED"}]
    active_fields = {normalize_target_field(str(item.get("target_field", ""))) for item in handled
                     if item.get("status") in {"PENDING", "ASKED"}}
    handled_texts = {normalize_question_text(str(item.get("question_text", ""))) for item in handled}
    covered_fields = covered_fields or set()
    return [
        candidate for candidate in candidates
        if normalize_target_field(candidate.target_field) not in active_fields
        and normalize_target_field(candidate.target_field) not in covered_fields
        and normalize_question_text(candidate.question_text) not in handled_texts
        and not any(similar_question(candidate.question_text, str(q.get("question_text", ""))) for q in handled
                    if not q.get("target_field") or normalize_target_field(q["target_field"]) == normalize_target_field(candidate.target_field))
    ]


def to_public_case_support_snapshot(
    case_id: str, payload: dict, *, available: bool, source_revision: int | None = None,
    projection_revision: int | None = None, projection_status: str = "UNCACHED",
    case: dict | None = None, questions: list[dict] | None = None,
    verifications: list[dict] | None = None, actions: list[dict] | None = None,
    tasks: list[dict] | None = None, include_right_panel: bool = False,
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
        right_panel=PublicRightPanelProjection.model_validate(build_right_panel_projection(
            case=case, case_context=context, questions=questions, verifications=verifications,
            actions=actions, tasks=tasks, source_revision=source_revision,
        )) if include_right_panel and case is not None else None,
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


async def _read_case_support_source(case_id: str, *, attempts: int = 3) -> tuple[int, dict, list[dict], list[dict], list[dict], list[dict], list[dict]]:
    """Panel, question planning and Copilot share the same source assembly."""
    try:
        state = await read_operational_state(repository, case_context_v2_repository(), case_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."}) from exc
    return state.revision, state.case, state.facts, state.questions, state.verifications, state.actions, state.tasks


def _case_support_ai_input(case_id: str, case: dict, facts: list[dict], questions: list[dict], verifications: list[dict], actions: list[dict]) -> dict:
    actions = actions_for_ai(actions)
    return {
        "case_id": case_id, "source_revision": max(1, int(case.get("context_revision", 1))),
        "diagnosis": case.get("diagnosis"),
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
            "source_kind": item.get("source_kind"), "staff_attested": bool(item.get("staff_attested")),
            "staff_reported": bool(item.get("staff_reported")),
            "evidence_refs": [str(ref.get("id")) for ref in item.get("evidence_refs", [])
                              if isinstance(ref, dict) and ref.get("id")][:20],
        } for item in facts],
        "verifications": [{
            "verification_task_id": item["verification_task_id"], "target": item.get("target", ""),
            "claim": item.get("claim", ""), "status": item.get("status", "PENDING"),
            "result_summary": item.get("result_summary"), "evidence_url": item.get("evidence_url"),
            "rag_source": item.get("rag_source"),
        } for item in verifications],
        "actions": [{
            "action_id": item["action_id"], "action_type": item.get("action_type", "OTHER"),
            "status": item.get("status", "PENDING"), "note": item.get("note", ""),
        } for item in actions],
    }


async def get_case_support_snapshot(case_id: str, *, include_right_panel: bool = False) -> PublicCaseSupportSnapshotResponse:
    # Mock/in-memory repositories keep the original uncached path. Production
    # MySQL uses durable revision + DB lease so multiple workers share one result.
    if isinstance(repository, MySqlCaseRepository):
        projections = ContextProjectionRepository(repository)
        for _ in range(3):
            try:
                revision, case, facts, questions, verifications, actions, tasks = await _read_case_support_source(case_id)
            except RuntimeError:
                continue
            claim = await projections.claim(case_id, revision)
            if claim.outcome == "STALE":
                continue
            if claim.outcome == "CACHED":
                return to_public_case_support_snapshot(case_id, claim.last_success_payload or {}, available=True,
                    source_revision=revision, projection_revision=claim.last_success_revision, projection_status="CURRENT",
                    case=case, questions=questions, verifications=verifications, actions=actions, tasks=tasks,
                    include_right_panel=include_right_panel)
            if claim.outcome == "IN_PROGRESS":
                if claim.last_success_payload is not None:
                    cached = {**claim.last_success_payload, "warnings": [
                        *claim.last_success_payload.get("warnings", []), "최신 변경사항을 반영 중이며 직전 정상 사건 맥락을 표시합니다.",
                    ]}
                    return to_public_case_support_snapshot(case_id, cached, available=True,
                        source_revision=revision, projection_revision=claim.last_success_revision, projection_status="UPDATING",
                        case=case, questions=questions, verifications=verifications, actions=actions, tasks=tasks,
                        include_right_panel=include_right_panel)
                return to_public_case_support_snapshot(case_id, {}, available=False,
                    source_revision=revision, projection_status="UPDATING", case=case,
                    questions=questions, verifications=verifications, actions=actions, tasks=tasks,
                    include_right_panel=include_right_panel)
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
                        source_revision=revision, projection_revision=claim.last_success_revision, projection_status="STALE",
                        case=case, questions=questions, verifications=verifications, actions=actions, tasks=tasks,
                        include_right_panel=include_right_panel)
                return to_public_case_support_snapshot(case_id, {}, available=False,
                    source_revision=revision, projection_status="FAILED", case=case,
                    questions=questions, verifications=verifications, actions=actions, tasks=tasks,
                    include_right_panel=include_right_panel)
            if await projections.complete(case_id, revision, claim.lease_token or "", payload):
                return to_public_case_support_snapshot(case_id, payload, available=True,
                    source_revision=revision, projection_revision=revision, projection_status="CURRENT",
                    case=case, questions=questions, verifications=verifications, actions=actions, tasks=tasks,
                    include_right_panel=include_right_panel)
            # Data changed during generation; never publish this obsolete result.
        return PublicCaseSupportSnapshotResponse(case_id=case_id, available=False,
            warnings=["사건 정보가 연속으로 변경되어 최신 맥락 반영을 다시 시도합니다."], projection_status="UPDATING")

    case = await repository.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."})
    questions = await repository.list_customer_questions(case_id)
    verifications = await repository.list_verifications(case_id)
    actions = await repository.list_actions(case_id)
    task_rows: list[dict] = []
    try:
        resources = await case_context_v2_repository().list_resources(case_id)
        facts, actions = merge_support_records(resources, [], actions)
        task_rows = [task.model_dump(mode="json") if hasattr(task, "model_dump") else dict(task)
                     for task in getattr(resources, "tasks", [])]
        payload = await service.ai_client.build_case_support_snapshot(
            _case_support_ai_input(case_id, case, facts, questions, verifications, actions)
        )
        return to_public_case_support_snapshot(case_id, payload, available=True,
            source_revision=int(case.get("context_revision", 1)), case=case, questions=questions,
            verifications=verifications, actions=actions, tasks=task_rows,
            include_right_panel=include_right_panel)
    except AiServiceError as exc:
        return to_public_case_support_snapshot(case_id, {}, available=False,
            source_revision=int(case.get("context_revision", 1)), projection_status="FAILED",
            case=case, questions=questions, verifications=verifications, actions=actions,
            tasks=task_rows, include_right_panel=include_right_panel)


@app.get("/api/cases/{case_id}/ai/case-support", response_model=PublicCaseSupportSnapshotResponse)
async def read_case_support_snapshot(case_id: str, actor_user_id: str | None = None) -> PublicCaseSupportSnapshotResponse:
    if actor_user_id:
        await require_context_v2_member(case_id, actor_user_id, access="READ")
    return await get_case_support_snapshot(case_id, include_right_panel=bool(actor_user_id))


@app.get("/api/cases/{case_id}/customer-question-candidates", response_model=list[PublicQuestionCandidateResponse])
async def list_customer_question_candidates(case_id: str) -> list[PublicQuestionCandidateResponse]:
    case = await repository.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."})
    queued = await repository.list_customer_questions(case_id)
    snapshot = await get_case_support_snapshot(case_id)
    # AI 장애 시에도 기존 deterministic 후보로 고객 확인 흐름을 멈추지 않는다.
    fallback_candidates = build_customer_question_candidates(case, queued)
    candidates = list(snapshot.recommended_questions) if snapshot.available else []
    represented = {normalize_target_field(item.target_field) for item in candidates}
    candidates.extend(item for item in fallback_candidates if normalize_target_field(item.target_field) not in represented)
    # A customer may accidentally report a different amount after a transfer
    # has already been recorded.  Keep the recorded transaction unchanged and
    # surface one explicit clarification question instead of guessing.
    messages = await repository.list_messages(case_id)
    transactions = await repository.list_transactions(case_id)
    if not isinstance(messages, list):
        messages = []
    if not isinstance(transactions, list):
        transactions = []
    conflicts = [
        conflict for message in messages
        if (conflict := detect_transfer_amount_conflict(message, transactions)) is not None
    ]
    if conflicts and TRANSACTION_AMOUNT_CONFLICT_TARGET not in represented:
        candidates.append(build_transaction_amount_conflict_candidate(conflicts[-1]))
    # 최신 typed 상태를 B의 공통 정책에 연결한다. General에서 충분성을 재판단하지 않는다.
    resources = await case_context_v2_repository().list_resources(case_id)
    facts, _ = merge_support_records(resources, [], [])
    adapter = CaseSnapshotAiAdapter()
    eligibility = adapter.question_eligibilities(adapter.adapt(
        _case_support_ai_input(case_id, case, facts, queued, [], [])
    ))
    covered_fields = question_fields_covered_by_case(facts, messages)
    filtered = [candidate for candidate in exclude_handled_question_candidates(candidates, queued, covered_fields)
                if normalize_target_field(candidate.target_field) in MANUAL_BASIC_QUESTION_FIELDS
                and ((policy := eligibility.get(normalize_target_field(candidate.target_field))) is None
                     or policy.allow_basic_question)]
    # 레거시 저장 target은 alias로 합치지 않고, 사칭 대상 질문일 때만 새 기본 후보와 비교한다.
    if any(
        normalize_target_field(str(q.get("target_field", ""))) == "impersonated_institution"
        and any(word in str(q.get("question_text", "")) for word in ("기관", "은행", "회사", "소속", "사칭"))
        and any(word in str(q.get("question_text", "")) for word in ("어느", "어떤", "어디", "말했", "주장", "사칭"))
        for q in queued if q.get("status") in {"PENDING", "ASKED", "ANSWERED"}
    ):
        filtered = [item for item in filtered if item.target_field != "claimed_organization"]
    stage_order = {
        TRANSACTION_AMOUNT_CONFLICT_TARGET: 0,
        "transfer_status": 1, "authentication_information_exposure": 1,
        "personal_information_exposure": 1, "remote_control_app": 1,
        "transfer_purpose": 2, "claimed_organization": 3, "incident_claim": 3,
    }
    target_order = {
        TRANSACTION_AMOUNT_CONFLICT_TARGET: 0,
        "transfer_status": 0, "authentication_information_exposure": 1,
        "personal_information_exposure": 2, "remote_control_app": 3,
        "transfer_purpose": 4, "claimed_organization": 5, "incident_claim": 6,
    }
    return sorted(filtered, key=lambda item: (
        stage_order.get(normalize_target_field(item.target_field), 4),
        {"P0": 0, "P1": 1, "P2": 2}[item.priority],
        target_order.get(normalize_target_field(item.target_field), 99),
    ))


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
        question_payloads = [item.model_dump() for item in request.questions]
        if any(is_follow_up_target(item.target_field) for item in request.questions):
            state = await _live_question_state(case_id, await repository.get(case_id))
            parents = CaseSnapshotAiAdapter.follow_up_parents(state)
            for index, item in enumerate(request.questions):
                if is_follow_up_target(item.target_field):
                    parent = parents.get(item.target_field)
                    if parent is None:
                        raise HTTPException(status_code=409, detail={"code": "FOLLOW_UP_NOT_ALLOWED"})
                    normalized = validate_follow_up_question(item.model_dump(mode="python"), parent)
                    question_payloads[index] = normalized.model_dump(exclude={"source"})
        items = await repository.queue_customer_questions(
            case_id, question_payloads, request.requested_by
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_FOLLOW_UP", "message": str(exc)}) from exc
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
    resources = await case_context_v2_repository().list_resources(case_id)
    facts, _ = merge_support_records(resources, [], [])
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
        target_field = TargetField(canonical_question_scope(normalize_target_field(str(question["target_field"]))))
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


async def _persist_transaction_amount_conflict(case_id: str, message: dict) -> dict | None:
    """Record a proposed conflict without mutating the confirmed transaction ledger."""
    try:
        transactions = await repository.list_transactions(case_id)
        if not isinstance(transactions, list):
            transactions = []
        conflict = detect_transfer_amount_conflict(message, transactions)
        if conflict is None:
            return None
        await case_context_v2_repository().create_fact(case_id, {
            "client_request_id": conflict_client_request_id(case_id, conflict),
            "semantic_key": "transfer.amount_conflict",
            "display_label": "송금 금액 불일치",
            "value": {
                "reported_amount_krw": conflict["reported_amount_krw"],
                "existing_amounts_krw": conflict["existing_amounts_krw"],
                "conflict_kind": conflict.get("conflict_kind", "DIFFERENT_AMOUNT"),
                "existing_transaction_ids": conflict["existing_transaction_ids"],
                "reported_message_id": conflict["reported_message_id"],
                "reported_at": conflict.get("reported_at"),
            },
            "display_value": (
                f"기존 {', '.join(f'{int(amount):,}원' for amount in conflict['existing_amounts_krw'])} "
                f"· 새 발화 {int(conflict['reported_amount_krw']):,}원 · "
                f"{'동일 금액 추가 여부 확인 필요' if conflict.get('conflict_kind') == 'SAME_AMOUNT_AMBIGUOUS' else '금액 차이 확인 필요'}"
            ),
            "confidence": None,
            "evidence_refs": [{"type": "MESSAGE", "id": conflict["reported_message_id"]}],
            "visibility": "BANK_INTERNAL",
        }, message.get("actor_user_id") or "transaction-conflict-detector", source_kind="CUSTOMER_STATEMENT")
        return conflict
    except Exception:
        # A proposal is additive.  Message persistence and the authoritative
        # transaction ledger must remain available if Context V2 is unavailable.
        logger.exception("Could not persist transaction amount conflict for %s", case_id)
        return None


def _classify_transaction_conflict_answer(answer_text: str) -> str:
    """Return ADDITIONAL, CORRECTION, or UNCERTAIN; ambiguous text stays open."""
    compact = re.sub(r"\s+", "", answer_text or "").casefold()
    # Negation must be evaluated before the positive ``추가/별도`` cues.
    # Otherwise “추가 송금이 아니에요” could be misclassified as ADDITIONAL.
    negative_additional = (
        bool(re.search(r"추가송금(?:이|은|을|건)?(?:아니|아닌|아닙)", compact))
        or ("추가로보낸게" in compact and "아니" in compact)
        or bool(re.search(r"별도송금(?:이|은|을|건)?(?:아니|아닌|아닙)", compact))
        or ("한번더" in compact and "아니" in compact)
        or ("또보낸게" in compact and "아니" in compact)
    )
    correction = (
        "잘못" in compact or "말실수" in compact or "착각" in compact or "오타" in compact
        or "기존거래" in compact or "다시말" in compact or "같은거래" in compact
        or "중복" in compact or "이미말" in compact
        or negative_additional
    )
    additional = (
        "추가" in compact or "별도" in compact or "두번" in compact or "둘다" in compact
        or "한번더" in compact or "또보냈" in compact or "추가송금" in compact
    )
    if additional and not correction:
        return "ADDITIONAL"
    if correction:
        return "CORRECTION"
    return "UNCERTAIN"


def _confirmed_money_transaction_record(fact: PublicCaseFactV2, transaction_at: str) -> dict | None:
    """Map a confirmed actual-money fact to the internal Case transaction shape."""
    if fact.status != "CONFIRMED" or fact.semantic_key != "transfer.actual.amount":
        return None
    value = fact.value or {}
    raw_amount = value.get("amount_krw")
    if isinstance(raw_amount, bool) or not isinstance(raw_amount, (int, float)):
        return None
    amount = int(raw_amount)
    if amount <= 0 or float(raw_amount) != amount:
        return None
    direction = str(value.get("direction") or "").upper()
    amount_role = str(value.get("amount_role") or "").upper()
    if direction == "OUT" or amount_role == "TRANSFER_OUT":
        transaction_type = "TRANSFER_OUT"
    elif direction == "IN" or amount_role == "REFUND_IN":
        transaction_type = "RETURN_IN"
    else:
        # A requested amount, promised refund, or directionless claim is not
        # an actual ledger event and must remain a Context V2 fact only.
        return None
    record = {
        "transaction_type": transaction_type,
        "transaction_at": transaction_at,
        "amount": amount,
        "memo": f"Context V2 확인 사실 {fact.fact_id}",
        "source": "CONTEXT_FACT_CONFIRMED",
    }
    for target, source in (
        ("account_number", "account_number"),
        ("counterparty_name", "counterparty_name"),
        ("counterparty_account", "counterparty_account"),
        ("bank_name", "bank_name"),
    ):
        if isinstance(value.get(source), str) and value[source].strip():
            record[target] = value[source].strip()
    return record


async def _promote_confirmed_money_fact_to_transaction(case_id: str, fact: PublicCaseFactV2) -> dict | None:
    """Create one internal transaction row for a confirmed actual-money fact."""
    if fact.status != "CONFIRMED":
        return None
    transaction_at = datetime.now(timezone.utc).isoformat()
    messages = await repository.list_messages(case_id)
    if not isinstance(messages, list):
        messages = []
    for evidence in fact.evidence_refs:
        if evidence.type == "MESSAGE":
            message = next((item for item in messages if item.get("message_id") == evidence.id), None)
            if message and message.get("created_at"):
                value = message["created_at"]
                transaction_at = value.isoformat() if hasattr(value, "isoformat") else str(value)
                break
    record = _confirmed_money_transaction_record(fact, transaction_at)
    if record is None:
        return None
    transactions = await repository.list_transactions(case_id)
    if not isinstance(transactions, list):
        transactions = []
    if any(item.get("memo") == record["memo"] for item in transactions):
        return next(item for item in transactions if item.get("memo") == record["memo"])
    return await repository.create_transaction(case_id, record)


async def _resolve_transaction_amount_conflict_after_answer(
    case_id: str, question: dict | None, answer_text: str, actor_user_id: str,
) -> None:
    """Apply only an explicit clarification; otherwise leave the proposal open."""
    if not question or normalize_target_field(str(question.get("target_field", ""))) != TRANSACTION_AMOUNT_CONFLICT_TARGET:
        return
    decision = _classify_transaction_conflict_answer(answer_text)
    if decision == "UNCERTAIN":
        return
    store = case_context_v2_repository()
    resources = await store.list_resources(case_id)
    proposals = [item for item in resources.facts
                 if item.semantic_key == "transfer.amount_conflict" and item.status == "PROPOSED"]
    if not proposals:
        return
    proposal = sorted(proposals, key=lambda item: item.created_at)[-1]
    value = proposal.value
    reported_amount = int(value.get("reported_amount_krw") or 0)
    if reported_amount <= 0:
        return
    if decision == "ADDITIONAL":
        transactions = await repository.list_transactions(case_id)
        if not isinstance(transactions, list):
            transactions = []
        memo = f"고객 재확인: 기존 거래와 별도 송금 ({proposal.fact_id})"
        if not any(item.get("memo") == memo for item in transactions):
            await repository.create_transaction(case_id, {
                "transaction_type": "TRANSFER_OUT",
                "transaction_at": value.get("reported_at") or datetime.now(timezone.utc).isoformat(),
                "amount": reported_amount,
                "memo": memo,
                "source": "CUSTOMER_CLARIFIED",
            })
        reason = "고객이 기존 거래와 별도 추가 송금으로 확인하여 거래 원장에 별도 기록했습니다."
    else:
        reason = "고객이 새 금액을 잘못 말한 것으로 확인하여 기존 거래를 유지합니다."
    await store.review_fact(case_id, proposal.fact_id, proposal.version, "REJECT", reason, actor_user_id)


@app.post("/api/cases/{case_id}/customer-questions/{question_id}/answer", response_model=PublicCustomerQuestionResponse)
async def answer_customer_question(case_id: str, question_id: str, request: PublicAnswerCustomerQuestionRequest, background_tasks: BackgroundTasks) -> PublicCustomerQuestionResponse:
    await require_case(case_id)
    question = next((item for item in await repository.list_customer_questions(case_id) if item["question_id"] == question_id), None)
    if request.raw_answer is None and question is None:
        raise HTTPException(status_code=404, detail={"code": "CUSTOMER_QUESTION_NOT_FOUND", "message": "답변할 질문을 찾을 수 없습니다."})
    current_version = int((question or {}).get("question_version", 1))
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
        await _resolve_transaction_amount_conflict_after_answer(
            case_id, question, answer_text or "", request.actor_user_id,
        )
    except Exception:
        # Never turn a committed customer answer into an API failure.  Leaving
        # the proposal open is safer than guessing or deleting a transaction.
        logger.exception("Could not resolve transaction amount conflict for question %s", question_id)
    try:
        message = next((item for item in await repository.list_messages(case_id) if item.get("message_id") == answered.get("answer_message_id")), None)
        if message:
            await enqueue_context_extraction(message, background_tasks)
            await _persist_transaction_amount_conflict(case_id, message)
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


@app.get("/api/cases/{case_id}/facts", include_in_schema=False)
async def retired_legacy_case_facts(case_id: str) -> None:
    """Fail closed for the retired legacy Fact contract.

    Fact reads and reviews must use ``/context-v2/facts``.  Keeping an
    explicit 410 response gives old clients a deterministic migration signal
    without exposing a second public fact shape.
    """
    raise HTTPException(
        status_code=410,
        detail={"code": "LEGACY_FACTS_DISABLED", "message": "기존 facts API가 종료되었습니다. context-v2/facts를 사용해 주세요."},
    )


@app.post("/api/cases/{case_id}/facts/{fact_id}/confirm", include_in_schema=False)
async def retired_legacy_case_fact_confirmation(case_id: str, fact_id: str) -> None:
    raise HTTPException(
        status_code=410,
        detail={"code": "LEGACY_FACTS_DISABLED", "message": "기존 facts API가 종료되었습니다. context-v2/facts/{fact_id}/review를 사용해 주세요."},
    )


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


@app.api_route("/api/cases/{case_id}/attachments", methods=["POST", "GET"], status_code=410)
async def retired_case_attachments(case_id: str) -> None:
    """Attachments are intentionally out of scope for the demo."""
    raise HTTPException(status_code=410, detail={"code": "ATTACHMENTS_DISABLED", "message": ATTACHMENTS_DISABLED_MESSAGE})


@app.get("/api/internal/cases/{case_id}/attachments", status_code=410)
async def retired_case_attachments_for_ai(case_id: str) -> None:
    raise HTTPException(status_code=410, detail={"code": "ATTACHMENTS_DISABLED", "message": ATTACHMENTS_DISABLED_MESSAGE})


@app.get("/api/cases/{case_id}/attachments/{attachment_id}/content", status_code=410)
async def retired_case_attachment_content(case_id: str, attachment_id: str) -> None:
    raise HTTPException(status_code=410, detail={"code": "ATTACHMENTS_DISABLED", "message": ATTACHMENTS_DISABLED_MESSAGE})


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
        raise HTTPException(status_code=422, detail={"code": str(exc), "message": ATTACHMENTS_DISABLED_MESSAGE}) from exc
    try:
        await enqueue_context_extraction(record, background_tasks)
    except Exception:
        logger.exception("Message was committed but its context extraction could not be queued")
    await _persist_transaction_amount_conflict(case_id, record)
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
    return [PublicCaseMemberResponse.model_validate({key: value for key, value in item.items() if key != "role"}) for item in await repository.list_members(case_id)]


@app.post("/api/cases/{case_id}/members", response_model=PublicCaseMemberResponse, status_code=201)
async def upsert_case_member(case_id: str, request: PublicCaseMemberUpsertRequest) -> PublicCaseMemberResponse:
    await require_case(case_id)
    try:
        stored = await repository.upsert_member(case_id, request.model_dump())
        return PublicCaseMemberResponse.model_validate({key: value for key, value in stored.items() if key != "role"})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."}) from exc


@app.delete("/api/cases/{case_id}/members/{user_id}", status_code=204)
async def remove_case_member(case_id: str, user_id: str) -> None:
    if user_id == CURRENT_BANK_USER_ID:
        raise HTTPException(status_code=409, detail={"code": "CURRENT_USER_CANNOT_BE_REMOVED", "message": "현재 사용자는 케이스 담당자에서 제거할 수 없습니다."})
    try:
        await require_case(case_id)
        await repository.remove_member(case_id, user_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "CASE_MEMBER_NOT_FOUND", "message": "케이스 담당자를 찾을 수 없습니다."}) from exc
    except ValueError as exc:
        if str(exc) == "CASE_OWNER_CANNOT_BE_REMOVED":
            raise HTTPException(status_code=409, detail={"code": "CASE_OWNER_CANNOT_BE_REMOVED", "message": "사건 총괄은 새 총괄을 지정한 후 제거할 수 있습니다."}) from exc
        raise


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


async def _live_question_state(case_id: str, case: dict):
    resources = await case_context_v2_repository().list_resources(case_id)
    facts, _ = merge_support_records(resources, [], [])
    questions = await repository.list_customer_questions(case_id)
    return CaseSnapshotAiAdapter().adapt(_case_support_ai_input(case_id, case, facts, questions, [], []))


@app.post("/api/cases/{case_id}/ai/work-cards", response_model=CaseWorkCardOutput)
async def generate_case_work_card(case_id: str, request: PublicWorkCardGenerateRequest) -> CaseWorkCardOutput:
    try:
        state = await read_operational_state(repository, case_context_v2_repository(), case_id)
    except KeyError:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."})
    case, verifications, actions, messages, resources, facts = (state.case, state.verifications,
        state.actions, state.messages, state.resources, state.facts)
    try:
        for draft in request.question_drafts:
            normalize_target_field(draft.target_field)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_FOLLOW_UP", "message": str(exc)}) from exc
    support = await get_case_support_snapshot(case_id)
    staff = await read_staff_context_records(case_id)
    previous_questions = state.questions
    candidates = await list_customer_question_candidates(case_id)
    retrieved = retrieve_context(case_id, " ".join(q.question_text for q in candidates[:6]) or "기관 확인 담당자 다음 업무", collect_records(
        case_id, messages=messages, questions=previous_questions, facts=facts, verifications=verifications, staff=staff,
    ))
    try:
        live_state = CaseSnapshotAiAdapter().adapt(_case_support_ai_input(case_id, case, facts, previous_questions, [], [])) if request.card_type == "QUESTION_PLAN" else None
        known_facts = [
            f"{item.get('field')}: {item.get('value')} ({item.get('status')})" for item in facts[:30]
        ]
        if request.card_type == "QUESTION_PLAN":
            case_context = support.case_context.model_dump(mode="python") if support.case_context else {}
            covered_question_fields = question_fields_covered_by_case(facts, messages)
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
            covered_state = [
                f"이미 확인된 질문 범위: {field}"
                for field in sorted(covered_question_fields)
            ]
            known_facts = (known_facts[:15] + contextual_facts + covered_state + question_state + draft_state)[:30]
        payload = await service.ai_client.generate_work_card({
            "case_id": case_id,
            "card_type": request.card_type,
            "staff_context": staff_context(staff),
            "retrieved_context": retrieved,
            "case_summary": state.summary,
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
                f"{item['title']}: {item['description']}"
                for item in state.tasks if item['status'] not in {"COMPLETED", "CANCELLED"}
            ][:20],
            "attachment_summaries": [],
            "unresolved_items": [f"{item.priority}: {item.description}" for item in support.unresolved_items[:20]],
            "pending_verifications": [f"{item.get('target')}: {item.get('claim')}" for item in verifications if item.get("status") != "COMPLETED"][:20],
            # Public 후보에는 고객 UI 전용 allow_multi_select가 있지만, AI 내부 WorkCardQuestion
            # 계약에는 없다. 내부 계약에 정의된 필드만 전달해 추천 요청 자체가 422가 되지 않게 한다.
            "question_candidates": [item.model_dump(mode="python", exclude={"allow_multi_select"}) for item in candidates[:10]],
            "question_state": live_state.model_dump(mode="json") if live_state else None,
        })
        card = CaseWorkCardOutput.model_validate(payload)
        if request.card_type == "QUESTION_PLAN":
            # Provider 대기 중 상태가 바뀌었으면 최신 B policy로 초안을 다시 걸러낸다.
            live_state = await _live_question_state(case_id, await repository.get(case_id))
            card.questions = filter_contextual_questions(
                card.questions, candidates, [q.model_dump() for q in live_state.questions], request.question_drafts,
                CaseSnapshotAiAdapter.follow_up_parents(live_state),
                question_fields_covered_by_case(facts, messages),
            )
        return card
    except AiServiceQuotaError as exc:
        raise HTTPException(status_code=429, detail={"code": "OPENAI_QUOTA_EXHAUSTED", "message": str(exc)}) from exc
    except AiServiceAuthenticationError as exc:
        raise HTTPException(status_code=401, detail={"code": "OPENAI_AUTHENTICATION_FAILED", "message": str(exc)}) from exc
    except AiServiceError as exc:
        raise HTTPException(status_code=503, detail={
            "code": exc.code or "AI_WORK_CARD_FAILED",
            "message": str(exc),
            "retryable": exc.retryable,
        }) from exc


@app.post("/api/cases/{case_id}/ai/invocations", response_model=PublicAiInvocationResponse, status_code=201)
async def invoke_case_copilot(case_id: str, request: PublicAiInvocationRequest) -> PublicAiInvocationResponse:
    await require_context_v2_member(case_id, request.requester_user_id, access="WRITE")
    async with CopilotJobs(repository).serialize(case_id):
        return await _invoke_case_copilot(case_id, request)


async def _invoke_case_copilot(case_id: str, request: PublicAiInvocationRequest) -> PublicAiInvocationResponse:
    if request.client_request_id:
        existing = await repository.find_message_by_client_request_id(case_id, request.client_request_id)
        if isinstance(existing, dict):
            if existing.get('actor_type') != 'BANK_AGENT' or (existing.get('visibility') == 'AI_PRIVATE' and existing.get('private_owner_user_id') != request.requester_user_id):
                raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_CONFLICT", "message": "다른 요청에서 사용한 요청 번호입니다."})
            metadata = existing.get("ai_metadata") or {}
            return PublicAiInvocationResponse(invocation_id=existing["message_id"], message_id=existing["message_id"],
                case_id=case_id, channel=existing["channel"], content=existing["content"],
                model_mode=metadata.get("model_mode", "PERSISTED"), created_at=existing["created_at"],
                recommended_actions=metadata.get("recommended_actions", []), source_revision=metadata.get("source_revision"),
                mutation_results=metadata.get("mutation_results", []))
    case = await repository.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."})
    verifications = await repository.list_verifications(case_id)
    actions = await repository.list_actions(case_id)
    all_messages = await repository.list_messages(case_id)
    extraction_pending = await settle_copilot_source_extractions(
        case_id, request.requester_user_id, request.source_message_ids, all_messages,
    )
    state = await read_operational_state(repository, case_context_v2_repository(), case_id, await context_display_repository(case_id))
    case, resources, facts, actions = state.case, state.resources, state.facts, state.actions
    all_messages, verifications = state.messages, state.verifications
    members = await repository.list_members(case_id)
    requester_member = next(
        (item for item in members if item.get("user_id") == request.requester_user_id and item.get("status") == "ACTIVE"),
        None,
    )
    primary_assignee = next(
        (item.get("display_name") for item in members if case_role_for_member(item) == "CASE_OWNER"),
        None,
    )
    member_role_labels = {
        "CASE_OWNER": "메인 담당자",
        "CHAT_OPERATOR": "상담 담당자",
        "REVIEWER": "검토자",
        "VIEWER": "열람자",
    }
    unresolved = [item.get("claim", "추가 확인 항목") for item in verifications if item.get("status") != "COMPLETED"]
    staff = workspace_records(case_id, resources)
    questions = await repository.list_customer_questions(case_id)
    retrieved = retrieve_context(case_id, request.prompt, collect_records(
        case_id, messages=all_messages, questions=questions, facts=facts, verifications=verifications, staff=staff,
    ))
    try:
        ai_payload = {
            "case_id": case_id,
            "prompt": request.prompt,
            "requester_user_id": request.requester_user_id,
            "requester_display_name": request.requester_display_name,
            "requester_role": requester_member.get("role") if requester_member else "BANK_STAFF",
            "case_summary": state.summary,
            "workflow_status": case.get("status", "TRIAGE"),
            "fraud_type": case.get("fraud_type"),
            "transfer_status": case.get("victim_transfer_status"),
            "primary_assignee": primary_assignee,
            "participants": [
                f"{item.get('display_name', '이름 미상')} ({member_role_labels.get(case_role_for_member(item), case_role_for_member(item) or '역할 미상')})"
                for item in members
            ][:30],
            "staff_context": [*staff_context(staff), *(["최근 담당자 메시지의 구조화 저장이 진행 중입니다. 해당 메시지는 담당자 확인 보고로 귀속해 대화에 답하되, 저장 완료를 주장하지 마세요."] if extraction_pending else [])],
            "retrieved_context": retrieved,
            "known_facts": [f"{item.get('field')}: {item.get('value')} ({item.get('status')})" for item in facts[:30]],
            "recent_conversation": [
                f"{item.get('actor_display_name', item.get('actor_type', '작성자'))} "
                f"({item.get('actor_role') or item.get('actor_type', '역할 미상')}): {item.get('content', '')[:500]}"
                for item in all_messages[-30:]
                if item.get("message_kind") not in {"AI_RESPONSE", "REPORT_CARD"}
                and item.get("actor_type") not in {"BANK_AGENT", "CUSTOMER_AGENT"}
                and (item.get("channel") in {"TEAM", "CUSTOMER"}
                or (request.channel != "TEAM" and item.get("channel") == "AI_INTERNAL" and item.get("private_owner_user_id") == request.requester_user_id))
            ][-20:],
            "pending_actions": [
                f"{item.get('action_type')}: {item.get('note') or '상세 내용 없음'} ({item.get('status', 'REQUESTED')})"
                for item in actions_for_ai(actions) if item.get("status") not in {"COMPLETED", "CANCELLED"}
            ][:20],
            "attachment_summaries": [],
            "unresolved_verifications": unresolved[:10],
            "assistant_mode": "BANK_INTERNAL",
            "source_context": bank_source_context(case_id, resources, questions=questions,
                verifications=verifications, messages=[item for item in all_messages if item.get("visibility") in {"CUSTOMER", "BANK_INTERNAL"}],
                diagnosis=case.get("diagnosis") or {}).model_dump(mode="json"),
            "customer_progress": progress_ai_context(build_customer_progress(actions)),
            "response_style": request.response_style,
            "source_revision": state.revision,
            "case_state": state.payload(),
            "dialogue_history": [{key: item.get(key) for key in (
                "message_id", "case_id", "actor_type", "actor_user_id", "actor_display_name", "actor_role",
                "channel", "audience", "content", "created_at")}
                for item in all_messages if item.get("channel") == "TEAM"
                and item.get("visibility") == "BANK_INTERNAL" and item.get("message_kind") in {"CHAT", "AI_RESPONSE"}][-20:],
            "allow_task_planning": not extraction_pending,
        }
        ai_reply = await service.ai_client.generate_case_copilot_reply(ai_payload)
        mutation_results, task_buttons = [], []
        if ai_reply.get("task_intents") and not extraction_pending:
            latest = await repository.get(case_id)
            if int(latest.get("context_revision", 1)) != state.revision:
                raise HTTPException(status_code=409, detail={"code": "AI_GENERATION_STALE", "message": "사건 정보가 변경되어 최신 상태에서 다시 안내합니다."})
            allow_cancel = False
            try:
                await require_context_v2_member(case_id, request.requester_user_id, access="REVIEW")
                allow_cancel = True
            except HTTPException as permission_error:
                if permission_error.status_code != 403:
                    raise
            mutation_results, task_buttons = await apply_task_intents(case_context_v2_repository(), state,
                ai_reply["task_intents"], request.requester_user_id, request.source_message_ids, allow_cancel=allow_cancel)
            state = await read_operational_state(repository, case_context_v2_repository(), case_id, await context_display_repository(case_id))
            ai_payload.update(case_state=state.payload(), case_summary=state.summary, source_revision=state.revision,
                mutation_results=mutation_results, allow_task_planning=False,
                known_facts=[f"{f.get('field')}: {f.get('value')} ({f.get('status')})" for f in state.facts[:30]],
                pending_actions=[f"{t['title']}: {t['description']}" for t in state.tasks if t['status'] not in {'COMPLETED', 'CANCELLED'}][:20],
                source_context=bank_source_context(case_id, state.resources, questions=state.questions,
                    verifications=state.verifications, messages=[m for m in state.messages if m.get("visibility") in {"CUSTOMER", "BANK_INTERNAL"}],
                    diagnosis=state.case.get("diagnosis") or {}).model_dump(mode="json"))
            try:
                ai_reply = await service.ai_client.generate_case_copilot_reply(ai_payload)
            except AiServiceError:
                titles = [r["title"] for r in mutation_results if r["status"] == "APPLIED"]
                ai_reply = {"content": ("업무 기록에 반영했습니다: " + ", ".join(titles) + ". " if titles else "새로 반영된 업무는 없습니다. ")
                    + "추가 AI 안내 생성에 실패했습니다. 저장된 업무는 아래 기능에서 확인할 수 있습니다.",
                    "model_mode": "WORKFLOW_RESULT", "recommended_actions": task_buttons}
            if task_buttons:
                ai_reply["recommended_actions"] = [*task_buttons, *ai_reply.get("recommended_actions", [])]
    except AiServiceQuotaError as exc:
        raise HTTPException(status_code=429, detail={"code": "OPENAI_QUOTA_EXHAUSTED", "message": str(exc)}) from exc
    except AiServiceAuthenticationError as exc:
        raise HTTPException(status_code=401, detail={"code": "OPENAI_AUTHENTICATION_FAILED", "message": str(exc)}) from exc
    except AiServiceError as exc:
        raise HTTPException(status_code=503, detail={"code": "AI_CASE_COPILOT_FAILED", "message": str(exc)}) from exc
    safe_buttons = []
    seen_action_keys: set[str] = set()
    raw_actions = ai_reply.get('recommended_actions')
    for candidate in (raw_actions[:12] if isinstance(raw_actions, list) else []):
        normalized = normalize_public_recommended_actions([candidate], request.channel)
        if not normalized:
            continue
        action = normalized[0]
        if action.target_type:
            collection, key = ({'TASK': (state.tasks, 'task_id'), 'QUESTION': (state.questions, 'question_id'),
                                'VERIFICATION': (state.verifications, 'verification_task_id')})[action.target_type]
            target = next((r for r in collection if r.get(key) == action.target_id), None)
            if not target or target.get('status') in {'COMPLETED', 'CANCELLED', 'ANSWERED', 'SKIPPED'}:
                continue
            action.expected_version = target.get('version')
        if action.action_key in seen_action_keys:
            continue
        seen_action_keys.add(action.action_key)
        safe_buttons.append(action.model_dump(mode='json'))
    content = ai_reply["content"]
    if request.channel == "TEAM":
        safe_buttons.extend(fallback_case_recommendations(content, request.prompt, state))
    ai_reply['recommended_actions'] = [item.model_dump(mode='json') for item in normalize_public_recommended_actions(safe_buttons, request.channel)]
    is_team_request = request.channel == "TEAM"
    source_guard = ({
        "source_message_ids": request.source_message_ids,
        "channel": request.channel,
        "actor_type": "BANK_STAFF",
        "actor_user_id": request.requester_user_id,
    } if request.source_message_ids else None)
    message = await repository.append_message(case_id, {
        "actor_type": "BANK_AGENT", "actor_user_id": "case-copilot", "actor_display_name": "CaseCopilot",
        "actor_role": "BANK_AGENT", "content": content,
        "channel": "TEAM" if is_team_request else "AI_INTERNAL", "audience": "BANK_INTERNAL",
        "visibility": "BANK_INTERNAL" if is_team_request else "AI_PRIVATE", "message_kind": "AI_RESPONSE", "mentions": ["CaseCopilot"],
        "private_owner_user_id": None if is_team_request else request.requester_user_id, "client_request_id": request.client_request_id, "log_event": True,
        "expected_context_revision": state.revision,
        "ai_metadata": {"recommended_actions": [item.model_dump(mode="json") for item in normalize_public_recommended_actions(ai_reply.get("recommended_actions"), request.channel)],
                        "source_revision": state.revision, "mutation_results": mutation_results, "model_mode": ai_reply["model_mode"]},
    }, source_guard=source_guard)
    if message is None:
        raise HTTPException(status_code=409, detail={
            "code": "AI_GENERATION_STALE", "message": "새 메시지가 저장되어 이전 AI 응답을 폐기했습니다.",
        })
    return PublicAiInvocationResponse(
        invocation_id=f"ai-{uuid4().hex}", message_id=message["message_id"], case_id=case_id,
        channel="TEAM" if is_team_request else "AI_INTERNAL", content=content, model_mode=ai_reply["model_mode"], created_at=message["created_at"],
        recommended_actions=normalize_public_recommended_actions(ai_reply.get("recommended_actions"), request.channel),
        source_revision=state.revision, mutation_results=mutation_results,
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
    asked_questions = [
        item for item in questions
        if item.get("status") == "ASKED" and item.get("question_text")
        and item.get("case_id", case_id) == case_id
    ][:5]
    # Always include visible unanswered cards, even when retrieval cannot match a vague "이 질문".
    service_questions = [
        {
            'source': 'CSR_QUESTION_CARD', 'status': 'ASKED',
            'question_text': str(item.get('question_text', ''))[:1000],
            'customer_explanation': str(item.get('customer_explanation') or '')[:1000],
            'options': [str(option)[:160] for option in (item.get('options') or [])[:10]],
        }
        for item in asked_questions
    ]
    customer_ui_capabilities: list[str] = []
    customer_actions: list[dict[str, str]] = []
    question_action_target = next((item for item in asked_questions if item.get("question_id")), None)
    if question_action_target:
        customer_ui_capabilities.append("OPEN_ACTIVE_QUESTION")
        customer_actions.append({
            "action_key": "OPEN_ACTIVE_QUESTION",
            "target_id": str(question_action_target["question_id"]),
        })
    recovery_active = str(case.get("mode") or "") == "RECOVERY" or str(case.get("victim_transfer_status") or "") == "YES"
    if recovery_active:
        customer_ui_capabilities.append("OPEN_RECOVERY_GUIDE")
        customer_actions.append({"action_key": "OPEN_RECOVERY_GUIDE"})
    retrieved = retrieve_context(case_id, request.prompt, collect_records(
        case_id, messages=all_messages, questions=questions, verifications=verifications, customer=True,
    ), customer=True)
    try:
        ai_reply = await service.ai_client.generate_case_copilot_reply({
            "case_id": case_id,
            "prompt": request.prompt,
            "known_facts": answered,
            "retrieved_context": retrieved,
            "recent_conversation": customer_history,
            "assistant_mode": "CUSTOMER_SUPPORT",
            "customer_progress": progress_ai_context(progress),
            "customer_service_questions": service_questions,
            "customer_ui_capabilities": customer_ui_capabilities,
            "published_verification_results": published_results,
            "attachment_summaries": [],
        })
    except AiServiceQuotaError as exc:
        raise HTTPException(status_code=429, detail={"code": "OPENAI_QUOTA_EXHAUSTED", "message": str(exc)}) from exc
    except AiServiceAuthenticationError as exc:
        raise HTTPException(status_code=401, detail={"code": "OPENAI_AUTHENTICATION_FAILED", "message": str(exc)}) from exc
    except AiServiceError as exc:
        raise HTTPException(status_code=503, detail={"code": "AI_CUSTOMER_SUPPORT_FAILED", "message": str(exc)}) from exc
    source_guard = ({
        "source_message_ids": request.source_message_ids,
        "channel": "CUSTOMER",
        "actor_type": "CUSTOMER",
        "actor_user_id": request.requester_user_id,
    } if request.source_message_ids else None)
    message = await repository.append_message(case_id, {
        "actor_type": "CUSTOMER_AGENT", "actor_user_id": "customer-agent",
        "actor_display_name": "안전 상담 AI", "actor_role": "CUSTOMER_AGENT",
        "content": ai_reply["content"], "channel": "CUSTOMER", "audience": "CUSTOMER",
        "visibility": "CUSTOMER", "message_kind": "AI_RESPONSE", "mentions": [],
        "reply_to_message_id": request.reply_to_message_id, "client_request_id": request.client_request_id,
        "ai_metadata": {"customer_actions": customer_actions},
        "log_event": False,
    }, source_guard=source_guard)
    if message is None:
        raise HTTPException(status_code=409, detail={
            "code": "AI_GENERATION_STALE", "message": "새 메시지가 저장되어 이전 AI 응답을 폐기했습니다.",
        })
    return to_public_message(message)


async def enqueue_copilot_guidance(case_id: str, actor: str, kind: str):
    state = await read_operational_state(repository, case_context_v2_repository(), case_id, await context_display_repository(case_id))
    if state.case.get("analysis_status") in {"IN_PROGRESS", "FAILED", "NO_CASE"} or not state.case.get("diagnosis"):
        return None
    return await CopilotJobs(repository).enqueue(case_id, state.guidance_key(), kind, state.revision, actor)


@app.post("/api/cases/{case_id}/ai/guidance", status_code=202)
async def ensure_copilot_guidance(case_id: str, request: PublicGuidanceRequest):
    await require_context_v2_member(case_id, request.actor_user_id, access="WRITE")
    job = await enqueue_copilot_guidance(case_id, request.actor_user_id, request.reason)
    return {"status": job["status"] if job else "WAITING_ANALYSIS",
            "job_id": job["job_id"] if job else None,
            "message_id": job.get("result_message_id") if job else None}


async def process_copilot_guidance(candidate):
    jobs = CopilotJobs(repository)
    job = await jobs.claim(candidate)
    if not job:
        return
    try:
        async with jobs.serialize(job["case_id"]):
            await require_context_v2_member(job["case_id"], job["actor_user_id"], access="WRITE")
            # If append succeeded but the worker crashed before finish, recover its receipt.
            existing = await repository.find_message_by_client_request_id(job["case_id"], job["job_id"])
            if isinstance(existing, dict):
                await jobs.finish(job, "COMPLETED", existing["message_id"])
                return
            state = await read_operational_state(repository, case_context_v2_repository(), job["case_id"],
                                                 await context_display_repository(job["case_id"]))
            if state.guidance_key() != job["dedupe_key"] or state.case.get("status") == "CLOSED":
                await jobs.finish(job, "SUPERSEDED")
                return
            pending = await repository.list_retryable_message_extractions()
            if any(p.get('case_id') == job['case_id'] for p in pending):
                await jobs.finish(job, "FAILED", error_code="EXTRACTION_PENDING")
                return
            guidance_prompt = (
                "현재 사건을 처음 넘겨받은 은행 동료에게 킥오프 브리핑해 주세요. 현 상황 한 줄에 사칭 주체·상대 요구·현재 위험을 담고, 고객의 실제 송금·앱 설치·개인정보 제공 여부처럼 아직 미확인인 행동이 있을 때만 짧게 짚어 주세요. 이어서 지금 가장 중요한 행동 한 가지만 구체적으로 안내하고 필요한 이유를 덧붙여 주세요. 본문과 직접 관련된 서로 다른 추천 기능을 최대 세 개까지 연결하되, 고객 확인 질문과 사칭 기관의 공식 소속 확인을 우선하고 목데이터 송금 조회는 추천하지 마세요. 사건 근거가 없는 사실은 추정하지 말고, ‘미완료 업무 확인’ 같은 일반 문구 대신 확인 대상과 목적을 말해 주세요. 짧고 자연스러운 한국어 Markdown으로 작성해 주세요."
                if job["trigger_kind"] == "INITIAL" else
                "새로 반영된 고객 답변·확인 결과·업무 상태를 읽고, 달라진 점을 한 줄로 알려 주세요. 추가 대응이 필요하면 지금 가장 중요한 행동 한 가지만 안내하고 그 행동과 직접 관련된 서로 다른 기능을 최대 세 개까지 추천해 주세요. 고객 확인 질문과 사칭 기관의 공식 소속 확인을 우선하고 목데이터 송금 조회는 추천하지 마세요. 이전 안내를 반복하지 마세요."
            )
            response = await _invoke_case_copilot(job["case_id"], PublicAiInvocationRequest(
                prompt=guidance_prompt,
                requester_user_id=job["actor_user_id"], requester_display_name="은행 담당자",
                channel="TEAM", response_style="BRIEF", client_request_id=job["job_id"]))
            await jobs.finish(job, "COMPLETED", response.message_id)
    except HTTPException as exc:
        code = (exc.detail or {}).get("code", "GUIDANCE_FAILED") if isinstance(exc.detail, dict) else "GUIDANCE_FAILED"
        await jobs.finish(job, "SUPERSEDED" if code == "AI_GENERATION_STALE" else "FAILED", error_code=code)
    except Exception as exc:
        logger.warning("Copilot guidance failed: %s", type(exc).__name__)
        await jobs.finish(job, "FAILED", error_code=type(exc).__name__)


async def run_proactive_case_automation(case_id: str) -> bool:
    """Refresh AI support and staff checklist without contacting the customer.

    The automation is deliberately fail-open for the rest of the Case API:
    an AI outage must not prevent staff or customer messages from being saved.
    """
    try:
        snapshot = await get_case_support_snapshot(case_id)
        await sync_ai_checklist_items(case_id, snapshot)
        actor = await CopilotJobs(repository).enrolled_actor(case_id)
        if actor:
            await enqueue_copilot_guidance(case_id, actor, "CHANGE")
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
    for job in await CopilotJobs(repository).pending():
        await process_copilot_guidance(job)
    return reconciled


@app.on_event("startup")
async def start_proactive_case_worker() -> None:
    global _proactive_worker_task
    ping = getattr(repository, "ping", None)
    if callable(ping):
        await ping()
    for pending_case in await repository.list_pending_analyses():
        schedule_background_case_analysis(str(pending_case["case_id"]))
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
    for task in list(_background_analysis_tasks.values()):
        task.cancel()
    if _background_analysis_tasks:
        await asyncio.gather(*_background_analysis_tasks.values(), return_exceptions=True)
    _background_analysis_tasks.clear()
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


class RightPanelItemMutation(BaseModel):
    model_config = {"extra": "forbid"}
    expected_version: int = Field(ge=0)
    operation: Literal['ADD', 'EDIT', 'ARCHIVE', 'RESTORE', 'PERMANENT_HIDE', 'SET_STATUS']
    text: str | None = Field(default=None, min_length=1, max_length=1200)
    source_text: str | None = Field(default=None, max_length=1200)
    evidence_refs: list[str] = Field(default_factory=list, max_length=20)
    display_status: Literal['TODO', 'COMPLETED'] | None = None

    @model_validator(mode='after')
    def validate_mutation(self):
        if self.operation in {'ADD', 'EDIT'} and (self.text is None or not self.text.strip()):
            raise ValueError('표시할 항목 내용을 입력해 주세요.')
        if self.operation == 'SET_STATUS' and self.display_status is None:
            raise ValueError('업무 상태를 선택해 주세요.')
        if self.operation != 'SET_STATUS' and self.display_status is not None:
            raise ValueError('업무 상태 변경은 SET_STATUS에서만 보낼 수 있습니다.')
        if self.operation not in {'ADD', 'EDIT'} and self.text is not None:
            raise ValueError('추가·수정 외 작업에는 본문을 함께 보낼 수 없습니다.')
        if self.operation == 'ADD' and self.expected_version != 0:
            raise ValueError('새 항목은 expected_version 0으로 등록해야 합니다.')
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
    if actor.actor_type != "BANK_STAFF" or (member and case_role_for_member(member) == "CUSTOMER"):
        raise HTTPException(
            status_code=403,
            detail={"code": "CASE_CONTEXT_FORBIDDEN", "message": "이 사건에 대한 작업 권한이 없습니다."},
        )
    if mvp_context_permissions(actor.actor_id):
        return case_context_v2_repository()
    scoped_actor = actor.for_case(case_id, str(case_role_for_member(member))) if member else actor
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
            and case_role_for_member(item) == "CUSTOMER"
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


@app.get("/api/cases/{case_id}/context-v2/workspace", response_model=PublicContextWorkspaceResponse)
async def read_context_workspace(case_id: str, actor_user_id: str) -> PublicContextWorkspaceResponse:
    store = await require_context_v2_member(case_id, actor_user_id, access="READ")
    resources = await store.list_resources(case_id)
    actions, questions, members, gap_history = await asyncio.gather(
        repository.list_actions(case_id), repository.list_customer_questions(case_id),
        repository.list_members(case_id), store.list_gap_history(case_id),
    )
    # Context V2 is the only public Fact source. Legacy Fact-shaped fields are
    # not duplicated in the workspace response.
    result = build_workspace(resources, actions, questions, gap_history)
    role = next((case_role_for_member(m) for m in members if m.get("user_id") == actor_user_id and m.get("status", "ACTIVE") == "ACTIVE"), None)
    allow_all = mvp_context_permissions(actor_user_id)
    result["permissions_mode"] = "MVP_OPEN" if allow_all else "ROLE_BASED"
    result["can_write"] = allow_all or role in {"CASE_OWNER", "CHAT_OPERATOR", "REVIEWER"}
    result["can_review"] = allow_all or role in {"CASE_OWNER", "REVIEWER"}
    result["can_review_suggestions"] = allow_all or role in {"CASE_OWNER", "CHAT_OPERATOR", "REVIEWER"}
    return PublicContextWorkspaceResponse.model_validate(result)


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
            try:
                await _promote_confirmed_money_fact_to_transaction(case_id, fact)
            except Exception:
                # The fact review remains authoritative.  Keep the failure
                # visible in logs rather than guessing a transaction row.
                logger.exception("Could not promote confirmed money fact %s to transaction", fact.fact_id)
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
    store = await require_context_v2_member(case_id, actor_user_id, access="WRITE")
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
    if actor.actor_type != 'BANK_STAFF' or (member and case_role_for_member(member) == 'CUSTOMER'):
        return []
    if not mvp_context_permissions(actor.actor_id) and not (
        member and actor.for_case(case_id, str(case_role_for_member(member))).can('WRITE')
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


@app.get('/api/cases/{case_id}/right-panel/items', response_model=list[ContextItem])
async def read_right_panel_items(case_id: str, actor_user_id: str):
    await require_context_v2_member(case_id, actor_user_id, access='READ')
    store = await context_display_repository(case_id)
    return [item for item in await store.list_items(case_id, include_deleted=True)
            if item.section in RightPanelSection.__args__]


@app.put('/api/cases/{case_id}/right-panel/items/{section}/{semantic_key}', response_model=ContextItem)
async def mutate_right_panel_item(
    case_id: str, section: RightPanelSection, semantic_key: str, actor_user_id: str,
    request: RightPanelItemMutation,
):
    await require_context_v2_member(case_id, actor_user_id, access='WRITE')
    store = await context_display_repository(case_id)
    operation = 'DELETE' if request.operation == 'ARCHIVE' else request.operation
    try:
        return await store.change_right_panel_item(
            case_id, section, semantic_key, request.expected_version, operation, actor_user_id,
            text=request.text, source_text=request.source_text, evidence_refs=request.evidence_refs,
            staff_authored=request.operation == 'ADD', display_status=request.display_status,
        )
    except ContextItemConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail='사건 또는 표시 항목을 찾을 수 없습니다.') from exc


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
        updated = await repository.update_action(
            case_id, action_id, next_status, request.updated_by,
            note=request.note, expected_version=request.expected_version,
            title=request.title, visibility=request.visibility,
        )
        return to_public_action(updated)
    except CaseVersionConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "VERSION_CONFLICT", "message": "Action has changed.", "current_version": exc.current_version},
        ) from exc
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
            final_report = PublicReportResponse.model_validate(_annotate_report_revision(stored_final_report, record))
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


@app.api_route(
    "/api/cases/{case_id}/voice-sessions/{session_id}/transcript",
    methods=["GET", "POST"],
    status_code=410,
)
async def retired_voice_transcript(case_id: str, session_id: str) -> None:
    """Legacy multi-segment endpoint retained as an explicit storage boundary.

    The request body is intentionally not parsed. CSR never accepts, stores, or
    returns transcript segments through this legacy voice-session URL. The demo
    analyzer stores its single submitted input in ``case_inputs`` instead, and
    that value is excluded from Case Copilot/Context AI payloads.
    """
    raise HTTPException(
        status_code=410,
        detail={
            "code": "TRANSCRIPT_STORAGE_DISABLED",
            "message": "레거시 통화 구간 저장·조회 API는 지원하지 않습니다. 데모 분석 입력은 Case 입력으로 별도 보관됩니다.",
        },
    )


@app.get("/api/cases/{case_id}/reports/live")
async def get_live_report(case_id: str) -> dict:
    record = await repository.get(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case를 찾을 수 없습니다."})
    return record["initial_report"]


def _enforce_proposed_fact_caution(report: dict[str, Any], report_facts: list[dict[str, Any]]) -> dict[str, Any]:
    """Keep upstream PROPOSED facts explicitly unconfirmed in report prose."""
    proposed = [item for item in report_facts if item.get("status") == "PROPOSED"]
    if not proposed:
        return report
    marker = "PROPOSED (NOT CONFIRMED)"
    terms = {
        token.lower()
        for item in proposed
        for token in re.findall(r"[A-Za-z0-9가-힣]{2,}", str(item.get("value") or ""))
    }
    for key in ("executive_summary", "incident_summary", "customer_impact_summary"):
        text = str(report.get(key) or "").strip()
        if text and marker not in text and any(term in text.lower() for term in terms):
            report[key] = f"{marker}: {text}"
    facts = []
    for item in report.get("verified_facts") or []:
        value = str(item)
        facts.append(value if marker in value or "확인 전" in value or "미확인" in value or not any(term in value.lower() for term in terms) else f"{marker}: {value}")
    report["verified_facts"] = facts
    return report


@app.post("/api/cases/{case_id}/reports/finalize", response_model=PublicReportResponse)
async def finalize_case_report(case_id: str, request: AdminCaseFinalizeRequest) -> PublicReportResponse:
    require_admin_password(request.password)
    try:
        case = await repository.get(case_id)
        if case is None:
            raise KeyError(case_id)
        resources, verifications, actions, messages, questions = await asyncio.gather(
            case_context_v2_repository().list_resources(case_id),
            repository.list_verifications(case_id),
            repository.list_actions(case_id),
            repository.list_messages(case_id),
            repository.list_customer_questions(case_id),
        )
        if isinstance(repository, MySqlCaseRepository):
            display_store = await context_display_repository(case_id)
            display_items = await display_store.list_items(case_id, include_deleted=True)
        else:
            display_records = getattr(repository, "_display_items", {})
            display_items = list(display_records.values()) if isinstance(display_records, dict) else []
        summary = build_summary_projection(case, resources, verifications, actions, display_items)
        merged_facts, _ = merge_support_records(resources, [], actions)
        v2_fact_ids = {fact.fact_id for fact in resources.facts}
        v2_fact_fields = {
            SEMANTIC_FIELDS[fact.semantic_key]
            for fact in resources.facts
            if fact.semantic_key in SEMANTIC_FIELDS
        }
        report_facts = [
            item for item in merged_facts
            if item.get("status") not in {"REJECTED", "SUPERSEDED"}
            and (
                item.get("fact_id") in v2_fact_ids
                or normalize_target_field(str(item.get("field", ""))) not in v2_fact_fields
            )
        ]
        report_actions = [
            item for item in actions
            if item.get("actor_type") in {None, "BANK_STAFF"}
            and not str(item.get("action_type", "")).startswith("CUSTOMER_PROGRESS:")
        ]
        staff = await read_staff_context_records(case_id)
        ai_report = await service.ai_client.generate_final_report({
            "case_id": case_id,
            "case_summary": summary["text"],
            "workflow_status": case.get("status", "TRIAGE"),
            "case_mode": case.get("mode", "PREVENT"),
            "staff_context": staff_context(staff),
            "known_facts": [user_text(f"{item.get('field')}: {item.get('value')} ({item.get('status')})") for item in report_facts[:40]],
            "recent_conversation": [
                f"{item.get('actor_display_name', item.get('actor_type', '작성자'))}: {item.get('content', '')[:500]}"
                for item in messages[-30:] if item.get("message_kind") != "REPORT_CARD" and item.get("visibility") != "AI_PRIVATE"
            ],
            "verification_results": [
                f"{item.get('target')}: {item.get('result_summary') or item.get('claim')} ({item.get('status')})"
                for item in verifications[:30]
            ],
            "action_results": [
                user_text(f"{item.get('title') or item.get('action_type')}: {item.get('note') or '상세 내용 없음'} ({item.get('status')})")
                for item in report_actions[:30]
            ],
            "customer_answers": [
                f"질문: {item.get('question_text')} / 고객 답변: {item.get('answer_text')}"
                for item in questions if item.get("answer_text")
            ][:30],
            "closure_note": request.note,
        })
        ai_report = _enforce_proposed_fact_caution(ai_report, report_facts)
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
            {"section_key": "report_metadata", "content": {
                "summary_source_revision": summary["source_revision"],
            }},
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
    latest_case = await repository.get(case_id) or case
    return PublicReportResponse.model_validate(_annotate_report_revision(report, latest_case))


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
    case = await repository.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found."})
    report = await repository.get_final_report(case_id)
    if report is None:
        raise HTTPException(status_code=404, detail={"code": "FINAL_REPORT_NOT_FOUND", "message": "Final report not found."})
    return PublicReportResponse.model_validate(_annotate_report_revision(report, case))


def _annotate_report_revision(report: dict, case: dict) -> dict:
    metadata = next((item.get("content") or {} for item in report.get("sections", []) if item.get("section_key") == "report_metadata"), {})
    source = metadata.get("summary_source_revision")
    current = max(1, int(case.get("context_revision", 1)))
    # Finalization itself writes one REPORT_CARD message and closes the Case;
    # both are non-input mutations that advance context_revision by two.
    generated_revision = int(source) + 2 if source is not None else None
    return {
        **report,
        "summary_source_revision": int(source) if source is not None else None,
        "current_context_revision": current,
        "is_stale": source is not None and current not in {int(source), generated_revision},
    }


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
        if section.get("section_key") == "report_metadata":
            continue
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
