-- Open-world extension storage for privacy-safe observations not yet mapped to a Fact.
-- Additive only: existing Context v2 tables and contracts remain unchanged.
CREATE TABLE IF NOT EXISTS case_context_observations (
    observation_id VARCHAR(100) NOT NULL,
    case_id VARCHAR(32) NOT NULL,
    observation_type VARCHAR(80) NOT NULL,
    payload_json JSON NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'UNMAPPED',
    created_by VARCHAR(64) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (case_id, observation_id),
    INDEX idx_context_observations_review (case_id, status, created_at),
    CONSTRAINT fk_context_observations_case FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE,
    CONSTRAINT chk_context_observations_status CHECK (status IN ('UNMAPPED','REVIEWED','MAPPED','DISMISSED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
