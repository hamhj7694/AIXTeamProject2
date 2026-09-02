from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from contracts.diagnosis import AnalyzeCaseResponse, AnalyzeTextRequest, RiskLevel
from general_api.app.clients.diagnosis_ai import DiagnosisAiClient

from .repository import CaseRepository
from .initial_report import InitialReportBuilder


class AnalyzeCaseService:
    def __init__(self, ai_client: DiagnosisAiClient, repository: CaseRepository, report_builder: InitialReportBuilder | None = None) -> None:
        self.ai_client = ai_client
        self.repository = repository
        self.report_builder = report_builder or InitialReportBuilder()

    async def analyze(self, request: AnalyzeTextRequest) -> AnalyzeCaseResponse:
        text = request.text.strip()
        if not text:
            raise ValueError("통화 내용을 입력하세요.")
        if request.client_request_id:
            existing = await self.repository.find_by_client_request_id(request.client_request_id)
            if existing:
                return self._created_response(existing)

        diagnosis = await self.ai_client.analyze(request.model_copy(update={"text": text}))
        if diagnosis.risk_level is RiskLevel.NORMAL:
            return AnalyzeCaseResponse(
                disposition="NO_CASE", risk=RiskLevel.NORMAL,
                initial_brief="현재 모델 판정 기준 미만입니다. 안전 확정을 의미하지 않으므로 의심 상황은 공식 채널로 확인하세요.",
                diagnosis=diagnosis,
            )

        now = datetime.now(timezone.utc).isoformat()
        case_id = f"VP-{uuid4().hex[:8].upper()}"
        diagnosis = diagnosis.model_copy(update={"case_id": case_id})
        initial_report = self.report_builder.build(case_id, diagnosis)
        stored = await self.repository.create({
            "case_id": case_id,
            "client_request_id": request.client_request_id,
            "input_text": text,
            "risk": diagnosis.risk_level.value,
            "risk_score": diagnosis.risk_score,
            "mode": "PREVENT", "status": "TRIAGE",
            "initial_brief": diagnosis.context.summary,
            "diagnosis": diagnosis.model_dump(mode="json"),
            "initial_report": initial_report.model_dump(mode="json"),
            "created_at": now, "updated_at": now,
        })
        return self._created_response(stored)

    @staticmethod
    def _created_response(record: dict) -> AnalyzeCaseResponse:
        diagnosis = record["diagnosis"]
        diagnosis["case_id"] = record["case_id"]
        return AnalyzeCaseResponse(
            disposition="CASE_CREATED", case_id=record["case_id"], risk=record["risk"],
            mode="PREVENT", status="TRIAGE", initial_brief=record["initial_brief"],
            diagnosis=diagnosis,
            initial_report=record["initial_report"],
        )


STATUS_TRANSITIONS = {
    "NEW": {"NEW", "TRIAGE"},
    "TRIAGE": {"TRIAGE", "VERIFYING", "IN_PROGRESS", "CLOSED"},
    "VERIFYING": {"VERIFYING", "IN_PROGRESS", "CLOSED"},
    "IN_PROGRESS": {"IN_PROGRESS", "CLOSED"},
    "CLOSED": {"CLOSED"},
}
MODE_TRANSITIONS = {
    "PREVENT": {"PREVENT", "RECOVERY", "CLOSED"},
    "RECOVERY": {"RECOVERY", "CLOSED"},
    "CLOSED": {"CLOSED"},
}


class InvalidCaseTransitionError(ValueError):
    pass


async def transition_case(repository: CaseRepository, case_id: str, expected_version: int, *, status: str | None, mode: str | None) -> dict[str, Any]:
    current = await repository.get(case_id)
    if current is None:
        raise KeyError(case_id)
    changes = {key: value for key, value in (("status", status), ("mode", mode)) if value is not None}
    if not changes:
        return current
    if status is not None and status not in STATUS_TRANSITIONS.get(current["status"], set()):
        raise InvalidCaseTransitionError(f"Invalid status transition: {current['status']} -> {status}")
    if mode is not None and mode not in MODE_TRANSITIONS.get(current["mode"], set()):
        raise InvalidCaseTransitionError(f"Invalid mode transition: {current['mode']} -> {mode}")
    return await repository.update_case(case_id, expected_version, changes)
