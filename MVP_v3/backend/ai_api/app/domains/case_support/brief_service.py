"""DiagnosisResult를 담당자용 Structured Case Brief로 투영한다."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

from openai import AsyncOpenAI

from contracts.ai_internal.mvp_workflow import CaseBrief, QuestionPriority, TargetField, UnresolvedItem
from contracts.diagnosis import DiagnosisResult, Evidence

from .brief_prompt import CASE_BRIEF_OUTPUT_SCHEMA, build_case_brief_prompt


@dataclass(frozen=True)
class CaseBriefBuildOutcome:
    """LLM 실패 여부를 Contract 밖에서 전달해, 실패를 성공처럼 숨기지 않는다."""

    brief: CaseBrief
    used_fallback: bool = False
    warning: str | None = None


class CaseBriefService:
    def build_brief(self, diagnosis: DiagnosisResult) -> CaseBrief:
        """LLM 없이도 항상 재현 가능한 최소 Brief를 만든다."""
        evidence = list(diagnosis.evidence)
        impersonation = next(
            (item.subtype for item in evidence if item.event_family == "IMPERSONATION" and item.subtype),
            None,
        )
        money_evidence = [item.text for item in evidence if item.event_family == "MONEY_MOVEMENT"]
        amount = self._requested_amount(diagnosis)
        unresolved = self._unresolved_items(diagnosis, bool(money_evidence), impersonation is not None)
        return CaseBrief(
            summary=diagnosis.context.summary,
            incident_type=diagnosis.context.incident_type,
            risk_level=diagnosis.risk_level,
            risk_score=diagnosis.risk_score,
            impersonation_target=impersonation,
            claims=list(diagnosis.context.claims),
            transfer_context=" ".join(money_evidence) or None,
            mentioned_amount_krw=amount,
            risk_evidence=evidence,
            # Diagnosis Contract에는 반대 증거를 별도로 식별하는 필드가 없다.
            counter_evidence=[],
            unresolved_items=unresolved,
            next_checks=list(diagnosis.context.recommended_next_steps),
        )

    async def build(self, diagnosis: DiagnosisResult) -> CaseBriefBuildOutcome:
        """실제 LLM으로 요약을 보강하고 장애 시 입력 기반 안전 초안을 반환한다."""
        fallback = self.build_brief(diagnosis)
        try:
            instructions, input_text = build_case_brief_prompt(diagnosis, fallback)
            client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
            response = await client.responses.create(
                model=os.getenv("OPENAI_CASE_BRIEF_MODEL", "gpt-4o-mini"),
                instructions=instructions,
                input=input_text,
                text={"format": {"type": "json_schema", "name": "case_brief_summary_v1", "schema": CASE_BRIEF_OUTPUT_SCHEMA, "strict": True}},
            )
            generated = json.loads(response.output_text)
            summary = str(generated["summary"]).strip()
            if not summary:
                raise ValueError("empty summary")
            # 위험도·금액·증거 같은 판단 필드는 결정론적 값을 그대로 보존한다.
            return CaseBriefBuildOutcome(brief=fallback.model_copy(update={"summary": summary}))
        except Exception as exc:
            return CaseBriefBuildOutcome(
                brief=fallback,
                used_fallback=True,
                warning=f"Case Brief LLM fallback: {type(exc).__name__}",
            )

    @staticmethod
    def _requested_amount(diagnosis: DiagnosisResult) -> float | None:
        value = diagnosis.features.get("requested_amount_max")
        try:
            amount = float(value)
        except (TypeError, ValueError):
            return None
        return amount if amount > 0 else None

    @staticmethod
    def _unresolved_items(
        diagnosis: DiagnosisResult, has_money_movement: bool, has_impersonation: bool,
    ) -> list[UnresolvedItem]:
        fields: list[tuple[TargetField, str, QuestionPriority]] = [
            (TargetField.TRANSFER_STATUS, "실제 송금 진행 여부 확인 필요", QuestionPriority.P0),
            (TargetField.PERSONAL_INFORMATION_EXPOSURE, "개인정보 제공 여부 확인 필요", QuestionPriority.P0),
            (TargetField.AUTHENTICATION_INFORMATION_EXPOSURE, "인증정보 제공 여부 확인 필요", QuestionPriority.P0),
        ]
        if has_money_movement:
            fields.append((TargetField.TRANSFER_PURPOSE, "송금 요구의 목적과 맥락 확인 필요", QuestionPriority.P1))
        if not has_impersonation:
            fields.append((TargetField.CLAIMED_ORGANIZATION, "상대방이 주장한 소속 기관 확인 필요", QuestionPriority.P1))
        if not diagnosis.context.claims:
            fields.append((TargetField.INCIDENT_CLAIM, "상대방이 주장한 사건 또는 상황 확인 필요", QuestionPriority.P1))
        return [UnresolvedItem(target_field=field, description=description, priority=priority) for field, description, priority in fields]
