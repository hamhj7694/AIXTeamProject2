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

ATOM_CLASSES = [
    "IDENTITY_CLAIM", "ORGANIZATION_CLAIM", "ROLE_CLAIM", "STATE_CLAIM",
    "EVENT_CLAIM", "ACTION_REQUEST", "ACTION_INSTRUCTION", "PROHIBITION",
    "QUESTION", "WARNING", "THREAT", "PROMISE", "JUSTIFICATION", "CONDITION",
    "OBSERVED_ACTION", "REPORTED_ACTION", "CUSTOMER_RESPONSE", "DISCLOSURE_REQUEST",
    "SECRECY_REQUEST", "COMMUNICATION_CONTROL", "FINANCIAL_ACTION",
]
ENTITY_CODES = [
    "CALLER", "CUSTOMER", "CUSTOMER_ACCOUNT", "EXTERNAL_ACCOUNT",
    "CLAIMED_SAFE_ACCOUNT", "PROSECUTION_SERVICE", "POLICE_SERVICE",
    "FINANCIAL_INSTITUTION", "FAMILY", "THIRD_PARTY", "UNKNOWN",
]
CLAIMED_ORGANIZATION_CODES = [
    "PROSECUTION_SERVICE", "POLICE_SERVICE", "FINANCIAL_SUPERVISORY_SERVICE",
    "COURT", "BANK", "CARD_COMPANY", "LOAN_COMPANY", "TELECOM_COMPANY",
    "DELIVERY_COMPANY", "GOVERNMENT_AGENCY", "OTHER", "UNKNOWN",
]
CLAIMED_ROLE_CODES = [
    "INVESTIGATOR", "PROSECUTOR", "POLICE_OFFICER", "BANK_EMPLOYEE",
    "FSS_EMPLOYEE", "COURT_EMPLOYEE", "LOAN_COUNSELOR", "DELIVERY_AGENT",
    "FAMILY_MEMBER", "ACQUAINTANCE", "OTHER", "UNKNOWN",
]
LEXICAL_CUE_CODES = [
    "PROSECUTION", "POLICE", "FINANCIAL_AUTHORITY", "COURT", "BANK",
    "INVESTIGATOR_ROLE", "PROSECUTOR_ROLE", "POLICE_ROLE", "BANK_ROLE",
    "ACCOUNT_CRIME_LINK", "CRIME_INVOLVEMENT", "ARREST", "ASSET_FREEZE",
    "SAFE_ACCOUNT", "TRANSFER", "WITHDRAWAL", "ALL_FUNDS", "EXACT_AMOUNT",
    "OTP", "PASSWORD", "PIN", "CARD_CVC", "APP_INSTALL", "URL_OPEN",
    "SCREEN_SHARE", "IMMEDIATE", "DEADLINE", "NO_END_CALL", "NO_FAMILY",
    "NO_BANK_CONTACT", "NO_REPORTING", "NO_SEARCH", "KEEP_SECRET",
]
PREDICATE_CODES = [
    "CLAIMS_IDENTITY", "CLAIMS_ORGANIZATION", "CLAIMS_ROLE",
    "CLAIMS_ACCOUNT_INVOLVEMENT", "CLAIMS_CRIME_INVOLVEMENT",
    "TRANSFER_FUNDS", "WITHDRAW_CASH", "DISCLOSE_OTP", "DISCLOSE_PASSWORD",
    "PROVIDE_CARD_INFO", "INSTALL_APP", "OPEN_URL", "SHARE_SCREEN",
    "MAINTAIN_CALL", "END_CALL", "KEEP_SECRET", "AVOID_REPORTING",
    "AVOID_EXTERNAL_CONTACT", "THREATEN_ARREST", "THREATEN_ASSET_FREEZE",
    "JUSTIFY_ASSET_PROTECTION", "PROMISE_RETURN", "OTHER",
]


def _nullable_enum(values: list[str]) -> dict[str, object]:
    return {"type": ["string", "null"], "enum": [*values, None]}


