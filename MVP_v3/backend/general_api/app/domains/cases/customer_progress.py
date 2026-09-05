"""Append-only progress snapshots in the existing transactional action journal.

Only dedicated endpoints write these records. Generic checklist completion,
guide clicks, customer answers and case status never imply workflow completion.
"""
from contracts.public_api.customer_progress import CustomerProgressItem, LABELS, STATUS_LABELS

PREFIX = 'CUSTOMER_PROGRESS:'

class ProgressConflict(Exception):
    pass

def progress_items(actions):
    latest = {step: CustomerProgressItem(step=step, label=label) for step, label in LABELS.items()}
    for action in actions:
        if not action.get('action_type', '').startswith(PREFIX):
            continue
        try:
            item = CustomerProgressItem.model_validate_json(action['note'])
        except (ValueError, TypeError, KeyError):
            continue
        if action['action_type'] != PREFIX + item.step:
            continue
        if item.revision > latest[item.step].revision:
            latest[item.step] = item
    return list(latest.values())

def prepare_progress(actions, command, now):
    current = next(item for item in progress_items(actions) if item.step == command['step'])
    if command['request_confirmation']:
        if current.confirmation_requested:
            return None
        item = current.model_copy(update={'confirmation_requested': True})
    else:
        values = command['values']
        if current.revision != values['expected_revision']:
            raise ProgressConflict('새로운 처리 기록이 있습니다. 최신 내용을 확인한 뒤 다시 저장해 주세요.')
        item = CustomerProgressItem.model_validate({**current.model_dump(), **{key: value for key, value in values.items() if key != 'expected_revision'}})
        item.confirmation_requested = False
    item.revision = current.revision + 1
    item.updated_at = now
    item.status_label = STATUS_LABELS[item.status]
    # Revalidate after model_copy so persisted snapshots always obey the contract.
    item = CustomerProgressItem.model_validate(item.model_dump())
    return {'action_type': PREFIX + item.step, 'actor_type': 'CUSTOMER' if command['request_confirmation'] else 'BANK_STAFF',
            'note': item.model_dump_json()}

def progress_ai_context(items):
    return [
        f'{item.label}: {item.status_label}. {item.summary} '
        f'고객이 할 일: {item.next_action or "등록 없음"}. '
        f'근거: {item.reference or "등록 없음"}. 확인 시각: {item.confirmed_at or "등록 없음"}. '
        f'담당자 확인 요청: {"기록됨 · 답변 대기" if item.confirmation_requested else "없음"}.'
        for item in items
    ]

def actions_for_ai(actions):
    """Expose only the latest progress, with readable meaning rather than journal JSON."""
    items = [item for item in progress_items(actions) if item.revision]
    return [action for action in actions if not action.get('action_type', '').startswith(PREFIX)] + [
        {'action_id': f'progress-{item.step}-{item.revision}', 'action_type': '고객 공개 처리 결과',
         'status': 'COMPLETED' if item.status in {'COMPLETED', 'NOT_APPLICABLE'} and not item.confirmation_requested else 'REQUESTED',
         'note': text} for item, text in zip(items, progress_ai_context(items))
    ]
