"""Working information is not an assertion of official verification."""
def staff_working_fact(source_kind, value):
    if source_kind != 'STAFF_OBSERVATION' or not isinstance(value, dict):
        return False
    if value.get('status') in {'UNKNOWN', 'REQUESTED', 'PLANNED', 'MENTIONED'}:
        return False
    return value.get('staff_reported') is True or value.get('staff_attestation') == 'EXPLICIT_STAFF_CHECK'


def money_rollup(facts):
    events = {}
    for fact in facts:
        if fact.get('status') in {'REJECTED', 'SUPERSEDED'} or fact.get('semantic_key', fact.get('field')) != 'transfer.actual.amount':
            continue
        value = fact.get('value_json', fact.get('value')) or {}
        if not isinstance(value, dict) or not isinstance(value.get('amount_krw'), int):
            continue
        if value.get('amount_scope', 'EVENT') != 'EVENT':
            continue
        key = value.get('event_id') or fact.get('fact_id')
        events[key] = value
    outgoing = sum(v['amount_krw'] for v in events.values() if v.get('direction') in {'OUT', 'TRANSFER_OUT'})
    returned = sum(v['amount_krw'] for v in events.values() if v.get('direction') in {'IN', 'RETURN_IN'})
    return {'event_count': len(events), 'reported_outgoing_krw': outgoing,
            'reported_returned_krw': returned, 'reported_net_krw': outgoing - returned,
            'basis': 'CURRENT_REPORTED_EVENTS_NOT_BANK_LEDGER'}
