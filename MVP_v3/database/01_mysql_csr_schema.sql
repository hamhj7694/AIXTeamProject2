-- MVP_v3 FastAPI용 빈 MySQL 스키마
-- 대상: MySQL 8.0 이상 권장 (utf8mb4 / JSON / DATETIME(6) 사용)
-- 이 파일은 기존 Case·메시지 데이터를 INSERT하지 않는다.
--
-- DB가 아직 없다면 아래 두 줄을 먼저 실행한다.
-- CREATE DATABASE IF NOT EXISTS `csr` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE `csr`;

SET NAMES utf8mb4;
SET time_zone = '+00:00';

CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_name VARCHAR(255) PRIMARY KEY,
    applied_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS cases (
    case_id VARCHAR(32) PRIMARY KEY,
    client_request_id VARCHAR(100) NULL UNIQUE,
    risk_level ENUM('NORMAL', 'LOW', 'HIGH') NOT NULL,
    risk_score DECIMAL(9, 6) NOT NULL,
    mode ENUM('PREVENT', 'RECOVERY', 'CLOSED') NOT NULL DEFAULT 'PREVENT',
    status ENUM('NEW', 'TRIAGE', 'VERIFYING', 'IN_PROGRESS', 'CLOSED') NOT NULL DEFAULT 'TRIAGE',
    version INT NOT NULL DEFAULT 1,
    context_revision BIGINT NOT NULL DEFAULT 1,
    initial_brief TEXT NOT NULL,
    diagnosis_json JSON NOT NULL,
    victim_transfer_status VARCHAR(30) NULL,
    actual_loss_amount_krw BIGINT NULL,
    deleted_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL,
    INDEX idx_cases_active_updated (deleted_at, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS case_inputs (
    input_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    input_type ENUM('TEXT', 'VOICE_TRANSCRIPT') NOT NULL DEFAULT 'TEXT',
    input_text TEXT NOT NULL,
    created_at DATETIME(6) NOT NULL,
    INDEX idx_case_inputs_case (case_id, input_id),
    CONSTRAINT fk_case_inputs_case FOREIGN KEY (case_id) REFERENCES cases(case_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS analysis_segments (
    segment_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    start_turn INT NOT NULL,
    end_turn INT NOT NULL,
    segment_text TEXT NOT NULL,
    risk_score DECIMAL(9, 6) NOT NULL,
    model_label ENUM('NORMAL', 'PHISHING') NOT NULL,
    evidence_json JSON NOT NULL,
    created_at DATETIME(6) NOT NULL,
    INDEX idx_analysis_segments_case (case_id, start_turn, end_turn),
    CONSTRAINT fk_segments_case FOREIGN KEY (case_id) REFERENCES cases(case_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS context_features (
    feature_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    segment_id VARCHAR(64) NULL,
    feature_key VARCHAR(100) NOT NULL,
    feature_value DECIMAL(18, 6) NOT NULL,
    source VARCHAR(50) NOT NULL,
    created_at DATETIME(6) NOT NULL,
    INDEX idx_context_features_case_key (case_id, feature_key),
    CONSTRAINT fk_features_case FOREIGN KEY (case_id) REFERENCES cases(case_id),
    CONSTRAINT fk_features_segment FOREIGN KEY (segment_id) REFERENCES analysis_segments(segment_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS case_events (
    event_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    actor_type VARCHAR(32) NOT NULL DEFAULT 'SYSTEM',
    payload_json JSON NOT NULL,
    occurred_at DATETIME(6) NOT NULL,
    INDEX idx_case_events_case_cursor (case_id, event_id),
    CONSTRAINT fk_case_events_case FOREIGN KEY (case_id) REFERENCES cases(case_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS case_reports (
    report_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    report_type ENUM('LIVE', 'FINAL') NOT NULL DEFAULT 'LIVE',
    report_version INT NOT NULL DEFAULT 1,
    created_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL,
    UNIQUE KEY uq_case_live_report (case_id, report_type),
    CONSTRAINT fk_case_reports_case FOREIGN KEY (case_id) REFERENCES cases(case_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS case_report_sections (
    report_id VARCHAR(64) NOT NULL,
    section_key VARCHAR(64) NOT NULL,
    content_json JSON NOT NULL,
    section_version INT NOT NULL DEFAULT 1,
    updated_at DATETIME(6) NOT NULL,
    PRIMARY KEY (report_id, section_key),
    CONSTRAINT fk_report_sections_report FOREIGN KEY (report_id) REFERENCES case_reports(report_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS messages (
    message_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    actor_type VARCHAR(32) NOT NULL,
    actor_user_id VARCHAR(64) NULL,
    actor_display_name VARCHAR(80) NULL,
    actor_role VARCHAR(64) NULL,
    content TEXT NOT NULL,
    channel VARCHAR(32) NOT NULL DEFAULT 'CUSTOMER',
    audience VARCHAR(32) NOT NULL DEFAULT 'CUSTOMER',
    visibility VARCHAR(32) NOT NULL DEFAULT 'CUSTOMER',
    message_kind VARCHAR(32) NOT NULL DEFAULT 'CHAT',
    mentions_json TEXT NULL,
    reply_to_message_id VARCHAR(64) NULL,
    private_owner_user_id VARCHAR(64) NULL,
    attachments_json JSON NULL,
    client_request_id VARCHAR(100) NULL,
    created_at DATETIME(6) NOT NULL,
    UNIQUE KEY uq_messages_case_client_request (case_id, client_request_id),
    INDEX idx_messages_case_cursor (case_id, created_at, message_id),
    CONSTRAINT fk_messages_case FOREIGN KEY (case_id) REFERENCES cases(case_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS verification_tasks (
    verification_task_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    claim TEXT NOT NULL,
    target VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    version INT NOT NULL DEFAULT 1,
    result_summary TEXT NULL,
    evidence_url VARCHAR(2000) NULL,
    verified_by VARCHAR(80) NULL,
    rag_source VARCHAR(255) NULL,
    customer_visible BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL,
    INDEX idx_verification_tasks_case (case_id, created_at),
    CONSTRAINT fk_verification_tasks_case FOREIGN KEY (case_id) REFERENCES cases(case_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS voice_sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    status ENUM('REQUESTED', 'ACTIVE', 'ENDED', 'FAILED') NOT NULL DEFAULT 'REQUESTED',
    participants_json JSON NOT NULL,
    started_at DATETIME(6) NULL,
    ended_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL,
    INDEX idx_voice_sessions_case (case_id, created_at),
    CONSTRAINT fk_voice_sessions_case FOREIGN KEY (case_id) REFERENCES cases(case_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS transcript_segments (
    segment_id VARCHAR(64) PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    case_id VARCHAR(32) NOT NULL,
    speaker VARCHAR(32) NOT NULL,
    content TEXT NOT NULL,
    started_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL,
    INDEX idx_transcript_segments_session (session_id, created_at),
    CONSTRAINT fk_transcript_segments_session FOREIGN KEY (session_id) REFERENCES voice_sessions(session_id),
    CONSTRAINT fk_transcript_segments_case FOREIGN KEY (case_id) REFERENCES cases(case_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS message_attachments (
    message_id VARCHAR(64) NOT NULL,
    attachment_id VARCHAR(64) NOT NULL,
    attached_at DATETIME(6) NOT NULL,
    PRIMARY KEY (message_id, attachment_id),
    CONSTRAINT fk_message_attachments_message FOREIGN KEY (message_id) REFERENCES messages(message_id),
    CONSTRAINT fk_message_attachments_attachment FOREIGN KEY (attachment_id) REFERENCES case_attachments(attachment_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
    answer_text TEXT NULL,
    created_at DATETIME(6) NOT NULL,
    INDEX idx_customer_questions_case (case_id, sequence),
    CONSTRAINT fk_customer_questions_case FOREIGN KEY (case_id) REFERENCES cases(case_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS case_facts (
    fact_id VARCHAR(100) PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    value TEXT NOT NULL,
    source VARCHAR(32) NOT NULL,
    status VARCHAR(16) NOT NULL,
    confidence DECIMAL(5, 4) NOT NULL,
    evidence_message_id VARCHAR(64) NULL,
    source_question_id VARCHAR(100) NULL,
    confirmed_by VARCHAR(80) NULL,
    confirmed_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL,
    INDEX idx_case_facts_case (case_id, field_name),
    INDEX idx_case_facts_question (case_id, source_question_id),
    CONSTRAINT fk_case_facts_case FOREIGN KEY (case_id) REFERENCES cases(case_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 이 단일 초기화 파일이 포함한 기존 migration을 기준선으로 기록한다.
CREATE TABLE IF NOT EXISTS case_context_items (
    item_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    section VARCHAR(32) NOT NULL,
    semantic_key VARCHAR(160) COLLATE utf8mb4_bin NOT NULL,
    item_version BIGINT NOT NULL,
    state_json JSON NOT NULL,
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    UNIQUE KEY uq_context_semantic (case_id, section, semantic_key),
    CONSTRAINT fk_context_item_case FOREIGN KEY (case_id) REFERENCES cases(case_id)
);

CREATE TABLE IF NOT EXISTS case_context_item_history (
    history_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    item_id VARCHAR(64) NOT NULL,
    item_version BIGINT NOT NULL,
    operation VARCHAR(24) NOT NULL,
    actor_id VARCHAR(64) NOT NULL,
    before_json JSON NULL,
    after_json JSON NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    UNIQUE KEY uq_context_history_version (item_id, item_version),
    CONSTRAINT fk_context_history_item FOREIGN KEY (item_id) REFERENCES case_context_items(item_id)
);

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

CREATE TRIGGER trg_cases_context_revision_update BEFORE UPDATE ON cases FOR EACH ROW
SET NEW.context_revision=GREATEST(NEW.context_revision,OLD.context_revision+IF(NOT (OLD.mode <=> NEW.mode) OR NOT (OLD.status <=> NEW.status) OR NOT (OLD.diagnosis_json <=> NEW.diagnosis_json) OR NOT (OLD.victim_transfer_status <=> NEW.victim_transfer_status) OR NOT (OLD.actual_loss_amount_krw <=> NEW.actual_loss_amount_krw),1,0));
CREATE TRIGGER trg_messages_context_revision_insert AFTER INSERT ON messages FOR EACH ROW UPDATE cases SET context_revision=context_revision+1 WHERE case_id=NEW.case_id;
CREATE TRIGGER trg_messages_context_revision_delete AFTER DELETE ON messages FOR EACH ROW UPDATE cases SET context_revision=context_revision+1 WHERE case_id=OLD.case_id;
CREATE TRIGGER trg_questions_context_revision_insert AFTER INSERT ON customer_questions FOR EACH ROW UPDATE cases SET context_revision=context_revision+1 WHERE case_id=NEW.case_id;
CREATE TRIGGER trg_questions_context_revision_update AFTER UPDATE ON customer_questions FOR EACH ROW UPDATE cases SET context_revision=context_revision+IF(NOT (OLD.target_field <=> NEW.target_field) OR NOT (OLD.question_text <=> NEW.question_text) OR NOT (OLD.reason <=> NEW.reason) OR NOT (OLD.priority <=> NEW.priority) OR NOT (OLD.status <=> NEW.status) OR NOT (OLD.answer_text <=> NEW.answer_text),1,0) WHERE case_id=NEW.case_id;
CREATE TRIGGER trg_questions_context_revision_delete AFTER DELETE ON customer_questions FOR EACH ROW UPDATE cases SET context_revision=context_revision+1 WHERE case_id=OLD.case_id;
CREATE TRIGGER trg_facts_context_revision_insert AFTER INSERT ON case_facts FOR EACH ROW UPDATE cases SET context_revision=context_revision+1 WHERE case_id=NEW.case_id;
CREATE TRIGGER trg_facts_context_revision_update AFTER UPDATE ON case_facts FOR EACH ROW UPDATE cases SET context_revision=context_revision+IF(NOT (OLD.field_name <=> NEW.field_name) OR NOT (OLD.value <=> NEW.value) OR NOT (OLD.source <=> NEW.source) OR NOT (OLD.status <=> NEW.status),1,0) WHERE case_id=NEW.case_id;
CREATE TRIGGER trg_facts_context_revision_delete AFTER DELETE ON case_facts FOR EACH ROW UPDATE cases SET context_revision=context_revision+1 WHERE case_id=OLD.case_id;
CREATE TRIGGER trg_verifications_context_revision_insert AFTER INSERT ON verification_tasks FOR EACH ROW UPDATE cases SET context_revision=context_revision+1 WHERE case_id=NEW.case_id;
CREATE TRIGGER trg_verifications_context_revision_update AFTER UPDATE ON verification_tasks FOR EACH ROW UPDATE cases SET context_revision=context_revision+IF(NOT (OLD.claim <=> NEW.claim) OR NOT (OLD.target <=> NEW.target) OR NOT (OLD.status <=> NEW.status) OR NOT (OLD.result_summary <=> NEW.result_summary),1,0) WHERE case_id=NEW.case_id;
CREATE TRIGGER trg_verifications_context_revision_delete AFTER DELETE ON verification_tasks FOR EACH ROW UPDATE cases SET context_revision=context_revision+1 WHERE case_id=OLD.case_id;
CREATE TRIGGER trg_actions_context_revision_insert AFTER INSERT ON actions FOR EACH ROW UPDATE cases SET context_revision=context_revision+1 WHERE case_id=NEW.case_id;
CREATE TRIGGER trg_actions_context_revision_update AFTER UPDATE ON actions FOR EACH ROW UPDATE cases SET context_revision=context_revision+IF(NOT (OLD.action_type <=> NEW.action_type) OR NOT (OLD.status <=> NEW.status) OR NOT (OLD.note <=> NEW.note),1,0) WHERE case_id=NEW.case_id;
CREATE TRIGGER trg_actions_context_revision_delete AFTER DELETE ON actions FOR EACH ROW UPDATE cases SET context_revision=context_revision+1 WHERE case_id=OLD.case_id;

-- 업무 데이터가 아니라 Schema version metadata이며, 이후 apply_migrations.py를
-- 실행했을 때 동일 ALTER 문이 중복 실행되는 것을 방지한다.
INSERT IGNORE INTO schema_migrations (migration_name) VALUES
    ('001_core_case_diagnosis.sql'),
    ('002_initial_live_report.sql'),
    ('003_expand_risk_score_precision.sql'),
    ('004_case_messages_and_event_actor.sql'),
    ('005_verification_actions.sql'),
    ('006_case_version.sql'),
    ('007_voice_sessions.sql'),
    ('008_collaboration_channels.sql'),
    ('009_case_attachments.sql'),
    ('009_mysql_parity_workflow.sql'),
    ('010_case_fact_question_link.sql'),
    ('012_context_items.sql'),
    ('013_context_projection_revision.sql');