SEMANTIC_ATOM_OUTPUT_PROPERTIES = {
    "atom_class": {"type": "string", "enum": ATOM_CLASSES},
    "speaker": {"type": "string", "enum": ["CALLER", "CUSTOMER", "BANK_STAFF", "SYSTEM", "UNKNOWN"]},
    "subject": _nullable_enum(ENTITY_CODES),
    "predicate": {"type": "string", "enum": PREDICATE_CODES},
    "actor": _nullable_enum(ENTITY_CODES), "target": _nullable_enum(ENTITY_CODES),
    "object": _nullable_enum(ENTITY_CODES),
    "destination": _nullable_enum(["CLAIMED_SAFE_ACCOUNT", "EXTERNAL_ACCOUNT", "CUSTOMER_ACCOUNT", "UNKNOWN"]),
    "action_state": _nullable_enum(["MENTIONED", "REQUESTED", "INSTRUCTED", "PLANNED", "ATTEMPTED", "REPORTED_ACTION", "VERIFIED", "COMPLETED", "FAILED", "CANCELLED", "DENIED", "UNKNOWN"]),
    "modality": _nullable_enum(["ASSERTION", "REQUEST", "DIRECTIVE", "QUESTION", "WARNING", "CONDITIONAL", "PROMISE", "UNKNOWN"]),
    "polarity": {"type": "string", "enum": ["POSITIVE", "NEGATIVE", "UNKNOWN"]},
    "claim_status": {"type": "string", "enum": ["CALLER_CLAIM", "CUSTOMER_REPORTED", "STAFF_REPORTED", "UNVERIFIED", "VERIFIED", "UNKNOWN"]},
    "lexical_cues": {
        "type": "array", "items": {"type": "string", "enum": LEXICAL_CUE_CODES},
        "description": "Privacy-safe normalized cue codes only; never source words or quotations.",
    },
    "speech_act": _nullable_enum(["ASSERTION", "REQUEST", "INSTRUCTION", "PROHIBITION", "QUESTION", "WARNING", "THREAT", "PROMISE", "JUSTIFICATION", "CONDITION", "UNKNOWN"]),
    "directive_strength": _nullable_enum(["WEAK", "MEDIUM", "STRONG", "UNKNOWN"]),
    "obligation": _nullable_enum(["OPTIONAL", "SUGGESTED", "REQUIRED", "UNKNOWN"]),
    "urgency": _nullable_enum(["NONE", "IMMEDIATE", "TODAY", "WITHIN_30_MINUTES", "BEFORE_CALL_END", "BEFORE_BANK_CLOSE", "UNKNOWN_DEADLINE"]),
    "authority_pressure": _nullable_enum(["NONE", "LOW", "MEDIUM", "HIGH", "UNKNOWN"]),
    "fear_pressure": _nullable_enum(["NONE", "LOW", "MEDIUM", "HIGH", "UNKNOWN"]),
    "secrecy_pressure": _nullable_enum(["NONE", "LOW", "MEDIUM", "HIGH", "UNKNOWN"]),
    "isolation_pressure": _nullable_enum(["NONE", "LOW", "MEDIUM", "HIGH", "UNKNOWN"]),
    "financial_pressure": _nullable_enum(["NONE", "LOW", "MEDIUM", "HIGH", "UNKNOWN"]),
    "repetition_pressure": _nullable_enum(["NONE", "LOW", "MEDIUM", "HIGH", "UNKNOWN"]),
    "threat_type": _nullable_enum(["ARREST_THREAT", "ASSET_FREEZE_THREAT", "LEGAL_ACTION_THREAT", "FINANCIAL_LOSS_THREAT", "ACCOUNT_SUSPENSION_THREAT", "FAMILY_HARM_THREAT", "INVESTIGATION_ESCALATION_THREAT", "UNKNOWN"]),
    "communication_control": _nullable_enum(["NO_END_CALL", "NO_EXTERNAL_CONTACT", "NO_REPORTING", "NO_FAMILY_DISCLOSURE", "NO_BANK_CONTACT", "NO_SEARCH", "KEEP_SECRET", "UNKNOWN"]),
    "auth_secret_type": _nullable_enum(["OTP", "SECURITY_CODE", "PASSWORD", "PIN", "CARD_CVC", "CERTIFICATE_SECRET", "UNKNOWN"]),
    "amount_scope": _nullable_enum(["ALL_FUNDS", "PARTIAL_FUNDS", "HALF", "REMAINING_BALANCE", "MAXIMUM_AVAILABLE", "EXPLICIT_AMOUNT", "UNKNOWN"]),
    "amount_value_krw": {"type": ["number", "null"], "minimum": 0},
    "claimed_organization": _nullable_enum(CLAIMED_ORGANIZATION_CODES),
    "claimed_role": _nullable_enum(CLAIMED_ROLE_CODES),
    "claimed_organization_name": {"type": ["string", "null"], "maxLength": 160},
    "claimed_branch_name": {"type": ["string", "null"], "maxLength": 160},
    "claimed_person_name": {"type": ["string", "null"], "maxLength": 100},
    "claimed_role_name": {"type": ["string", "null"], "maxLength": 160},
    "claimed_relationship": {"type": ["string", "null"], "maxLength": 100},
    "claimed_purpose": _nullable_enum(["ASSET_PROTECTION", "INVESTIGATION", "VERIFICATION", "FEE_PAYMENT", "REPAYMENT", "UNKNOWN"]),
    "speaker_role": _nullable_enum(["SUSPECTED_PARTY", "CUSTOMER", "BANK_STAFF", "SYSTEM", "UNKNOWN"]),
    "actor_role": _nullable_enum(["SUSPECTED_PARTY", "CUSTOMER", "BANK_STAFF", "SYSTEM", "UNKNOWN"]),
    "target_role": _nullable_enum(["SUSPECTED_PARTY", "CUSTOMER", "BANK_STAFF", "SYSTEM", "UNKNOWN"]),
    "reported_by_role": _nullable_enum(["SUSPECTED_PARTY", "CUSTOMER", "BANK_STAFF", "SYSTEM", "UNKNOWN"]),
    "speaker_confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
    "attribution_confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
    "vocative_target": {"type": ["string", "null"], "maxLength": 100},
    "deadline_at": {"type": ["string", "null"], "maxLength": 64},
    "relative_deadline_minutes": {"type": ["integer", "null"], "minimum": 0, "maximum": 525600},
    "mention_order": {"type": ["integer", "null"], "minimum": 1},
    "occurrence_count": {"type": "integer", "minimum": 1},
}

