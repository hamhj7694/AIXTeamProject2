CREATE TABLE IF NOT EXISTS verification_tasks (
    verification_task_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    claim TEXT NOT NULL,
    target VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    version INT NOT NULL DEFAULT 1,
    created_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL,
    INDEX idx_verification_tasks_case (case_id, created_at),
    CONSTRAINT fk_verification_tasks_case FOREIGN KEY (case_id) REFERENCES cases(case_id)
);

CREATE TABLE IF NOT EXISTS actions (
    action_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    action_type VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'REQUESTED',
    actor_type VARCHAR(32) NOT NULL,
    note TEXT NOT NULL,
    created_at DATETIME(6) NOT NULL,
    INDEX idx_actions_case_cursor (case_id, created_at, action_id),
    CONSTRAINT fk_actions_case FOREIGN KEY (case_id) REFERENCES cases(case_id)
);
