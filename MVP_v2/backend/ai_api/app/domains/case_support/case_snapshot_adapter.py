"""General Case snapshot과 AI case-support workflow 사이의 작은 경계."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from contracts.ai_internal.case_snapshot import (
    CaseContextProjection,
    CaseSnapshotAiInput,
    CaseSnapshotPresentationFixture,
)
from contracts.ai_internal.mvp_workflow import QuestionRecommendationContext, TargetField, UnresolvedItem
from contracts.diagnosis import DiagnosisResult

from .workflow import MvpWorkflowService


class CaseSnapshotAiAdapter:
    """Snapshot의 최소 AI 입력만 추려 기존 workflow 결과로 투영한다."""

    def __init__(self, workflow: MvpWorkflowService | None = None) -> None:
        self._workflow = workflow or MvpWorkflowService()

    def adapt(self, snapshot: Mapping[str, Any]) -> CaseSnapshotAiInput:
        warnings = self._warnings_from(snapshot.get("warnings"))
        case_id = self._non_empty_string(snapshot.get("case_id"))
        if case_id is None:
            warnings.append("Case snapshot에 case_id가 없어 AI 결과를 사건에 연결할 수 없습니다.")

        diagnosis = self._diagnosis_from(snapshot.get("diagnosis"), warnings)
        if diagnosis is not None:
            warnings.extend(diagnosis.warnings)
            if diagnosis.partial_failure:
                warnings.append("Diagnosis 결과가 부분 실패 상태입니다.")
            if case_id is not None:
                if diagnosis.case_id is not None and diagnosis.case_id != case_id:
                    warnings.append("Case snapshot과 diagnosis의 case_id가 달라 snapshot 값을 사용했습니다.")
                diagnosis = diagnosis.model_copy(update={"case_id": case_id})

        return CaseSnapshotAiInput(
            case_id=case_id,
            diagnosis=diagnosis,
            question_context=self._question_context_from(snapshot.get("question_context")),
            questions=snapshot.get("questions") or [],
            facts=snapshot.get("facts") or [],
            verifications=snapshot.get("verifications") or [],
            actions=snapshot.get("actions") or [],
            warnings=self._unique(warnings),
        )

    def build_presentation(self, snapshot: Mapping[str, Any]) -> CaseSnapshotPresentationFixture:
        ai_input = self.adapt(snapshot)
        if ai_input.case_id is None or ai_input.diagnosis is None:
            return CaseSnapshotPresentationFixture(case_id=ai_input.case_id, warnings=ai_input.warnings)

        brief = self._workflow.build_brief(ai_input.diagnosis)
        brief = self._apply_live_case_state(brief, ai_input)
        context = self._build_case_context(brief, ai_input)
        questions = self._workflow.recommend_questions(brief, ai_input.question_context)
        return CaseSnapshotPresentationFixture(
            case_id=ai_input.case_id,
            case_brief=brief,
            case_context=context,
            recommended_questions=questions,
            unresolved_items=brief.unresolved_items,
            warnings=ai_input.warnings,
        )

    @staticmethod
    def _apply_live_case_state(brief, ai_input: CaseSnapshotAiInput):
        """Project current Shared Case state onto the diagnosis-derived brief.

        Diagnosis is immutable evidence. Questions, answers, facts and work status
        are mutable operational context and therefore have to be applied every
        time a support snapshot is rebuilt.
        """
        confirmed_fields = {
            item.field for item in ai_input.facts if item.status == "CONFIRMED"
        } | {item.value for item in ai_input.question_context.confirmed_fields}
        answered_fields = {
            item.target_field for item in ai_input.questions if item.status == "ANSWERED"
        } | {item.value for item in ai_input.question_context.answered_question_fields}
        handled_fields = confirmed_fields | answered_fields
        pending_by_field = {
            item.target_field: item
            for item in ai_input.questions
            if item.status in {"PENDING", "ASKED"}
        }

        unresolved: list[UnresolvedItem] = []
        included_fields: set[str] = set()
        for item in brief.unresolved_items:
            field = item.target_field.value
            if field in handled_fields:
                continue
            pending = pending_by_field.get(field)
            unresolved.append(item.model_copy(update={
                "description": (
                    f"고객 답변 대기: {pending.question_text}"
                    if pending is not None else item.description
                ),
            }))
            included_fields.add(field)

        for field, question in pending_by_field.items():
            if field in included_fields or field in handled_fields:
                continue
            try:
                target_field = TargetField(field)
            except ValueError:
                continue
            unresolved.append(UnresolvedItem(
                target_field=target_field,
                description=f"고객 답변 대기: {question.question_text}",
                priority=question.priority,
            ))

        next_checks = [
            check for check in brief.next_checks
            if not CaseSnapshotAiAdapter._check_matches_any_field(check, handled_fields)
        ]
        next_checks.extend(
            f"고객 회신 확인: {question.question_text}"
            for question in pending_by_field.values()
        )
        next_checks.extend(
            f"기관 확인 완료 내용 검토: {item.target}"
            if item.status == "COMPLETED"
            else f"기관 확인 진행: {item.target}"
            for item in ai_input.verifications
            if item.status not in {"FAILED", "ON_HOLD"}
        )
        next_checks.extend(
            f"대응 업무 완료 확인: {item.note or item.action_type}"
            if item.status == "COMPLETED"
            else f"대응 업무 진행: {item.note or item.action_type}"
            for item in ai_input.actions
            if item.status not in {"CANCELLED", "FAILED"}
        )

        summary = CaseSnapshotAiAdapter._synthesize_summary(brief, ai_input, unresolved)

        return brief.model_copy(update={
            "summary": summary,
            "unresolved_items": unresolved,
            "next_checks": CaseSnapshotAiAdapter._unique(next_checks)[:8],
        })

    @staticmethod
    def _synthesize_summary(brief, ai_input: CaseSnapshotAiInput, unresolved: list[UnresolvedItem]) -> str:
        """현재 Case 전체를 짧은 상황 보고로 다시 쓴다.

        Brief는 변경 이력을 이어 붙이는 로그가 아니다. 초기 진단, 고객 답변,
        확정 사실, 기관 확인과 대응 업무의 *현재 상태*를 매번 같은 규칙으로
        다시 투영해 읽는 사람이 지금 상황만 빠르게 파악하게 한다.
        """
        sentences = [CaseSnapshotAiAdapter._base_summary(brief)]

        field_values = CaseSnapshotAiAdapter._current_field_values(ai_input)

        state_parts = [
            statement
            for field in (
                "transfer_status",
                "personal_information_exposure",
                "authentication_information_exposure",
                "transfer_purpose",
                "claimed_organization",
                "incident_claim",
            )
            if (value := field_values.get(field)) is not None
            if (statement := CaseSnapshotAiAdapter._field_statement(field, *value))
        ]
        if state_parts:
            sentences.append(" ".join(state_parts[:3]))

        work_parts: list[str] = []
        completed_verifications = [
            item for item in ai_input.verifications
            if item.status == "COMPLETED" and item.result_summary and item.result_summary.strip()
        ]
        active_verifications = [
            item.target for item in ai_input.verifications
            if item.status not in {"COMPLETED", "FAILED", "ON_HOLD"}
        ]
        active_actions = [
            item.note.strip() or item.action_type
            for item in ai_input.actions
            if item.status not in {"COMPLETED", "CANCELLED", "FAILED"}
            and item.action_type not in {"AI_CHECKLIST_REVIEW", "STAFF_JUDGMENT"}
            and not item.note.startswith("AI_CHECKLIST:")
        ]
        if completed_verifications:
            item = completed_verifications[-1]
            work_parts.append(f"{item.target} 확인 결과 {CaseSnapshotAiAdapter._short(item.result_summary)}")
        elif active_verifications:
            work_parts.append(f"{CaseSnapshotAiAdapter._join_labels(active_verifications)} 기관 확인 진행 중")
        if active_actions:
            work_parts.append(f"{CaseSnapshotAiAdapter._join_labels(active_actions)} 조치 진행 중")
        if work_parts:
            sentences.append(f"현재 {'이며, '.join(work_parts)}입니다.")

        if unresolved:
            labels = [CaseSnapshotAiAdapter._field_label(item.target_field.value) for item in unresolved]
            sentences.append(f"다음으로 {CaseSnapshotAiAdapter._join_labels(labels[:2])} 확인이 필요합니다.")

        return " ".join(filter(None, sentences))[:600].strip()

    @staticmethod
    def _build_case_context(brief, ai_input: CaseSnapshotAiInput) -> CaseContextProjection:
        """최초 진단과 변경 가능한 Case 상태를 하나의 최신 맥락으로 병합한다."""
        field_values = CaseSnapshotAiAdapter._current_field_values(ai_input)
        diagnosis = ai_input.diagnosis

        key_signals = [
            item.text for item in brief.risk_evidence
            if item.event_family in {"IMPERSONATION", "PSY_STRATEGY", "ACTION_REQUEST", "MONEY_MOVEMENT", "AMOUNT"}
        ]
        offender_claims = list(brief.claims)
        offender_demands = [
            event.evidence_text for event in diagnosis.events
            if event.event_family in {"ACTION_REQUEST", "MONEY_MOVEMENT", "AMOUNT"}
            and event.is_requested is not False
        ] if diagnosis is not None else []

        positive_signal_labels = {
            "transfer_status": "고객의 실제 송금 발생",
            "personal_information_exposure": "개인정보 제공 발생",
            "authentication_information_exposure": "비밀번호·인증번호 등 인증정보 제공 발생",
            "remote_control_app": "원격제어 앱 설치 발생",
        }
        for field, label in positive_signal_labels.items():
            current = field_values.get(field)
            if current is not None and CaseSnapshotAiAdapter._answer_polarity(current[0]) is True:
                key_signals.append(label)

        claimed_organization = field_values.get("claimed_organization")
        if claimed_organization and not CaseSnapshotAiAdapter._is_unknown_answer(claimed_organization[0]):
            offender_claims.append(f"{CaseSnapshotAiAdapter._short(claimed_organization[0])} 소속이라고 주장")
        incident_claim = field_values.get("incident_claim")
        if incident_claim and not CaseSnapshotAiAdapter._is_unknown_answer(incident_claim[0]):
            offender_claims.append(f"{CaseSnapshotAiAdapter._short(incident_claim[0])}라고 주장")

        transfer_purpose = field_values.get("transfer_purpose")
        if transfer_purpose and not CaseSnapshotAiAdapter._is_unknown_answer(transfer_purpose[0]):
            offender_demands.append(f"{CaseSnapshotAiAdapter._short(transfer_purpose[0])} 명목의 자금 이동 요구")
        requested_account = field_values.get("requested_account")
        if requested_account and not CaseSnapshotAiAdapter._is_unknown_answer(requested_account[0]):
            offender_demands.append(f"{CaseSnapshotAiAdapter._short(requested_account[0])} 계좌로 송금 요구")
        remote_app = field_values.get("remote_control_app")
        if remote_app and CaseSnapshotAiAdapter._answer_polarity(remote_app[0]) is True:
            offender_demands.append("원격제어 앱 설치 요구")

        for verification in ai_input.verifications:
            if verification.status == "COMPLETED" and verification.result_summary:
                key_signals.append(
                    f"{verification.target} 공식 확인: {CaseSnapshotAiAdapter._short(verification.result_summary)}"
                )

        return CaseContextProjection(
            key_signals=CaseSnapshotAiAdapter._unique(key_signals)[:8],
            offender_claims=CaseSnapshotAiAdapter._unique(offender_claims)[:6],
            offender_demands=CaseSnapshotAiAdapter._unique(offender_demands)[:6],
        )

    @staticmethod
    def _current_field_values(ai_input: CaseSnapshotAiInput) -> dict[str, tuple[str, str]]:
        values: dict[str, tuple[str, str]] = {}
        # 낮은 신뢰 상태부터 넣고, 고객 답변과 담당자 확정 사실이 차례로 덮어쓴다.
        for fact in ai_input.facts:
            if fact.status == "PROPOSED" and fact.value.strip():
                values[fact.field] = (fact.value.strip(), "proposed")
        for question in ai_input.questions:
            if question.status == "ANSWERED" and question.answer_text and question.answer_text.strip():
                values[question.target_field] = (question.answer_text.strip(), "answered")
        for fact in ai_input.facts:
            if fact.status == "CONFIRMED" and fact.value.strip():
                values[fact.field] = (fact.value.strip(), "confirmed")
        return values

    @staticmethod
    def _base_summary(brief) -> str:
        summary = brief.summary.strip()
        if summary:
            return summary if summary.endswith((".", "!", "?")) else f"{summary}."
        return f"{brief.incident_type} 사건의 현재 맥락을 확인하고 있습니다."

    @staticmethod
    def _field_statement(field: str, value: str, source: str) -> str:
        polarity = CaseSnapshotAiAdapter._answer_polarity(value)
        authority = "확인 결과" if source == "confirmed" else "고객 답변상" if source == "answered" else "AI 분석상"
        labels = {
            "transfer_status": ("이미 송금한 상태", "아직 송금하지 않은 상태"),
            "personal_information_exposure": ("개인정보를 제공한 상태", "개인정보를 제공하지 않은 상태"),
            "authentication_information_exposure": ("비밀번호·인증번호 등 인증정보를 제공한 상태", "인증정보를 제공하지 않은 상태"),
        }
        if field in labels and polarity is not None:
            return f"{authority} {labels[field][0 if polarity else 1]}입니다."

        short_value = CaseSnapshotAiAdapter._short(value)
        templates = {
            "transfer_status": f"{authority} 송금 여부는 ‘{short_value}’입니다.",
            "personal_information_exposure": f"{authority} 개인정보 제공 여부는 ‘{short_value}’입니다.",
            "authentication_information_exposure": f"{authority} 인증정보 제공 여부는 ‘{short_value}’입니다.",
            "transfer_purpose": f"송금 요구 이유는 ‘{short_value}’로 파악됩니다.",
            "claimed_organization": f"상대방이 주장한 기관은 ‘{short_value}’로 파악됩니다.",
            "incident_claim": f"상대방의 핵심 주장은 ‘{short_value}’로 파악됩니다.",
        }
        return templates.get(field, "")

    @staticmethod
    def _answer_polarity(value: str) -> bool | None:
        normalized = "".join(value.casefold().split())
        explicit_negative_values = {
            "미제공", "미송금", "not_transferred", "not_provided", "false", "no", "아니요", "아니오",
        }
        negative_markers = (
            "아니", "않", "안했", "못했", "없", "not_",
        )
        positive_markers = (
            "이미송금", "송금했", "이체했", "제공했", "설치했", "transferred", "provided", "yes", "true", "예", "네",
        )
        if normalized in explicit_negative_values or any(marker in normalized for marker in negative_markers):
            return False
        if any(marker in normalized for marker in positive_markers):
            return True
        return None

    @staticmethod
    def _field_label(field: str) -> str:
        return {
            "transfer_status": "실제 송금 여부",
            "transfer_purpose": "송금 요구 이유",
            "claimed_organization": "사칭 기관",
            "incident_claim": "상대방의 사건 주장",
            "personal_information_exposure": "개인정보 제공 여부",
            "authentication_information_exposure": "인증정보 제공 여부",
        }.get(field, field)

    @staticmethod
    def _is_unknown_answer(value: str) -> bool:
        normalized = "".join(value.casefold().split())
        return any(marker in normalized for marker in ("모르", "알수없", "확인안", "unknown", "don'tknow", "dontknow"))

    @staticmethod
    def _short(value: str | None, limit: int = 72) -> str:
        normalized = " ".join((value or "").split())
        return normalized if len(normalized) <= limit else f"{normalized[:limit - 1]}…"

    @staticmethod
    def _join_labels(values: list[str]) -> str:
        unique = CaseSnapshotAiAdapter._unique([value for value in values if value])
        if not unique:
            return ""
        if len(unique) == 1:
            return unique[0]
        return "·".join(unique)

    @staticmethod
    def _check_matches_any_field(check: str, fields: set[str]) -> bool:
        markers = {
            "transfer_status": ("송금", "이체", "입금"),
            "transfer_purpose": ("송금 목적", "이체 목적", "자금 이동"),
            "claimed_organization": ("기관", "사칭"),
            "incident_claim": ("사건", "주장"),
            "personal_information_exposure": ("개인정보",),
            "authentication_information_exposure": ("인증정보", "otp", "비밀번호"),
        }
        normalized = check.casefold()
        return any(
            marker.casefold() in normalized
            for field in fields
            for marker in markers.get(field, (field,))
        )

    @staticmethod
    def _diagnosis_from(value: Any, warnings: list[str]) -> DiagnosisResult | None:
        if value is None:
            warnings.append("Case snapshot에 diagnosis가 없어 AI 사건 정리를 만들지 않았습니다.")
            return None
        try:
            return value if isinstance(value, DiagnosisResult) else DiagnosisResult.model_validate(value)
        except ValidationError:
            warnings.append("Case snapshot의 diagnosis 형식이 유효하지 않아 AI 사건 정리를 만들지 않았습니다.")
            return None

    @staticmethod
    def _non_empty_string(value: Any) -> str | None:
        return value.strip() if isinstance(value, str) and value.strip() else None

    @staticmethod
    def _warnings_from(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]

    @staticmethod
    def _question_context_from(value: Any) -> QuestionRecommendationContext:
        if value is None:
            return QuestionRecommendationContext()
        return value if isinstance(value, QuestionRecommendationContext) else QuestionRecommendationContext.model_validate(value)

    @staticmethod
    def _unique(values: list[str]) -> list[str]:
        return list(dict.fromkeys(values))
