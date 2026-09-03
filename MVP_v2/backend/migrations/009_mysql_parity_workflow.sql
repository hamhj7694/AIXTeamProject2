-- MySQL parity additions for the latest MVP_v2 Repository/Public API.
-- Run after migrations 001-008.

ALTER TABLE cases
    ADD COLUMN victim_transfer_status VARCHAR(30) NULL,
    ADD COLUMN actual_loss_amount_krw BIGINT NULL,
    ADD COLUMN deleted_at DATETIME(6) NULL;

ALTER TABLE messages
    ADD COLUMN actor_user_id VARCHAR(64) NULL,
    ADD COLUMN actor_display_name VARCHAR(80) NULL,
    ADD COLUMN actor_role VARCHAR(64) NULL,
    ADD COLUMN visibility VARCHAR(32) NOT NULL DEFAULT 'CUSTOMER',
    ADD COLUMN message_kind VARCHAR(32) NOT NULL DEFAULT 'CHAT',
    ADD COLUMN private_owner_user_id VARCHAR(64) NULL,
    ADD COLUMN attachments_json JSON NULL;

ALTER TABLE verification_tasks
    ADD COLUMN result_summary TEXT NULL,
    ADD COLUMN evidence_url VARCHAR(2000) NULL,
    ADD COLUMN verified_by VARCHAR(80) NULL,
    ADD COLUMN rag_source VARCHAR(255) NULL,
    ADD COLUMN customer_visible BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS attachments (
    attachment_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    original_name VARCHAR(255) NOT NULL,
    mime_type VARCHAR(255) NOT NULL,
    size_bytes BIGINT NOT NULL,
    sha256 CHAR(64) NOT NULL,
    uploaded_by VARCHAR(64) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'UPLOADED',
    ai_readable BOOLEAN NOT NULL DEFAULT TRUE,
    storage_key VARCHAR(500) NULL,
    message_id VARCHAR(64) NULL,
    created_at DATETIME(6) NOT NULL,
    INDEX idx_attachments_case (case_id, created_at),
    CONSTRAINT fk_attachments_case FOREIGN KEY (case_id) REFERENCES cases(case_id),
    CONSTRAINT fk_attachments_message FOREIGN KEY (message_id) REFERENCES messages(message_id)
);

CREATE TABLE IF NOT EXISTS customer_questions (
    question_id VARCHAR(100) PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    source VARCHAR(32) NOT NULL,
    target_field VARCHAR(100) NOT NULL,
    question_text TEXT NOT NULL,
    reason TEXT NOT NULL,
    priority VARCHAR(2) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
    sequence INT NOT NULL,
    requested_by VARCHAR(80) NULL,
    asked_at DATETIME(6) NULL,
    answered_at DATETIME(6) NULL,
    options_json JSON NOT NULL,
    question_message_id VARCHAR(64) NULL,
    answer_message_id VARCHAR(64) NULL,
    created_at DATETIME(6) NOT NULL,
    INDEX idx_customer_questions_case (case_id, sequence),
    CONSTRAINT fk_customer_questions_case FOREIGN KEY (case_id) REFERENCES cases(case_id)
);

CREATE TABLE IF NOT EXISTS case_facts (
    fact_id VARCHAR(100) PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    value TEXT NOT NULL,
    source VARCHAR(32) NOT NULL,
    status VARCHAR(16) NOT NULL,
    confidence DECIMAL(5,4) NOT NULL,
    evidence_message_id VARCHAR(64) NULL,
    confirmed_by VARCHAR(80) NULL,
    confirmed_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL,
    INDEX idx_case_facts_case (case_id, field_name),
    CONSTRAINT fk_case_facts_case FOREIGN KEY (case_id) REFERENCES cases(case_id)
);

CREATE TABLE IF NOT EXISTS personal_notes (
    note_id VARCHAR(100) PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    author_id VARCHAR(80) NOT NULL,
    content TEXT NOT NULL,
    visibility VARCHAR(32) NOT NULL DEFAULT 'PRIVATE_TO_AUTHOR',
    created_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL,
    INDEX idx_personal_notes_author (case_id, author_id, updated_at),
    CONSTRAINT fk_personal_notes_case FOREIGN KEY (case_id) REFERENCES cases(case_id)
);
