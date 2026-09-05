-- Durable semantic revision and single-flight projection state.
-- UI preferences, presence, bookmarks, private notes and context wording
-- overlays deliberately do not advance this revision.
ALTER TABLE cases
    ADD COLUMN context_revision BIGINT NOT NULL DEFAULT 1 AFTER version;

CREATE TABLE IF NOT EXISTS case_context_projections (
    case_id VARCHAR(32) PRIMARY KEY,
    generation_status VARCHAR(16) NOT NULL DEFAULT 'EMPTY',
    generating_revision BIGINT NULL,
    lease_token VARCHAR(64) NULL,
    lease_expires_at DATETIME(6) NULL,
    last_success_revision BIGINT NULL,
    last_success_payload JSON NULL,
    schema_version VARCHAR(32) NOT NULL DEFAULT 'case-support.v1',
    model_version VARCHAR(100) NULL,
    prompt_version VARCHAR(100) NULL,
    last_error VARCHAR(500) NULL,
    generated_at DATETIME(6) NULL,
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_context_projection_case FOREIGN KEY (case_id) REFERENCES cases(case_id)
);

-- Direct changes to fields used by the Case Context projection.
CREATE TRIGGER trg_cases_context_revision_update
BEFORE UPDATE ON cases FOR EACH ROW
SET NEW.context_revision = GREATEST(
    NEW.context_revision,
    OLD.context_revision + IF(
        NOT (OLD.mode <=> NEW.mode)
        OR NOT (OLD.status <=> NEW.status)
        OR NOT (OLD.diagnosis_json <=> NEW.diagnosis_json)
        OR NOT (OLD.victim_transfer_status <=> NEW.victim_transfer_status)
        OR NOT (OLD.actual_loss_amount_krw <=> NEW.actual_loss_amount_krw),
        1, 0
    )
);

CREATE TRIGGER trg_messages_context_revision_insert
AFTER INSERT ON messages FOR EACH ROW
UPDATE cases SET context_revision=context_revision+1 WHERE case_id=NEW.case_id;

CREATE TRIGGER trg_messages_context_revision_delete
AFTER DELETE ON messages FOR EACH ROW
UPDATE cases SET context_revision=context_revision+1 WHERE case_id=OLD.case_id;

CREATE TRIGGER trg_questions_context_revision_insert
AFTER INSERT ON customer_questions FOR EACH ROW
UPDATE cases SET context_revision=context_revision+1 WHERE case_id=NEW.case_id;

CREATE TRIGGER trg_questions_context_revision_update
AFTER UPDATE ON customer_questions FOR EACH ROW
UPDATE cases SET context_revision=context_revision + IF(
    NOT (OLD.target_field <=> NEW.target_field)
    OR NOT (OLD.question_text <=> NEW.question_text)
    OR NOT (OLD.reason <=> NEW.reason)
    OR NOT (OLD.priority <=> NEW.priority)
    OR NOT (OLD.status <=> NEW.status)
    OR NOT (OLD.answer_text <=> NEW.answer_text), 1, 0
) WHERE case_id=NEW.case_id;

CREATE TRIGGER trg_questions_context_revision_delete
AFTER DELETE ON customer_questions FOR EACH ROW
UPDATE cases SET context_revision=context_revision+1 WHERE case_id=OLD.case_id;

CREATE TRIGGER trg_facts_context_revision_insert
AFTER INSERT ON case_facts FOR EACH ROW
UPDATE cases SET context_revision=context_revision+1 WHERE case_id=NEW.case_id;

CREATE TRIGGER trg_facts_context_revision_update
AFTER UPDATE ON case_facts FOR EACH ROW
UPDATE cases SET context_revision=context_revision + IF(
    NOT (OLD.field_name <=> NEW.field_name)
    OR NOT (OLD.value <=> NEW.value)
    OR NOT (OLD.source <=> NEW.source)
    OR NOT (OLD.status <=> NEW.status), 1, 0
) WHERE case_id=NEW.case_id;

CREATE TRIGGER trg_facts_context_revision_delete
AFTER DELETE ON case_facts FOR EACH ROW
UPDATE cases SET context_revision=context_revision+1 WHERE case_id=OLD.case_id;

CREATE TRIGGER trg_verifications_context_revision_insert
AFTER INSERT ON verification_tasks FOR EACH ROW
UPDATE cases SET context_revision=context_revision+1 WHERE case_id=NEW.case_id;

CREATE TRIGGER trg_verifications_context_revision_update
AFTER UPDATE ON verification_tasks FOR EACH ROW
UPDATE cases SET context_revision=context_revision + IF(
    NOT (OLD.claim <=> NEW.claim)
    OR NOT (OLD.target <=> NEW.target)
    OR NOT (OLD.status <=> NEW.status)
    OR NOT (OLD.result_summary <=> NEW.result_summary), 1, 0
) WHERE case_id=NEW.case_id;

CREATE TRIGGER trg_verifications_context_revision_delete
AFTER DELETE ON verification_tasks FOR EACH ROW
UPDATE cases SET context_revision=context_revision+1 WHERE case_id=OLD.case_id;

CREATE TRIGGER trg_actions_context_revision_insert
AFTER INSERT ON actions FOR EACH ROW
UPDATE cases SET context_revision=context_revision+1 WHERE case_id=NEW.case_id;

CREATE TRIGGER trg_actions_context_revision_update
AFTER UPDATE ON actions FOR EACH ROW
UPDATE cases SET context_revision=context_revision + IF(
    NOT (OLD.action_type <=> NEW.action_type)
    OR NOT (OLD.status <=> NEW.status)
    OR NOT (OLD.note <=> NEW.note), 1, 0
) WHERE case_id=NEW.case_id;

CREATE TRIGGER trg_actions_context_revision_delete
AFTER DELETE ON actions FOR EACH ROW
UPDATE cases SET context_revision=context_revision+1 WHERE case_id=OLD.case_id;
