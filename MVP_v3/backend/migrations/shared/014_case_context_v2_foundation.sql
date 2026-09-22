-- Additive Case Context v2 storage foundation.
-- No existing table is renamed, rewritten, or dropped by this migration.

CREATE TABLE IF NOT EXISTS case_context_facts_v2 (
    fact_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    semantic_key VARCHAR(160) COLLATE utf8mb4_bin NOT NULL,
    display_label VARCHAR(255) NOT NULL,
    value_json JSON NOT NULL,
    display_value TEXT NOT NULL,
    source_kind VARCHAR(32) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'PROPOSED',
    confidence DECIMAL(5,4) NULL,
    evidence_refs_json JSON NOT NULL,
    visibility VARCHAR(32) NOT NULL DEFAULT 'BANK_INTERNAL',
    confirmed_by VARCHAR(64) NULL,
    confirmed_at DATETIME(6) NULL,
    rejection_reason VARCHAR(1000) NULL,
    supersedes_fact_id VARCHAR(64) NULL,
    client_request_id VARCHAR(100) NULL,
    version BIGINT NOT NULL DEFAULT 1,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    UNIQUE KEY uq_context_fact_request (case_id, client_request_id),
    INDEX idx_context_facts_case_state (case_id, status, semantic_key),
    CONSTRAINT fk_context_fact_v2_case FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE,
    CONSTRAINT fk_context_fact_v2_supersedes FOREIGN KEY (supersedes_fact_id) REFERENCES case_context_facts_v2(fact_id) ON DELETE SET NULL,
    CONSTRAINT chk_context_fact_status CHECK (status IN ('PROPOSED','CONFIRMED','REJECTED','SUPERSEDED')),
    CONSTRAINT chk_context_fact_source CHECK (source_kind IN ('AI_EXTRACTION','CUSTOMER_STATEMENT','STAFF_OBSERVATION','BANK_RECORD','OFFICIAL_VERIFICATION')),
    CONSTRAINT chk_context_fact_visibility CHECK (visibility IN ('BANK_INTERNAL','CUSTOMER_SHARED')),
    CONSTRAINT chk_context_fact_confidence CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    CONSTRAINT chk_context_fact_confirmed CHECK (status <> 'CONFIRMED' OR (confirmed_by IS NOT NULL AND confirmed_at IS NOT NULL)),
    CONSTRAINT chk_context_fact_rejected CHECK (status <> 'REJECTED' OR rejection_reason IS NOT NULL)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS case_gaps (
    gap_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    semantic_key VARCHAR(160) COLLATE utf8mb4_bin NOT NULL,
    title VARCHAR(300) NOT NULL,
    reason TEXT NOT NULL,
    priority VARCHAR(16) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'OPEN',
    source VARCHAR(24) NOT NULL,
    evidence_refs_json JSON NOT NULL,
    related_question_ids_json JSON NOT NULL,
    related_verification_ids_json JSON NOT NULL,
    resolution_fact_id VARCHAR(64) NULL,
    dismissal_reason VARCHAR(1000) NULL,
    visibility VARCHAR(32) NOT NULL DEFAULT 'BANK_INTERNAL',
    source_revision BIGINT NOT NULL,
    client_request_id VARCHAR(100) NULL,
    version BIGINT NOT NULL DEFAULT 1,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    active_semantic_key VARCHAR(160) COLLATE utf8mb4_bin GENERATED ALWAYS AS (
        CASE WHEN status IN ('OPEN','AWAITING_CUSTOMER','AWAITING_INSTITUTION','STAFF_REVIEW_REQUIRED') THEN semantic_key ELSE NULL END
    ) STORED,
    UNIQUE KEY uq_case_gap_active (case_id, active_semantic_key),
    UNIQUE KEY uq_case_gap_request (case_id, client_request_id),
    INDEX idx_case_gaps_state (case_id, status, priority),
    CONSTRAINT fk_case_gap_case FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE,
    CONSTRAINT fk_case_gap_resolution FOREIGN KEY (resolution_fact_id) REFERENCES case_context_facts_v2(fact_id) ON DELETE RESTRICT,
    CONSTRAINT chk_case_gap_status CHECK (status IN ('OPEN','AWAITING_CUSTOMER','AWAITING_INSTITUTION','STAFF_REVIEW_REQUIRED','RESOLVED','DISMISSED')),
    CONSTRAINT chk_case_gap_priority CHECK (priority IN ('URGENT','HIGH','NORMAL')),
    CONSTRAINT chk_case_gap_source CHECK (source IN ('AI','BANK_STAFF','SYSTEM_RULE')),
    CONSTRAINT chk_case_gap_visibility CHECK (visibility = 'BANK_INTERNAL'),
    CONSTRAINT chk_case_gap_resolved CHECK (status <> 'RESOLVED' OR resolution_fact_id IS NOT NULL),
    CONSTRAINT chk_case_gap_dismissed CHECK (status <> 'DISMISSED' OR dismissal_reason IS NOT NULL)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS case_ai_suggestions (
    suggestion_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    suggestion_type VARCHAR(40) NOT NULL,
    title VARCHAR(300) NOT NULL,
    rationale TEXT NOT NULL,
    priority VARCHAR(16) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'PROPOSED',
    related_gap_ids_json JSON NOT NULL,
    evidence_refs_json JSON NOT NULL,
    dedupe_key VARCHAR(255) COLLATE utf8mb4_bin NOT NULL,
    execution_mode VARCHAR(40) NOT NULL DEFAULT 'HUMAN_REVIEW_REQUIRED',
    source_revision BIGINT NOT NULL,
    model_version VARCHAR(100) NULL,
    prompt_version VARCHAR(100) NULL,
    accepted_task_id VARCHAR(64) NULL,
    reviewed_by VARCHAR(64) NULL,
    reviewed_at DATETIME(6) NULL,
    dismissal_reason VARCHAR(1000) NULL,
    version BIGINT NOT NULL DEFAULT 1,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    active_dedupe_key VARCHAR(255) COLLATE utf8mb4_bin GENERATED ALWAYS AS (
        CASE WHEN status = 'PROPOSED' THEN dedupe_key ELSE NULL END
    ) STORED,
    UNIQUE KEY uq_ai_suggestion_active (case_id, active_dedupe_key),
    INDEX idx_ai_suggestions_state (case_id, status, priority),
    CONSTRAINT fk_ai_suggestion_case FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE,
    CONSTRAINT chk_ai_suggestion_type CHECK (suggestion_type IN ('CUSTOMER_QUESTION','INSTITUTION_VERIFICATION','TRANSACTION_REVIEW','PROTECTIVE_ACTION','DOCUMENT_REQUEST','STAFF_REVIEW')),
    CONSTRAINT chk_ai_suggestion_priority CHECK (priority IN ('URGENT','HIGH','NORMAL')),
    CONSTRAINT chk_ai_suggestion_status CHECK (status IN ('PROPOSED','ACCEPTED','DISMISSED','EXPIRED','SUPERSEDED')),
    CONSTRAINT chk_ai_suggestion_mode CHECK (execution_mode IN ('HUMAN_REVIEW_REQUIRED','AUTO_CUSTOMER_QUESTION_ALLOWED')),
    CONSTRAINT chk_ai_suggestion_review CHECK (status NOT IN ('ACCEPTED','DISMISSED') OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)),
    CONSTRAINT chk_ai_suggestion_dismissed CHECK (status <> 'DISMISSED' OR dismissal_reason IS NOT NULL)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS case_tasks (
    task_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    source VARCHAR(32) NOT NULL,
    source_suggestion_id VARCHAR(64) NULL,
    task_type VARCHAR(40) NOT NULL,
    title VARCHAR(300) NOT NULL,
    description TEXT NOT NULL,
    priority VARCHAR(16) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'TODO',
    assignee_user_id VARCHAR(64) NULL,
    due_at DATETIME(6) NULL,
    related_gap_ids_json JSON NOT NULL,
    related_verification_ids_json JSON NOT NULL,
    result_code VARCHAR(100) NULL,
    result_summary TEXT NULL,
    evidence_refs_json JSON NOT NULL,
    customer_visibility VARCHAR(32) NOT NULL DEFAULT 'INTERNAL_ONLY',
    completed_by VARCHAR(64) NULL,
    completed_at DATETIME(6) NULL,
    cancellation_reason VARCHAR(1000) NULL,
    client_request_id VARCHAR(100) NULL,
    version BIGINT NOT NULL DEFAULT 1,
    created_by VARCHAR(64) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    UNIQUE KEY uq_case_task_request (case_id, client_request_id),
    INDEX idx_case_tasks_state (case_id, status, priority, updated_at),
    INDEX idx_case_tasks_assignee (case_id, assignee_user_id, status),
    CONSTRAINT fk_case_task_case FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE,
    CONSTRAINT fk_case_task_suggestion FOREIGN KEY (source_suggestion_id) REFERENCES case_ai_suggestions(suggestion_id) ON DELETE SET NULL,
    CONSTRAINT chk_case_task_source CHECK (source IN ('STAFF_CREATED','AI_SUGGESTION_ACCEPTED','SYSTEM_REQUIRED')),
    CONSTRAINT chk_case_task_type CHECK (task_type IN ('CUSTOMER_CONTACT','INSTITUTION_VERIFICATION','TRANSACTION_REVIEW','PROTECTIVE_ACTION','DOCUMENT_REVIEW','OTHER')),
    CONSTRAINT chk_case_task_priority CHECK (priority IN ('URGENT','HIGH','NORMAL')),
    CONSTRAINT chk_case_task_status CHECK (status IN ('TODO','IN_PROGRESS','BLOCKED','COMPLETED','CANCELLED')),
    CONSTRAINT chk_case_task_visibility CHECK (customer_visibility IN ('INTERNAL_ONLY','RESULT_SHAREABLE','RESULT_PUBLISHED')),
    CONSTRAINT chk_case_task_completed CHECK (status <> 'COMPLETED' OR (result_summary IS NOT NULL AND completed_by IS NOT NULL AND completed_at IS NOT NULL)),
    CONSTRAINT chk_case_task_cancelled CHECK (status <> 'CANCELLED' OR cancellation_reason IS NOT NULL)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS case_decisions (
    decision_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    decision_type VARCHAR(32) NOT NULL,
    title VARCHAR(300) NOT NULL,
    rationale TEXT NOT NULL,
    related_entity_type VARCHAR(24) NOT NULL,
    related_entity_id VARCHAR(100) NOT NULL,
    visibility VARCHAR(32) NOT NULL DEFAULT 'BANK_INTERNAL',
    actor_user_id VARCHAR(64) NOT NULL,
    supersedes_decision_id VARCHAR(64) NULL,
    client_request_id VARCHAR(100) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    UNIQUE KEY uq_case_decision_request (case_id, client_request_id),
    INDEX idx_case_decisions_created (case_id, created_at, decision_id),
    CONSTRAINT fk_case_decision_case FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE,
    CONSTRAINT fk_case_decision_supersedes FOREIGN KEY (supersedes_decision_id) REFERENCES case_decisions(decision_id) ON DELETE SET NULL,
    CONSTRAINT chk_case_decision_type CHECK (decision_type IN ('FACT_REVIEW','TASK_DECISION','CASE_STATUS','CUSTOMER_DISCLOSURE','OTHER')),
    CONSTRAINT chk_case_decision_entity CHECK (related_entity_type IN ('FACT','GAP','SUGGESTION','TASK','VERIFICATION','CASE')),
    CONSTRAINT chk_case_decision_visibility CHECK (visibility IN ('BANK_INTERNAL','CUSTOMER_SHARED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS case_context_v2_history (
    history_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    entity_type VARCHAR(24) NOT NULL,
    entity_id VARCHAR(64) NOT NULL,
    entity_version BIGINT NOT NULL,
    operation VARCHAR(32) NOT NULL,
    actor_user_id VARCHAR(64) NOT NULL,
    before_json JSON NULL,
    after_json JSON NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    UNIQUE KEY uq_context_v2_history_version (entity_type, entity_id, entity_version),
    INDEX idx_context_v2_history_case (case_id, created_at),
    CONSTRAINT fk_context_v2_history_case FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TRIGGER IF EXISTS trg_context_facts_v2_insert;
CREATE TRIGGER trg_context_facts_v2_insert AFTER INSERT ON case_context_facts_v2 FOR EACH ROW UPDATE cases SET context_revision=context_revision+1 WHERE case_id=NEW.case_id;
DROP TRIGGER IF EXISTS trg_context_facts_v2_update;
CREATE TRIGGER trg_context_facts_v2_update AFTER UPDATE ON case_context_facts_v2 FOR EACH ROW UPDATE cases SET context_revision=context_revision+1 WHERE case_id=NEW.case_id;
DROP TRIGGER IF EXISTS trg_context_facts_v2_delete;
CREATE TRIGGER trg_context_facts_v2_delete AFTER DELETE ON case_context_facts_v2 FOR EACH ROW UPDATE cases SET context_revision=context_revision+1 WHERE case_id=OLD.case_id;

DROP TRIGGER IF EXISTS trg_case_gaps_insert;
CREATE TRIGGER trg_case_gaps_insert AFTER INSERT ON case_gaps FOR EACH ROW UPDATE cases SET context_revision=context_revision+1 WHERE case_id=NEW.case_id;
DROP TRIGGER IF EXISTS trg_case_gaps_update;
CREATE TRIGGER trg_case_gaps_update AFTER UPDATE ON case_gaps FOR EACH ROW UPDATE cases SET context_revision=context_revision+1 WHERE case_id=NEW.case_id;
DROP TRIGGER IF EXISTS trg_case_gaps_delete;
CREATE TRIGGER trg_case_gaps_delete AFTER DELETE ON case_gaps FOR EACH ROW UPDATE cases SET context_revision=context_revision+1 WHERE case_id=OLD.case_id;

DROP TRIGGER IF EXISTS trg_ai_suggestions_insert;
CREATE TRIGGER trg_ai_suggestions_insert AFTER INSERT ON case_ai_suggestions FOR EACH ROW UPDATE cases SET context_revision=context_revision+1 WHERE case_id=NEW.case_id;
DROP TRIGGER IF EXISTS trg_ai_suggestions_update;
CREATE TRIGGER trg_ai_suggestions_update AFTER UPDATE ON case_ai_suggestions FOR EACH ROW UPDATE cases SET context_revision=context_revision+1 WHERE case_id=NEW.case_id;
DROP TRIGGER IF EXISTS trg_ai_suggestions_delete;
CREATE TRIGGER trg_ai_suggestions_delete AFTER DELETE ON case_ai_suggestions FOR EACH ROW UPDATE cases SET context_revision=context_revision+1 WHERE case_id=OLD.case_id;

DROP TRIGGER IF EXISTS trg_case_tasks_insert;
CREATE TRIGGER trg_case_tasks_insert AFTER INSERT ON case_tasks FOR EACH ROW UPDATE cases SET context_revision=context_revision+1 WHERE case_id=NEW.case_id;
DROP TRIGGER IF EXISTS trg_case_tasks_update;
CREATE TRIGGER trg_case_tasks_update AFTER UPDATE ON case_tasks FOR EACH ROW UPDATE cases SET context_revision=context_revision+1 WHERE case_id=NEW.case_id;
DROP TRIGGER IF EXISTS trg_case_tasks_delete;
CREATE TRIGGER trg_case_tasks_delete AFTER DELETE ON case_tasks FOR EACH ROW UPDATE cases SET context_revision=context_revision+1 WHERE case_id=OLD.case_id;

DROP TRIGGER IF EXISTS trg_case_decisions_insert;
CREATE TRIGGER trg_case_decisions_insert AFTER INSERT ON case_decisions FOR EACH ROW UPDATE cases SET context_revision=context_revision+1 WHERE case_id=NEW.case_id;
DROP TRIGGER IF EXISTS trg_case_decisions_delete;
CREATE TRIGGER trg_case_decisions_delete AFTER DELETE ON case_decisions FOR EACH ROW UPDATE cases SET context_revision=context_revision+1 WHERE case_id=OLD.case_id;