EVENT_OUTPUT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "events": {"type": "array", "items": {
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
        }},
        "semantic_atoms": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": SEMANTIC_ATOM_OUTPUT_PROPERTIES,
            "required": list(SEMANTIC_ATOM_OUTPUT_PROPERTIES),
        }},
    },
    "required": ["events", "semantic_atoms"],
}

SYSTEM_INSTRUCTION = """
금융 통화 텍스트의 현재 TARGET 문장에서 보이스피싱 위험 단서를 원자 Event로만 추출한다.
evidence_turn_id는 TARGET 번호와 같아야 하고 evidence_text는 TARGET 원문의 연속 구절이어야 한다.
입력은 고객이 은행에 피해 사실을 신고한 문서가 아니라, 보이스피싱 의심 인물과 고객이
실제로 통화하는 대화의 한 턴이다. 입력 앞의 [SPEAKER_CUSTOMER],
[SPEAKER_SUSPECTED_PARTY] 표시는 온디바이스 발화자 metadata이므로 최우선으로 따른다.
발화자 표기가 없으면 UNKNOWN으로 두며, "고객님" 같은 호칭이나 문장 속 고객 언급만으로
그 턴의 발화자를 CUSTOMER로 바꾸지 않는다. 의심 인물이 말한 주장·요구·압박은 고객의
신고나 진술이 아니라 SUSPECTED_PARTY의 발화로 기록한다.
근거가 애매하면 Event를 만들지 않는다. NORMAL/PHISHING, 점수, 최종 판단은 출력하지 않는다.
허용 subtype은 다음과 같다.
IMPERSONATION: PROSECUTION, POLICE, FSS, COURT, POST_OFFICE, GOVERNMENT_OTHER, BANK, CARD_COMPANY, LOAN_COMPANY, CAPITAL_COMPANY, SAVINGS_BANK, FINANCIAL_OTHER, FAMILY, ACQUAINTANCE, TELECOM, DELIVERY, OTHER
PSY_STRATEGY: AUTHORITY, FEAR, URGENCY, LEGITIMACY, INFO_EXTRACTION, ISOLATION, MONEY_REQUEST, BENEFIT, RESISTANCE_HANDLING, BEHAVIOR_CONTROL
ACTION_REQUEST: SENSITIVE_INFO, AUTH_INFO, DEVICE_CONTROL, CONTACT_RESTRICTION, CARD_HANDOVER, ACCOUNT_RENTAL, OTHER_HIGH_RISK
MONEY_MOVEMENT: TRANSFER, WITHDRAWAL, CASH_HANDOFF, FEE_PAYMENT, REPAYMENT, OTHER_MONEY_MOVEMENT
""".strip()

