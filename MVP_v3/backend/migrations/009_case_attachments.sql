CREATE TABLE IF NOT EXISTS case_attachments (
    attachment_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    original_name VARCHAR(160) NOT NULL,
    stored_name VARCHAR(80) NOT NULL,
    storage_path VARCHAR(512) NOT NULL,
    mime_type VARCHAR(120) NOT NULL,
    size_bytes BIGINT UNSIGNED NOT NULL,
    sha256 CHAR(64) NOT NULL,
    uploaded_by VARCHAR(80) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'UPLOADED',
    visibility VARCHAR(32) NOT NULL DEFAULT 'CUSTOMER',
    ai_readable BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME(6) NOT NULL,
    INDEX idx_case_attachments_case_created (case_id, created_at, attachment_id),
    INDEX idx_case_attachments_sha256 (sha256),
    CONSTRAINT fk_case_attachments_case FOREIGN KEY (case_id) REFERENCES cases(case_id)
);

CREATE TABLE IF NOT EXISTS message_attachments (
    message_id VARCHAR(64) NOT NULL,
    attachment_id VARCHAR(64) NOT NULL,
    attached_at DATETIME(6) NOT NULL,
    PRIMARY KEY (message_id, attachment_id),
    CONSTRAINT fk_message_attachments_message FOREIGN KEY (message_id) REFERENCES messages(message_id),
    CONSTRAINT fk_message_attachments_attachment FOREIGN KEY (attachment_id) REFERENCES case_attachments(attachment_id)
);
