-- Context Panel V3 additive persistence. Existing messages/facts/questions are retained.

ALTER TABLE customer_questions
    ADD COLUMN allow_multi_select BOOLEAN NOT NULL DEFAULT FALSE AFTER options_json,
    ADD COLUMN question_version BIGINT NOT NULL DEFAULT 1 AFTER answer_text,
    ADD COLUMN answer_payload_json JSON NULL AFTER question_version,
    ADD COLUMN answer_question_version BIGINT NULL AFTER answer_payload_json;

CREATE TABLE IF NOT EXISTS message_context_extractions (
    extraction_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    message_id VARCHAR(64) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
    attempts INT NOT NULL DEFAULT 0,
    last_error VARCHAR(1000) NULL,
    model_version VARCHAR(100) NULL,
    prompt_version VARCHAR(100) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    completed_at DATETIME(6) NULL,
    UNIQUE KEY uq_message_context_extraction_message (message_id),
    INDEX idx_message_context_extraction_retry (status, attempts, updated_at),
    INDEX idx_message_context_extraction_case (case_id, created_at),
    CONSTRAINT fk_message_context_extraction_case FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE,
    CONSTRAINT fk_message_context_extraction_message FOREIGN KEY (message_id) REFERENCES messages(message_id) ON DELETE CASCADE,
    CONSTRAINT chk_message_context_extraction_status CHECK (status IN ('PENDING','PROCESSING','COMPLETED','FAILED','SKIPPED')),
    CONSTRAINT chk_message_context_extraction_attempts CHECK (attempts BETWEEN 0 AND 3)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TRIGGER IF EXISTS trg_questions_context_revision_update;
CREATE TRIGGER trg_questions_context_revision_update AFTER UPDATE ON customer_questions FOR EACH ROW
UPDATE cases SET context_revision=context_revision+IF(
    NOT (OLD.target_field <=> NEW.target_field) OR NOT (OLD.question_text <=> NEW.question_text)
    OR NOT (OLD.reason <=> NEW.reason) OR NOT (OLD.priority <=> NEW.priority)
    OR NOT (OLD.status <=> NEW.status) OR NOT (OLD.answer_text <=> NEW.answer_text)
    OR NOT (OLD.answer_payload_json <=> NEW.answer_payload_json), 1, 0
) WHERE case_id=NEW.case_id;