SEMANTIC_ATOM_INSTRUCTION = """
Populate the top-level semantic_atoms array with every independently
verifiable meaning unit in the target turn. Split organization claims, role
claims, incident claims, requested actions, authentication-secret requests,
threats, urgency, secrecy and communication control into separate atoms.
The source is a live call between a suspected phishing person and a customer,
not a customer report to the bank. If the input metadata says
SPEAKER_SUSPECTED_PARTY, set speaker_role and actor_role to SUSPECTED_PARTY for
that person's claims, requests, and pressure tactics, with target_role CUSTOMER.
If it says SPEAKER_CUSTOMER, only customer actions, answers, denials, or
reported experiences belong to CUSTOMER. A vocative such as "고객님" or
"엄마" never changes the speaker. Never write "고객이 ... 주장함" for a claim
made by the suspected person.
Never copy the source sentence, quotation, phone number, account number, OTP,
or other sensitive literal into an atom. Keep claim_status and action_state
explicit; distinguish REQUESTED, INSTRUCTED and COMPLETED. Use UNKNOWN or null
when the target does not support a concrete value. Use only the uppercase codes
allowed by the JSON schema. Never emit the string "null"; emit JSON null.
Represent urgency, communication restrictions, amount scope and claimed
purpose in their dedicated fields rather than hiding them in lexical_cues.
Use the most specific authentication type supported by the target: OTP,
SECURITY_CODE, PASSWORD, PIN, CARD_CVC or CERTIFICATE_SECRET; do not collapse
these into a generic authentication request. Preserve pressure dimensions
independently: urgency is a deadline, obligation is requiredness,
authority_pressure is claimed institutional power, and fear_pressure is a
threat or feared consequence. Euphemisms such as "safe account", "protective
transfer" or "verification fee" must be normalized into dedicated purpose and
destination codes, while the original wording must not be copied.
One atom must contain exactly one primary predicate. A claimed organization and
a claimed role are always separate atoms. Every communication restriction is
a separate COMMUNICATION_CONTROL atom: "do not end the call" and "do not tell
family" must never be merged. Never attach communication_control to a transfer
atom. Put ALL_FUNDS, REMAINING_BALANCE or an explicit KRW amount on the relevant
financial atom. Claim atoms must have action_state null. Requested, instructed,
attempted and completed actions are different states and must not be inferred
from one another. "ask/request" means ACTION_REQUEST + REQUESTED; "tell/order/
instruct/require" means ACTION_INSTRUCTION + INSTRUCTED; only an action reported
as already performed means COMPLETED. Preserve denial with NEGATIVE + DENIED,
and preserve hypothetical or conditional actions with CONDITIONAL rather than
turning them into facts. Repeated pressure may raise repetition_pressure but
must not change an unperformed action to COMPLETED. A phrase such as "prosecution investigator ... do not end the
call or tell family ... immediately transfer all funds to a safe account"
therefore needs at least five atoms: organization claim, role claim, no-end-call
control, no-family-disclosure control, and transfer instruction.
Preserve exact non-sensitive names and labels in their dedicated fields:
claimed_organization_name, claimed_branch_name, claimed_person_name and
claimed_role_name. Do not generalize 서울지검, a named bank branch, police
station, court, prosecutor's office, or a stated person name when it is present.
Record claimed_relationship and vocative_target separately. In a sentence like
"엄마, 나 스마트폰 고장 났어", 엄마 is the addressee/vocative_target;
the speaker remains SUSPECTED_PARTY and the claimed relationship is CHILD.
Populate speaker_role, actor_role, target_role and reported_by_role explicitly.
The person who reports a claim is not necessarily its actor. Preserve an exact
deadline and relative remaining minutes when both are available, plus occurrence
count and mention order. These normalized entity fields may contain only the
specific short name/title/relationship, never a whole source sentence.
""".strip()
