EVENT_FAMILIES = ["IMPERSONATION", "PSY_STRATEGY", "ACTION_REQUEST", "MONEY_MOVEMENT", "AMOUNT"]
IMPERSONATION_GROUPS = [
    "PUBLIC_AGENCY", "FINANCIAL_INSTITUTION", "FAMILY", "ACQUAINTANCE",
    "TELECOM_COMPANY", "DELIVERY_LOGISTICS", "OTHER",
]

PSY_SLUG = {
    "AUTHORITY": "authority", "FEAR": "fear", "URGENCY": "urgency",
    "LEGITIMACY": "legitimacy", "INFO_EXTRACTION": "info_extraction",
    "ISOLATION": "isolation", "MONEY_REQUEST": "money_request_strategy",
    "BENEFIT": "benefit", "RESISTANCE_HANDLING": "resistance_handling",
    "BEHAVIOR_CONTROL": "behavior_control",
}
ACTION_SLUG = {
    "SENSITIVE_INFO": "sensitive_info", "AUTH_INFO": "auth_info",
    "DEVICE_CONTROL": "device_control", "CONTACT_RESTRICTION": "contact_restriction",
    "CARD_HANDOVER": "card_handover", "ACCOUNT_RENTAL": "account_rental",
    "OTHER_HIGH_RISK": "other_high_risk_action",
}
MONEY_SLUG = {
    "TRANSFER": "transfer", "WITHDRAWAL": "withdrawal", "CASH_HANDOFF": "cash_handoff",
    "FEE_PAYMENT": "fee_payment", "REPAYMENT": "repayment",
    "OTHER_MONEY_MOVEMENT": "other_money_movement",
}
IMP_GROUP_SLUG = {
    "PUBLIC_AGENCY": "public", "FINANCIAL_INSTITUTION": "financial", "FAMILY": "family",
    "ACQUAINTANCE": "acquaintance", "TELECOM_COMPANY": "telecom",
    "DELIVERY_LOGISTICS": "delivery_logistics", "OTHER": "other",
}
IMP_SUBTYPE_SLUG = {
    "PROSECUTION": "prosecution", "POLICE": "police", "FSS": "fss", "COURT": "court",
    "POST_OFFICE": "post_office", "GOVERNMENT_OTHER": "government_other", "BANK": "bank",
    "CARD_COMPANY": "card_company", "LOAN_COMPANY": "loan_company",
    "CAPITAL_COMPANY": "capital_company", "SAVINGS_BANK": "savings_bank",
    "FINANCIAL_OTHER": "financial_other", "FAMILY": "family_subtype",
    "ACQUAINTANCE": "acquaintance_subtype", "TELECOM": "telecom_subtype",
    "DELIVERY": "delivery_subtype", "OTHER": "other_subtype",
}

EVENT_OUTPUT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"events": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "properties": {
            "event_family": {"type": "string", "enum": EVENT_FAMILIES},
            "subtype": {"type": ["string", "null"]},
            "impersonation_group": {"type": ["string", "null"], "enum": IMPERSONATION_GROUPS + [None]},
            "evidence_turn_id": {"type": "integer"}, "evidence_text": {"type": "string"},
            "amount_krw": {"type": ["number", "null"]}, "amount_context": {"type": ["string", "null"]},
            "is_requested": {"type": ["boolean", "null"]},
        },
        "required": ["event_family", "subtype", "impersonation_group", "evidence_turn_id", "evidence_text", "amount_krw", "amount_context", "is_requested"],
    }}},
    "required": ["events"],
}

SYSTEM_INSTRUCTION = """
금융 통화 텍스트의 현재 TARGET 문장에서 보이스피싱 위험 단서를 원자 Event로만 추출한다.
evidence_turn_id는 TARGET 번호와 같아야 하고 evidence_text는 TARGET 원문의 연속 구절이어야 한다.
근거가 애매하면 Event를 만들지 않는다. NORMAL/PHISHING, 점수, 최종 판단은 출력하지 않는다.
허용 subtype은 다음과 같다.
IMPERSONATION: PROSECUTION, POLICE, FSS, COURT, POST_OFFICE, GOVERNMENT_OTHER, BANK, CARD_COMPANY, LOAN_COMPANY, CAPITAL_COMPANY, SAVINGS_BANK, FINANCIAL_OTHER, FAMILY, ACQUAINTANCE, TELECOM, DELIVERY, OTHER
PSY_STRATEGY: AUTHORITY, FEAR, URGENCY, LEGITIMACY, INFO_EXTRACTION, ISOLATION, MONEY_REQUEST, BENEFIT, RESISTANCE_HANDLING, BEHAVIOR_CONTROL
ACTION_REQUEST: SENSITIVE_INFO, AUTH_INFO, DEVICE_CONTROL, CONTACT_RESTRICTION, CARD_HANDOVER, ACCOUNT_RENTAL, OTHER_HIGH_RISK
MONEY_MOVEMENT: TRANSFER, WITHDRAWAL, CASH_HANDOFF, FEE_PAYMENT, REPAYMENT, OTHER_MONEY_MOVEMENT
""".strip()
