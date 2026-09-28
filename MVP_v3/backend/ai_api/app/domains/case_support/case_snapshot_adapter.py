"""General Case snapshot과 AI case-support workflow 사이의 작은 경계."""
from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any
from urllib.parse import urlparse

from pydantic import ValidationError

from contracts.ai_internal.case_snapshot import (
    CaseContextProjection,
    CaseSnapshotAiInput,
    CaseSnapshotPresentation,
    CaseSnapshotQuestion,
)
from contracts.ai_internal.mvp_workflow import QuestionRecommendationContext, TargetField, UnresolvedItem
from contracts.diagnosis import DiagnosisResult
from contracts.question_target import canonical_question_scope, is_follow_up_target, encode_follow_up_target

from .workflow import MvpWorkflowService
from .answer_service import CustomerAnswerStructuringService
from .grounding import validate_case_support_grounding
from .question_state_evaluator import QuestionStateEvaluator
from .question_policy import QuestionEligibility, question_eligibility, dynamic_follow_up_allowed


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
            source_revision=self._positive_int(snapshot.get("source_revision")),
            diagnosis=diagnosis,
            question_context=self._question_context_from(snapshot.get("question_context")),
            questions=snapshot.get("questions") or [],
            facts=snapshot.get("facts") or [],
            verifications=snapshot.get("verifications") or [],
            actions=snapshot.get("actions") or [],
            warnings=self._unique(warnings),
        )

    def build_presentation(self, snapshot: Mapping[str, Any]) -> CaseSnapshotPresentation:
        ai_input = self.adapt(snapshot)
        if ai_input.case_id is None or ai_input.diagnosis is None:
            return CaseSnapshotPresentation(case_id=ai_input.case_id, warnings=ai_input.warnings)

        eligibility = self.question_eligibilities(ai_input)
        brief = self._workflow.build_brief(ai_input.diagnosis)
        brief = self._apply_live_case_state(brief, ai_input, eligibility)
        context = self._build_case_context(brief, ai_input)
        questions = self._workflow.recommend_questions(brief, ai_input.question_context, eligibility=eligibility)
        presentation = CaseSnapshotPresentation(
            case_id=ai_input.case_id,
            case_brief=brief,
            case_context=context,
            recommended_questions=questions,
            unresolved_items=brief.unresolved_items,
            warnings=ai_input.warnings,
        )
        validate_case_support_grounding(presentation, ai_input)
        return presentation

    @staticmethod
    def _clear_remote_installation(value: str) -> bool:
        """설치 요구 기록은 실제 설치 여부의 답이나 확인 사실이 아니다."""
        compact = re.sub(r"\s+", "", value).casefold()
        if compact in {"installed", "not_installed", "설치함", "설치안함", "설치됨", "설치되지않음"}:
            return True
        return not CustomerAnswerStructuringService().structure_answer(
            TargetField.REMOTE_CONTROL_APP, value
        ).unresolved

    @staticmethod
    def is_clear_customer_answer(scope: str, answer: str) -> bool:
        try:
            target = TargetField(scope)
        except ValueError:
            return True
        if target is TargetField.REMOTE_CONTROL_APP:
            return CaseSnapshotAiAdapter._clear_remote_installation(answer)
        if target not in {
            TargetField.TRANSFER_STATUS,
            TargetField.PERSONAL_INFORMATION_EXPOSURE,
            TargetField.AUTHENTICATION_INFORMATION_EXPOSURE,
        }:
            return True
        compact = re.sub(r"\s+", "", answer).casefold()
        if compact in {"네", "예", "아니요", "아니오"}:
            return True
        if target is TargetField.TRANSFER_STATUS and compact in {"있음", "없음"}:
            return True
        return not CustomerAnswerStructuringService().structure_answer(target, answer).unresolved

    @staticmethod
    def question_eligibilities(ai_input: CaseSnapshotAiInput) -> dict[str, QuestionEligibility]:
        """기존 typed 입력만 연결한다. 관계가 없는 복수 기록의 current를 선택하지 않는다."""
        context = ai_input.question_context
        scopes = {field.value for field in TargetField}
        scopes.update(canonical_question_scope(question.target_field) for question in ai_input.questions)
        scopes.update(fact.field for fact in ai_input.facts)
        result = {}
        for scope in sorted(scopes):
            questions = [question.model_copy(update={"target_field": scope}) for question in ai_input.questions
                         if canonical_question_scope(question.target_field) == scope]
            facts = [fact for fact in ai_input.facts if fact.field == scope]
            has_scope_facts = bool(facts)
            if scope == TargetField.REMOTE_CONTROL_APP.value:
                facts = [fact for fact in facts if fact.status != "CONFIRMED"
                         or CaseSnapshotAiAdapter._clear_remote_installation(fact.value)]
            # 동일 값·상태의 중복 외에는 한 기록을 대표값으로 임의 선택하지 않는다.
            fact_signals = {(fact.status, fact.value) for fact in facts}
            current_question = questions[0] if len(questions) == 1 else None
            answer_uncertain = (
                current_question is not None
                and bool((current_question.answer_text or "").strip())
                and not CaseSnapshotAiAdapter.is_clear_customer_answer(scope, current_question.answer_text or "")
            )
            evaluation = QuestionStateEvaluator.evaluate(
                semantic_scope=scope,
                question=current_question,
                is_uncertain=True if answer_uncertain else None,
                fact=facts[0] if len(fact_signals) == 1 else None,
            )
            result[scope] = question_eligibility(
                evaluation,
                has_active_question=scope in context.pending_question_fields or any(
                    question.status in {"PENDING", "ASKED"} for question in questions
                ),
                has_skipped_question=any(question.status == "SKIPPED" for question in questions),
                has_answered_question=scope in context.answered_question_fields or any(
                    question.status == "ANSWERED" for question in questions
                ),
                # field 이력만으로 STAFF_CONFIRMED를 만들지 않는다.
                # 호환 입력의 반복 억제와 실제 근거의 충분성은 별개다.
                has_confirmed_history=not has_scope_facts and scope in context.confirmed_fields,
            )
        return result

    @staticmethod
    def follow_up_parents(ai_input: CaseSnapshotAiInput) -> dict[str, CaseSnapshotQuestion]:
        """현재 policy가 허용한 단일 기본 parent만 선정한다. 자식은 다시 parent가 되지 않는다."""
        policies = CaseSnapshotAiAdapter.question_eligibilities(ai_input)
        result = {}
        for parent in ai_input.questions:
            if is_follow_up_target(parent.target_field) or parent.status != "ANSWERED":
                continue
            policy = policies[parent.target_field]
            if not dynamic_follow_up_allowed(policy):
                continue
            if any(is_follow_up_target(q.target_field) and canonical_question_scope(q.target_field) == parent.target_field
                   for q in ai_input.questions):
                continue
            try:
                target = encode_follow_up_target(parent.target_field, parent.question_id)
            except ValueError:
                continue  # 참조 길이 초과는 hash/truncate로 숨기지 않는다.
            result[target] = parent
        return result

    @staticmethod
    def _apply_live_case_state(brief, ai_input: CaseSnapshotAiInput, eligibility: Mapping[str, QuestionEligibility]):
        """Project current Shared Case state onto the diagnosis-derived brief.

        Diagnosis is immutable evidence. Questions, answers, facts and work status
        are mutable operational context and therefore have to be applied every
        time a support snapshot is rebuilt.
        """
        handled_fields = {scope for scope, policy in eligibility.items() if policy.evaluation.is_sufficient}
        pending_by_field = {
            canonical_question_scope(item.target_field): item
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
            included_fields.add(field)

        # 초기 진단에서 빠진 scope도 부족한 답변의 보완 필요성이 사라지지 않게 보존한다.
        for scope, policy in eligibility.items():
            if scope in included_fields or scope in handled_fields or not policy.allow_follow_up:
                continue
            if not any(canonical_question_scope(question.target_field) == scope for question in ai_input.questions):
                continue
            try:
                field = TargetField(scope)
            except ValueError:
                continue
            unresolved.append(UnresolvedItem(
                target_field=field, description="고객 답변 내용의 추가 확인이 필요합니다.", priority="P1",
            ))
            included_fields.add(scope)

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
            and not item.action_type.startswith("AI_CHECKLIST:")
            and item.action_type != "AI_CHECKLIST_REVIEW"
        )

        summary = CaseSnapshotAiAdapter._synthesize_summary(brief, ai_input, unresolved)

        return brief.model_copy(update={
            "summary": summary,
            "unresolved_items": unresolved,
            "next_checks": CaseSnapshotAiAdapter._unique(next_checks)[:8],
        })

    @staticmethod
    def _synthesize_summary(brief, ai_input: CaseSnapshotAiInput, unresolved: list[UnresolvedItem]) -> str:
        """Build a concise, attributed current snapshot from structured evidence.

        This is a current-state summary, not a history of fields or staff workflow.
        It deliberately uses customer answers and source-attributed narratives, and
        never promotes a request, a legacy Fact status, or an unverified amount to
        a completed action.
        """
        sentences: list[str] = []
        incident = CaseSnapshotAiAdapter._incident_summary_label(brief)
        if incident:
            sentences.append(incident)

        field_values = {
            question.target_field: (
                CaseSnapshotAiAdapter._structured_value(question.target_field, question.answer_text or ""),
                "answered",
            )
            for question in ai_input.questions
            if question.status == "ANSWERED" and question.answer_text and question.answer_text.strip()
            and not is_follow_up_target(question.target_field)
        }

        narratives = ai_input.diagnosis.context.feature_narratives if ai_input.diagnosis else []
        claim = CaseSnapshotAiAdapter._summary_claim(narratives, ai_input.diagnosis.context.claims if ai_input.diagnosis else [])
        if claim:
            sentences.append(claim)

        demand_labels = CaseSnapshotAiAdapter._summary_demand_labels(
            narratives,
            ai_input.diagnosis.context.demands if ai_input.diagnosis else [],
            ai_input.diagnosis.features if ai_input.diagnosis else {},
        )
        state_sentence = CaseSnapshotAiAdapter._summary_exposure_state(field_values, unresolved)
        demand_sentence = CaseSnapshotAiAdapter._summary_demand_sentence(demand_labels)
        if demand_sentence and state_sentence:
            demand_prefix = demand_sentence.removesuffix("요구했습니다.")
            sentences.append(f"{demand_prefix}요구했지만, {state_sentence[0].lower() + state_sentence[1:]}")
        elif demand_sentence:
            sentences.append(demand_sentence)
        elif state_sentence:
            sentences.append(state_sentence)

        # A genuine verification result can replace an otherwise generic status
        # sentence, but a test/placeholder record is never summary evidence.
        if not state_sentence:
            completed = next((item for item in reversed(ai_input.verifications)
                              if item.status == "COMPLETED" and item.result_summary
                              and item.result_summary.strip()
                              and not CaseSnapshotAiAdapter._is_placeholder_text(item.target)
                              and not CaseSnapshotAiAdapter._is_placeholder_text(item.claim)), None)
            if completed is not None and sentences:
                verification = " ".join((completed.result_summary or "").split())
                source = "공식 확인으로" if CaseSnapshotAiAdapter._has_official_verification_source(completed.evidence_url) else "담당자 기록에는"
                sentences[-1] = f"{sentences[-1].rstrip('.')}며, {source} {completed.target} 결과가 기록되어 있습니다: {verification}."
            elif completed is not None:
                verification = " ".join((completed.result_summary or "").split())
                sentences.append(f"담당자 확인 기록에 {completed.target} 결과가 있습니다: {verification}.")

        return " ".join(sentence.strip() for sentence in sentences[:3] if sentence.strip()).strip()

    @staticmethod
    def _incident_summary_label(brief) -> str:
        value = " ".join((brief.incident_type or "").split()).strip(" .。")
        value = re.sub(r"^사건\s*[:：]\s*", "", value)
        if not value:
            return "보이스피싱 의심 사건입니다."
        if value.endswith("사건"):
            return f"{value}입니다."
        if "의심" in value:
            return f"{value} 사건입니다."
        return f"{value} 관련 보이스피싱 의심 사건입니다."

    @staticmethod
    def _is_placeholder_text(value: str | None) -> bool:
        return bool(re.search(r"(?:^|\s)(?:테스트|test|dummy|sample|예시)(?:\s|$)", value or "", re.IGNORECASE))

    @staticmethod
    def _summary_claim(narratives, claims: list[str]) -> str:
        candidates = [item for item in narratives if item.status == "CLAIMED"]
        preferred = ("CLAIM_CRIME_INVOLVEMENT", "INCIDENT_CLAIM", "CLAIM_ACCOUNT", "ROLE_PROSECUTION")
        candidates.sort(key=lambda item: next((index for index, code in enumerate(preferred)
                                               if code in item.code.upper()), len(preferred)))
        raw = next((item.sentence for item in candidates if item.sentence.strip()), "")
        raw = raw or next((item.strip() for item in claims if item.strip()), "")
        if not raw:
            return ""
        text = " ".join(raw.split()).strip(" .。")
        text = re.sub(r"^(?:보이스피싱 의심 인물이|보이스피싱 의심 인인은|보이스피싱 의심 인인이|상대방이|상대방은)\s*", "", text)
        text = text.replace("김인수라는 인물과 고객 또는 고객 계좌가", "김인수와 고객 계좌가")
        text = text.replace("고객 또는 고객 계좌가", "고객 계좌가")
        text = re.sub(r"\s*주장함$", "", text)
        if text.endswith("주장했습니다"):
            return f"상대방은 {text}."
        if text.endswith(("다고", "라고", "라며", "며")):
            return f"상대방은 {text} 주장했습니다."
        return f"상대방은 {text}고 주장했습니다."

    @staticmethod
    def _summary_demand_labels(narratives, demands: list[str], features: dict) -> list[str]:
        sources = [item.sentence for item in narratives if item.status == "REQUESTED"] + demands
        sources = [" ".join(text.split()) for text in sources if text and text.strip()]
        labels: list[str] = []
        has_transfer_request = any(re.search(r"송금|이체|자금 이동|안전계좌", text) for text in sources)
        requested_amount = features.get("requested_amount_max")
        amount_label = ""
        if has_transfer_request and requested_amount:
            try:
                amount = int(float(requested_amount))
                amount_label = f"{amount // 10_000:,}만원" if amount >= 10_000 and amount % 10_000 == 0 else f"{amount:,}원"
            except (TypeError, ValueError):
                amount_label = ""
        for text in sources:
            if re.search(r"송금|이체|자금 이동|안전계좌", text):
                match = re.search(r"(\d[\d,]*(?:만원|원))", text)
                amount = match.group(1) if match else amount_label
                label = f"{amount} 송금" if amount else "송금"
                labels.append(label)
            if re.search(r"개인\s*정보|민감\s*정보", text):
                labels.append("개인정보 제공")
            if re.search(r"인증\s*정보|인증번호|OTP|비밀번호", text, re.IGNORECASE):
                labels.append("인증정보 제공")
            if re.search(r"원격\s*제어|화면\s*공유|앱\s*설치", text):
                labels.append("원격제어 앱 설치")
        return list(dict.fromkeys(labels))

    @staticmethod
    def _summary_demand_sentence(labels: list[str]) -> str:
        if not labels:
            return ""
        if len(labels) == 1:
            target = labels[0]
        elif len(labels) == 2:
            target = f"{labels[0]}과 {labels[1]}"
        else:
            target = f"{', '.join(labels[:-1])} 및 {labels[-1]}"
        return f"상대방은 {target}을 요구했습니다."

    @staticmethod
    def _summary_exposure_state(field_values: dict, unresolved: list[UnresolvedItem]) -> str:
        labels = {
            "transfer_status": ("실제 송금", "송금"),
            "personal_information_exposure": ("개인정보 제공", "개인정보"),
            "authentication_information_exposure": ("인증정보 제공", "인증정보"),
            "remote_control_app": ("원격제어 앱 설치", "원격제어 앱"),
        }
        unresolved_fields = {item.target_field.value for item in unresolved}
        answered_states: list[str] = []
        unresolved_labels: list[str] = []
        for field, (label, short_label) in labels.items():
            answer = field_values.get(field)
            if answer:
                value = answer[0]
                polarity = CaseSnapshotAiAdapter._answer_polarity(value)
                if field == "transfer_status" and polarity is True:
                    answered_states.append("송금했다고")
                elif field == "transfer_status" and polarity is False:
                    answered_states.append("송금하지 않았다고")
                elif field == "personal_information_exposure" and value.casefold() == "partially_exposed":
                    answered_states.append("개인정보 일부를 제공했다고")
                elif field == "personal_information_exposure" and polarity is True:
                    answered_states.append("개인정보를 제공했다고")
                elif field == "personal_information_exposure" and polarity is False:
                    answered_states.append("개인정보를 제공하지 않았다고")
                elif field == "authentication_information_exposure" and polarity is True:
                    answered_states.append("인증정보를 제공했다고")
                elif field == "authentication_information_exposure" and polarity is False:
                    answered_states.append("인증정보를 제공하지 않았다고")
                elif field == "remote_control_app" and polarity is True:
                    answered_states.append("원격제어 앱을 설치했다고")
                elif field == "remote_control_app" and polarity is False:
                    answered_states.append("원격제어 앱을 설치하지 않았다고")
                else:
                    unresolved_labels.append(label)
            elif field in unresolved_fields:
                unresolved_labels.append(label)
        if answered_states and unresolved_labels:
            unknown = CaseSnapshotAiAdapter._join_exposure_labels(unresolved_labels)
            if len(answered_states) > 1:
                return f"고객은 {answered_states[0]} 답했고, {answered_states[1]} 답했습니다. {unknown} 여부는 아직 확인되지 않았습니다."
            return f"고객은 {answered_states[0]} 답했으며, {unknown} 여부는 아직 확인되지 않았습니다."
        if answered_states:
            if len(answered_states) > 1:
                return f"고객은 {answered_states[0]} 답했고, {answered_states[1]} 답했습니다."
            return f"고객은 {answered_states[0]} 답했습니다."
        if unresolved_labels:
            unknown = CaseSnapshotAiAdapter._join_exposure_labels(unresolved_labels)
            return f"{unknown} 여부는 아직 확인되지 않았습니다."
        return ""

    @staticmethod
    def _join_exposure_labels(labels: list[str]) -> str:
        values = list(dict.fromkeys(labels))
        if "개인정보 제공" in values and "인증정보 제공" in values:
            values = [value for value in values if value not in {"개인정보 제공", "인증정보 제공"}]
            values.insert(1 if values and values[0] == "실제 송금" else 0, "개인정보·인증정보 제공")
        if len(values) == 1:
            return values[0]
        if len(values) == 2:
            return f"{values[0]} 및 {values[1]}"
        return f"{', '.join(values[:-1])} 및 {values[-1]}"

    @staticmethod
    def _has_official_verification_source(evidence_url: str | None) -> bool:
        parsed = urlparse((evidence_url or "").strip())
        if parsed.scheme.casefold() != "https":
            return False
        host = (parsed.hostname or "").casefold().rstrip(".")
        return any(host == domain or host.endswith("." + domain) for domain in ("go.kr", "gov", "gov.kr"))

    @staticmethod
    def _build_case_context(brief, ai_input: CaseSnapshotAiInput) -> CaseContextProjection:
        """최초 진단과 변경 가능한 Case 상태를 하나의 최신 맥락으로 병합한다."""
        field_values = CaseSnapshotAiAdapter._current_field_values(ai_input)
        diagnosis = ai_input.diagnosis
        context_features = diagnosis.case_context_features if diagnosis is not None else None

        key_signals = [
            CaseSnapshotAiAdapter._readable_signal(item.text, item.event_family) for item in brief.risk_evidence
            if item.event_family in {"IMPERSONATION", "PSY_STRATEGY", "ACTION_REQUEST", "MONEY_MOVEMENT", "AMOUNT"}
        ]
        offender_claims = [CaseSnapshotAiAdapter._readable_signal(item, "IMPERSONATION") for item in brief.claims]
        offender_demands = [
            CaseSnapshotAiAdapter._readable_signal(event.evidence_text, event.event_family) for event in diagnosis.events
            if event.event_family in {"ACTION_REQUEST", "MONEY_MOVEMENT", "AMOUNT"}
            and event.is_requested is not False
        ] if diagnosis is not None else []
        if diagnosis is not None:
            offender_demands.extend(diagnosis.context.demands)

        tactic_labels = {
            "URGENCY": "시간 제한을 내세운 긴급 처리 압박",
            "FEAR": "처벌·계좌 동결 등 불안과 공포 조성",
            "ISOLATION": "가족·은행 직원과의 상의 차단",
            "TACTIC_URGENCY": "시간 제한을 내세운 긴급 처리 압박",
            "TACTIC_FEAR": "처벌·계좌 동결 등 불안과 공포 조성",
            "TACTIC_ISOLATION": "가족·은행 직원과의 상의 차단",
        }
        action_labels = {
            "REQUEST:TRANSFER": "지정 계좌로 송금·이체 요구",
            "REQUEST:SENSITIVE_INFO": "개인정보 또는 계좌정보 제공 요구",
            "REQUEST:AUTH_INFO": "비밀번호·OTP·인증번호 제공 요구",
            "REQUEST:CONTACT_RESTRICTION": "통화 유지 또는 외부 연락 제한 요구",
            "REQUEST_TRANSFER": "송금·이체 요구",
            "REQUEST_INSTALL_APP": "앱 설치 요구",
            "REQUEST_AUTH_INFO": "인증정보 제공 요구",
            "REQUEST_PERSONAL_INFO": "개인정보 제공 요구",
            "REQUEST_KEEP_CALL": "통화 유지 요구",
            "REQUEST_SECRECY": "외부에 알리지 않도록 요구",
        }
        manipulation_tactics = list(diagnosis.context.manipulation_tactics) if diagnosis is not None else []
        manipulation_tactics.extend(
            tactic_labels.get(code, "추가적인 압박·조작 정황 — 구체적인 수법 확인 필요")
            for code in (context_features.manipulation_tactic_codes if context_features else [])
        )
        offender_demands.extend(
            action_labels.get(code, "추가 행동 요구 — 구체적인 요구 확인 필요")
            for code in (context_features.requested_action_codes if context_features else [])
        )
        customer_exposure: list[str] = []

        positive_signal_labels = {
            "transfer_status": "고객의 실제 송금 발생",
            "personal_information_exposure": "개인정보 제공 발생",
            "authentication_information_exposure": "비밀번호·인증번호 등 인증정보 제공 발생",
            "remote_control_app": "원격제어 앱 설치 발생",
        }
        for field, label in positive_signal_labels.items():
            current = field_values.get(field)
            if current is not None and CaseSnapshotAiAdapter._answer_polarity(current[0]) is True:
                projected_label = (
                    "개인정보 일부 제공 발생"
                    if field == "personal_information_exposure" and current[0].casefold() == "partially_exposed"
                    else label
                )
                key_signals.append(projected_label)
                customer_exposure.append(projected_label)

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
        requested_amounts = [
            CaseSnapshotAiAdapter._short(fact.value, 80)
            for fact in ai_input.facts
            if fact.field == "requested_amount_krw" and fact.status in {"PROPOSED", "CONFIRMED"} and fact.value.strip()
        ]
        if requested_amounts:
            offender_demands.append(f"요구 금액 기록(개별): {', '.join(requested_amounts[:30])}")

        for verification in ai_input.verifications:
            if verification.status == "COMPLETED" and verification.result_summary:
                key_signals.append(
                    f"{verification.target} 공식 확인: {CaseSnapshotAiAdapter._short(verification.result_summary)}"
                )

        money_events = []
        if diagnosis is not None:
            for atom in diagnosis.semantic_atoms:
                if atom.amount_value_krw is None:
                    continue
                money_events.append({
                    "event_id": atom.amount_event_id or atom.source_event_id or atom.atom_id,
                    "atom_id": atom.atom_id,
                    "turn": atom.source_turn_id,
                    "amount_krw": int(atom.amount_value_krw),
                    "role": atom.amount_role or ("REQUESTED_AMOUNT" if atom.action_state in {"REQUESTED", "INSTRUCTED"} else "TRANSFER_OUT"),
                    "direction": atom.amount_direction or ("REQUEST" if atom.action_state in {"REQUESTED", "INSTRUCTED"} else "OUT"),
                    "scope": atom.amount_scope or "EVENT",
                    # Preserve what the analysis actually attributed. A
                    # TRANSFER_OUT role alone is not proof of a bank transfer.
                    "action_state": atom.action_state,
                    "modality": atom.modality,
                    "claim_status": atom.claim_status,
                    "speaker_role": CaseSnapshotAiAdapter._enum_value(atom.speaker_role),
                    "actor_role": CaseSnapshotAiAdapter._enum_value(atom.actor_role),
                    "target_role": CaseSnapshotAiAdapter._enum_value(atom.target_role),
                    "reported_by_role": CaseSnapshotAiAdapter._enum_value(atom.reported_by_role),
                    "predicate": atom.predicate,
                })

        confirmed_facts = [
            {"fact_id": fact.fact_id, "field": fact.field, "value": fact.value, "status": fact.status}
            for fact in ai_input.facts if fact.status == "CONFIRMED"
        ]
        proposed_facts = [
            {"fact_id": fact.fact_id, "field": fact.field, "value": fact.value, "status": fact.status}
            for fact in ai_input.facts if fact.status == "PROPOSED"
        ]
        unresolved_items = [
            str(getattr(item, "description", "추가 확인 필요"))
            for item in brief.unresolved_items
        ]

        return CaseContextProjection(
            situation_summary=brief.summary,
            key_signals=CaseSnapshotAiAdapter._unique(key_signals)[:8],
            offender_claims=CaseSnapshotAiAdapter._unique(offender_claims)[:6],
            offender_demands=CaseSnapshotAiAdapter._unique(offender_demands)[:6],
            manipulation_tactics=CaseSnapshotAiAdapter._unique(manipulation_tactics)[:6],
            customer_exposure=CaseSnapshotAiAdapter._unique(customer_exposure)[:6],
            next_actions=CaseSnapshotAiAdapter._unique(brief.next_checks)[:8],
            money_events=money_events[:100],
            confirmed_facts=confirmed_facts[:100],
            proposed_facts=proposed_facts[:100],
            unresolved_items=unresolved_items[:100],
            verification_records=[item.model_dump(mode="python") for item in ai_input.verifications][:100],
            staff_actions=[item.model_dump(mode="python") for item in ai_input.actions][:100],
            projection_revision=ai_input.source_revision,
        )

    @staticmethod
    def _readable_signal(text: str, family: str) -> str:
        # Older stored Cases used English family labels. Reproject only that
        # exact legacy format; do not rewrite an employee's natural-language text.
        if text.strip().casefold() != f"{family.replace('_', ' ')} 신호".casefold():
            return text
        return {
            "IMPERSONATION": "기관 또는 다른 사람의 신분을 내세운 정황",
            "PSY_STRATEGY": "불안이나 긴박함을 이용해 판단을 재촉하는 정황",
            "ACTION_REQUEST": "상대방이 특정 행동을 요구한 정황",
            "MONEY_MOVEMENT": "금전 이동을 요구하거나 언급한 정황",
            "AMOUNT": "금액 언급 — 실제 피해 금액인지는 확인 필요",
        }.get(family, "추가 확인이 필요한 통화 정황")

    @staticmethod
    def _current_field_values(ai_input: CaseSnapshotAiInput) -> dict[str, tuple[str, str]]:
        values: dict[str, tuple[str, str]] = {}
        follow_scopes = {canonical_question_scope(q.target_field) for q in ai_input.questions if is_follow_up_target(q.target_field)}
        # 낮은 신뢰 상태부터 넣고, 고객 답변과 담당자 확정 사실이 차례로 덮어쓴다.
        for fact in ai_input.facts:
            if fact.status == "PROPOSED" and fact.value.strip():
                values[fact.field] = (CaseSnapshotAiAdapter._structured_value(fact.field, fact.value), "proposed")
        for question in ai_input.questions:
            if is_follow_up_target(question.target_field):
                continue  # 확인 행동의 답변은 부모 답변을 대체하지 않는다.
            if question.status == "ANSWERED" and question.answer_text and question.answer_text.strip():
                values[question.target_field] = (
                    CaseSnapshotAiAdapter._structured_value(question.target_field, question.answer_text),
                    "answered",
                )
        for fact in ai_input.facts:
            if fact.status == "CONFIRMED" and fact.value.strip():
                values[fact.field] = (CaseSnapshotAiAdapter._structured_value(fact.field, fact.value), "confirmed")
        for scope in follow_scopes:
            signals = {(f.status, f.value) for f in ai_input.facts if f.field == scope and f.value.strip()}
            signals.update(("ANSWERED", q.answer_text) for q in ai_input.questions
                           if canonical_question_scope(q.target_field) == scope and q.answer_text)
            if len({value for _, value in signals}) > 1:
                values.pop(scope, None)  # 관계만으로 current/correction을 추측하지 않는다.
        return values

    @staticmethod
    def _structured_value(field: str, value: str) -> str:
        """Normalize supported answers while preserving every unresolved raw value."""
        raw_value = value.strip()
        try:
            target_field = TargetField(field)
        except ValueError:
            return raw_value
        result = CustomerAnswerStructuringService().structure_answer(target_field, raw_value)
        return result.structured_value or raw_value

    @staticmethod
    def _base_summary(brief) -> str:
        summary = brief.summary.strip()
        if summary:
            normalized = " ".join(summary.split())
            # A stored diagnosis summary can contain an accidentally repeated
            # history block. Do not copy that block into the current snapshot.
            if len(normalized) > 360:
                incident_type = " ".join((brief.incident_type or "현재 사건").split())
                return f"{incident_type} 관련 사건으로 현재 상황을 확인하고 있습니다."
            return normalized if normalized.endswith((".", "!", "?")) else f"{normalized}."
        return f"{brief.incident_type} 사건의 현재 맥락을 확인하고 있습니다."

    @staticmethod
    def _field_statement(field: str, value: str, source: str) -> str:
        polarity = CaseSnapshotAiAdapter._answer_polarity(value)
        authority = "확인 결과" if source == "confirmed" else "고객 답변상" if source == "answered" else "AI 분석상"
        if field == "personal_information_exposure" and value.casefold() == "partially_exposed":
            return f"{authority} 개인정보 일부를 제공한 상태입니다."
        labels = {
            "transfer_status": ("이미 송금한 상태", "아직 송금하지 않은 상태"),
            "personal_information_exposure": ("개인정보를 제공한 상태", "개인정보를 제공하지 않은 상태"),
            "authentication_information_exposure": ("비밀번호·인증번호 등 인증정보를 제공한 상태", "인증정보를 제공하지 않은 상태"),
        }
        if field in labels and polarity is not None:
            return f"{authority} {labels[field][0 if polarity else 1]}입니다."

        short_value = " ".join(value.split())
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
            "이미송금", "송금했", "이체했", "제공했", "설치했", "전달했", "알려줬",
            "transferred", "provided", "partially_exposed", "exposed", "installed", "yes", "true", "예", "네",
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
            "remote_control_app": "원격제어 앱 설치 여부",
            "requested_account": "요구받은 계좌",
            "caller_phone": "상대방 전화번호",
        }.get(field, "추가 확인 사항")

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
    def _enum_value(value: Any) -> str | None:
        if value is None:
            return None
        return str(getattr(value, "value", value))

    @staticmethod
    def _positive_int(value: Any) -> int | None:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return None
        return number if number >= 1 else None

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
