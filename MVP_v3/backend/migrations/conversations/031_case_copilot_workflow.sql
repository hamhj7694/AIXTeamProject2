-- Additive CaseCopilot persistence. Existing messages and task history are retained.
ALTER TABLE messages ADD COLUMN ai_metadata_json JSON NULL;
ALTER TABLE case_tasks DROP CHECK chk_case_task_source;
ALTER TABLE case_tasks ADD CONSTRAINT chk_case_task_source
    CHECK (source IN ('STAFF_CREATED','AI_SUGGESTION_ACCEPTED','SYSTEM_REQUIRED','AI_RECOMMENDED'));

CREATE TABLE case_copilot_jobs (
    job_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL,
    dedupe_key VARCHAR(100) NOT NULL,
    trigger_kind VARCHAR(24) NOT NULL,
    source_revision BIGINT NOT NULL,
    actor_user_id VARCHAR(64) NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'PENDING',
    attempts INT NOT NULL DEFAULT 0,
    lease_token VARCHAR(64) NULL,
    lease_until DATETIME(6) NULL,
    next_attempt_at DATETIME(6) NULL,
    result_message_id VARCHAR(64) NULL,
    error_code VARCHAR(100) NULL,
    created_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL,
    UNIQUE KEY uq_copilot_job_request (case_id, dedupe_key),
    INDEX idx_copilot_jobs_retry (status, next_attempt_at),
    CONSTRAINT fk_copilot_job_case FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE,
    CONSTRAINT chk_copilot_job_status CHECK (status IN ('PENDING','PROCESSING','COMPLETED','FAILED','SUPERSEDED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
