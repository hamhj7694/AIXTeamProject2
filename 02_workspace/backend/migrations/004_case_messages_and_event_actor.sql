CREATE TABLE IF NOT EXISTS messages (
    message_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    actor_type VARCHAR(32) NOT NULL,
    content TEXT NOT NULL,
    client_request_id VARCHAR(100) NULL,
    created_at DATETIME(6) NOT NULL,
    INDEX idx_messages_case_cursor (case_id, created_at, message_id),
    CONSTRAINT fk_messages_case FOREIGN KEY (case_id) REFERENCES cases(case_id)
);

ALTER TABLE case_events
    ADD COLUMN actor_type VARCHAR(32) NOT NULL DEFAULT 'SYSTEM' AFTER event_type;
