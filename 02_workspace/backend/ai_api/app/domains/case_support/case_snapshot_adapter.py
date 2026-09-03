"""General Case snapshot과 기존 case-support workflow 사이의 작은 경계."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from contracts.ai_internal.case_snapshot import (
    CaseSnapshotAiInput,
    CaseSnapshotPresentationFixture,
)
from contracts.diagnosis import DiagnosisResult

from .workflow import MvpWorkflowService


class CaseSnapshotAiAdapter:
    """Case record의 최소 AI 입력만 추려 기존 workflow 결과로 투영한다.

    이 클래스만 General Backend snapshot의 ``case_id``와 ``diagnosis`` 키를 안다.
    메시지, UI 상태, DB 식별자, report/verification 구조는 AI 판단에 필요하지 않아
    의도적으로 읽거나 전달하지 않는다.
    """

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
                # General Case가 소유하는 식별자를 AI 결과 연결용 metadata로만 맞춘다.
                diagnosis = diagnosis.model_copy(update={"case_id": case_id})

        return CaseSnapshotAiInput(
            case_id=case_id,
            diagnosis=diagnosis,
            warnings=self._unique(warnings),
        )

    def build_presentation(self, snapshot: Mapping[str, Any]) -> CaseSnapshotPresentationFixture:
        """정규화 입력을 기존 Brief/Question workflow로 실행해 내부 fixture를 만든다."""
        ai_input = self.adapt(snapshot)
        if ai_input.case_id is None or ai_input.diagnosis is None:
            return CaseSnapshotPresentationFixture(
                case_id=ai_input.case_id,
                warnings=ai_input.warnings,
            )

        brief = self._workflow.build_brief(ai_input.diagnosis)
        questions = self._workflow.recommend_questions(brief)
        return CaseSnapshotPresentationFixture(
            case_id=ai_input.case_id,
            case_brief=brief,
            recommended_questions=questions,
            unresolved_items=brief.unresolved_items,
            warnings=ai_input.warnings,
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
    def _unique(values: list[str]) -> list[str]:
        return list(dict.fromkeys(values))
