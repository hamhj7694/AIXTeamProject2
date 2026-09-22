-- Copy the two explicitly supported legacy fact fields into the V2 authority.
-- This migration is idempotent through the deterministic client_request_id.
-- No legacy rows are deleted here; 028 performs the guarded retirement.

INSERT INTO case_context_facts_v2 (
    fact_id, case_id, semantic_key, display_label, value_json, display_value,
    source_kind, status, confidence, evidence_refs_json, visibility,
    confirmed_by, confirmed_at, client_request_id, version, created_at, updated_at
)
SELECT
    CONCAT('legacy-', LEFT(SHA2(CONCAT(cf.case_id, ':', cf.fact_id), 256), 57)),
    cf.case_id,
    CASE cf.field_name
        WHEN 'authentication_information_exposure' THEN 'exposure.authentication_information'
        WHEN 'personal_information_exposure' THEN 'exposure.personal_information'
    END,
    CASE cf.field_name
        WHEN 'authentication_information_exposure' THEN '인증정보 노출 여부'
        WHEN 'personal_information_exposure' THEN '개인정보 노출 여부'
    END,
    JSON_OBJECT('legacy_value', cf.value, 'legacy_field', cf.field_name),
    cf.value,
    CASE cf.source
        WHEN 'AI_EXTRACTED' THEN 'AI_EXTRACTION'
        WHEN 'HUMAN_CONFIRMED' THEN 'STAFF_OBSERVATION'
        WHEN 'VERIFIED' THEN 'OFFICIAL_VERIFICATION'
        WHEN 'UNRESOLVED' THEN 'STAFF_OBSERVATION'
    END,
    CASE cf.status WHEN 'CONFIRMED' THEN 'CONFIRMED' ELSE 'PROPOSED' END,
    cf.confidence,
    CASE
        WHEN cf.evidence_message_id IS NOT NULL AND cf.source_question_id IS NOT NULL THEN JSON_ARRAY(
            JSON_OBJECT('type', 'MESSAGE', 'id', cf.evidence_message_id),
            JSON_OBJECT('type', 'QUESTION_ANSWER', 'id', cf.source_question_id)
        )
        WHEN cf.evidence_message_id IS NOT NULL THEN JSON_ARRAY(JSON_OBJECT('type', 'MESSAGE', 'id', cf.evidence_message_id))
        WHEN cf.source_question_id IS NOT NULL THEN JSON_ARRAY(JSON_OBJECT('type', 'QUESTION_ANSWER', 'id', cf.source_question_id))
        ELSE JSON_ARRAY()
    END,
    'BANK_INTERNAL',
    CASE WHEN cf.status = 'CONFIRMED' THEN cf.confirmed_by ELSE NULL END,
    CASE WHEN cf.status = 'CONFIRMED' THEN cf.confirmed_at ELSE NULL END,
    CONCAT('legacy-case-fact:', cf.fact_id),
    1,
    cf.created_at,
    cf.created_at
FROM case_facts cf
WHERE cf.field_name IN ('authentication_information_exposure', 'personal_information_exposure')
  AND cf.source IN ('AI_EXTRACTED', 'HUMAN_CONFIRMED', 'VERIFIED', 'UNRESOLVED')
ON DUPLICATE KEY UPDATE fact_id = VALUES(fact_id);
