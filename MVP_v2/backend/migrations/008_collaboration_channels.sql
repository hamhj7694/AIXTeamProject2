ALTER TABLE messages
    ADD COLUMN channel VARCHAR(32) NOT NULL DEFAULT 'CUSTOMER' AFTER content,
    ADD COLUMN audience VARCHAR(32) NOT NULL DEFAULT 'CUSTOMER' AFTER channel,
    ADD COLUMN mentions_json TEXT NOT NULL AFTER audience,
    ADD COLUMN reply_to_message_id VARCHAR(64) NULL AFTER mentions_json;

UPDATE messages
SET mentions_json = '[]'
WHERE mentions_json = '';

CREATE TABLE IF NOT EXISTS case_members (
    case_id VARCHAR(32) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    display_name VARCHAR(80) NOT NULL,
    role VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    assigned_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL,
    PRIMARY KEY (case_id, user_id),
    CONSTRAINT fk_case_members_case FOREIGN KEY (case_id) REFERENCES cases(case_id)
);

CREATE TABLE IF NOT EXISTS case_presence (
    case_id VARCHAR(32) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    display_name VARCHAR(80) NOT NULL,
    presence VARCHAR(16) NOT NULL,
    channel VARCHAR(32) NOT NULL,
    last_seen_at DATETIME(6) NOT NULL,
    expires_at DATETIME(6) NOT NULL,
    PRIMARY KEY (case_id, user_id),
    INDEX idx_case_presence_expiry (case_id, expires_at),
    CONSTRAINT fk_case_presence_case FOREIGN KEY (case_id) REFERENCES cases(case_id)
);
