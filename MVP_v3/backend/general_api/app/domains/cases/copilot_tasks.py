"""Apply bounded internal-task intents; only staff reports can complete work."""
import re

from contracts.ai_internal.case_copilot import CopilotTaskIntent
from .copilot_state import digest
from .case_context_v2_repository import ContextV2ConflictError, ContextV2TransitionError


def scope(title):
    if '지급정지' in title or '계좌 정지' in title:
        return 'payment_hold'
    if any(term in title for term in ('기관', '소속', '공식', '사칭', '검찰', '경찰', '금감원', '금융감독원', '법원')):
        institution = next((name for name in ('금융감독원', '금감원', '검찰', '경찰', '법원', '은행') if name in title), 'unspecified')
        return f'institution:{institution}'
    for key, terms in (("auth", ("인증", "비밀번호", "OTP")), ("personal", ("개인정보", "신분증")),
                       ("device", ("앱", "원격", "기기")), ("transfer", ("송금", "이체", "거래", "지급정지")),
                       ):
        if any(term.lower() in title.lower() for term in terms):
            return key
    return re.sub(r"\W+", "", title).lower()


def task_action(task):
    key = {"CUSTOMER_CONTACT": "CUSTOMER_QUESTION", "TRANSACTION_REVIEW": "TRANSACTION_LOOKUP",
           "INSTITUTION_VERIFICATION": "OFFICIAL_VERIFICATION"}.get(task.task_type, "RESPONSE_ACTION")
    return dict(action_key=key, kind="TOOL", target_channel="TEAM", target_type="TASK",
                target_id=task.task_id, expected_version=task.version)


async def apply_task_intents(store, state, raw_intents, actor, source_message_ids, *, allow_cancel=False):
    messages = {m["message_id"]: m for m in state.messages if m.get("actor_type") == "BANK_STAFF"
                and m.get("actor_user_id") == actor and m.get("visibility") == "BANK_INTERNAL"
                and m.get("message_kind", "CHAT") == "CHAT" and m.get("message_id") in source_message_ids}
    sources = {f["fact_id"]: f for f in state.facts}
    sources.update({q["question_id"]: q for q in state.questions})
    sources.update({v["verification_task_id"]: v for v in state.verifications})
    sources.update(messages)
    # Structured initial analysis is an explicit source, never invented by the model.
    if state.case.get("diagnosis"):
        sources["analysis"] = state.case["diagnosis"]
    tasks = {t.task_id: t for t in state.resources.tasks}
    receipts, buttons = [], []
    for raw in raw_intents[:3]:
        intent = CopilotTaskIntent.model_validate(raw)
        receipt = {"operation": intent.operation, "status": "FAILED", "title": intent.title}
        try:
            if intent.operation == "CREATE":
                if not intent.title.strip() or not intent.description.strip() or not intent.evidence_ids or any(e not in sources for e in intent.evidence_ids):
                    raise ValueError("TASK_EVIDENCE_REQUIRED")
                if re.search(r"AI_CHECKLIST|\b(?:REQUESTED|PROPOSED|CONFIRMED|BANK_EMPLOYEE|TASK|RECOMMENDATION)\b", intent.title + ' ' + intent.description):
                    raise ValueError("TASK_HUMAN_READABLE_TEXT_REQUIRED")
                family = digest([intent.task_type, scope(intent.title)])[:16]
                basis = digest({key: sources[key] for key in sorted(set(intent.evidence_ids))})[:24]
                request_key = f"copilot:{family}:{basis}"
                existing = next((t for t in tasks.values() if t.client_request_id == request_key or
                    (t.status not in {"COMPLETED", "CANCELLED"} and t.task_type == intent.task_type and scope(t.title) == scope(intent.title))), None)
                if existing:
                    task = existing
                    receipt["status"] = "SUPPRESSED" if task.status in {"COMPLETED", "CANCELLED"} else "UNCHANGED"
                else:
                    task = await store.create_task(state.case["case_id"], dict(client_request_id=request_key,
                        source="AI_RECOMMENDED", title=intent.title, description=intent.description,
                        task_type=intent.task_type, priority=intent.priority,
                        evidence_refs=[{"type": "STRUCTURED_SIGNAL" if e == "analysis" else "MESSAGE" if e in messages else "STAFF_RECORD", "id": e}
                                       for e in intent.evidence_ids]), "system:case-copilot")
                    receipt["status"] = "APPLIED"
            else:
                task = tasks.get(intent.target_id)
                message = messages.get(intent.source_message_id)
                if task is None or message is None or task.version != intent.expected_version:
                    raise ValueError("TASK_TARGET_OR_SOURCE_CHANGED")
                text = re.sub(r"\s+", "", message["content"])
                if re.search(r"그거|그것|해당업무", text):
                    previous = next((m for m in reversed(state.messages) if m.get('actor_type') == 'BANK_AGENT' and m.get('visibility') == 'BANK_INTERNAL' and m.get('channel') == 'TEAM'), {})
                    targets = {a.get('target_id') for a in (previous.get('ai_metadata') or {}).get('recommended_actions', []) if a.get('target_type') == 'TASK'}
                    if targets != {task.task_id}:
                        raise ValueError("AMBIGUOUS_TASK_TARGET")
                if re.search(r"(?:안했|못했|하지않|할까|해야|예정|하면|[?？]|했는지|됐는지)", text):
                    raise ValueError("EXPLICIT_TASK_INSTRUCTION_REQUIRED")
                data = {"expected_version": task.version}
                if intent.operation == "COMPLETE":
                    if not re.search(r"완료|끝냈|처리했|마쳤|확인했|발송했", text) or not intent.result_summary.strip():
                        raise ValueError("COMPLETION_REPORT_REQUIRED")
                    data.update(result_summary=intent.result_summary,
                        evidence_refs=[{"type": "MESSAGE", "id": message["message_id"]}])
                    task = await store.complete_task(state.case["case_id"], task.task_id, data, actor)
                elif intent.operation == "CANCEL":
                    if not allow_cancel or not re.search(r"삭제|취소|빼줘|제외|지워", text):
                        raise ValueError("TASK_CANCEL_PERMISSION_REQUIRED")
                    task = await store.cancel_task(state.case["case_id"], task.task_id,
                        {**data, "reason": message["content"][:1000]}, actor)
                else:
                    if not re.search(r"수정|바꿔|변경|다시|복구|재등록|진행", text):
                        raise ValueError("EXPLICIT_TASK_INSTRUCTION_REQUIRED")
                    if intent.operation == "REOPEN":
                        data["status"] = "TODO"
                    else:
                        if intent.title: data["title"] = intent.title
                        if intent.description: data["description"] = intent.description
                        data["priority"] = intent.priority
                    task = await store.update_task(state.case["case_id"], task.task_id, data, actor)
                receipt["status"] = "APPLIED"
            tasks[task.task_id] = task
            receipt.update(target_id=task.task_id, title=task.title, version=task.version)
            if task.status not in {"COMPLETED", "CANCELLED"}:
                buttons.append(task_action(task))
        except (ValueError, KeyError, ContextV2ConflictError, ContextV2TransitionError) as exc:
            receipt["error_code"] = "VERSION_CONFLICT" if isinstance(exc, ContextV2ConflictError) else str(exc)[:120]
        receipts.append(receipt)
    return receipts, buttons
