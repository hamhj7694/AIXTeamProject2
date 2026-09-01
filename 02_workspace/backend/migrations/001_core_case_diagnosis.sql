CREATE TABLE cases (
    case_id VARCHAR(32) PRIMARY KEY,
    client_request_id VARCHAR(100) NULL UNIQUE,
    risk_level ENUM('NORMAL', 'LOW', 'HIGH') NOT NULL,
    risk_score DECIMAL(6, 3) NOT NULL,
    mode ENUM('PREVENT', 'RECOVERY', 'CLOSED') NOT NULL DEFAULT 'PREVENT',
    status ENUM('NEW', 'TRIAGE', 'VERIFYING', 'IN_PROGRESS', 'CLOSED') NOT NULL DEFAULT 'TRIAGE',
    initial_brief TEXT NOT NULL,
    diagnosis_json JSON NOT NULL,
    created_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL
);

CREATE TABLE case_inputs (
    input_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    input_type ENUM('TEXT', 'VOICE_TRANSCRIPT') NOT NULL DEFAULT 'TEXT',
    input_text TEXT NOT NULL,
    created_at DATETIME(6) NOT NULL,
    CONSTRAINT fk_case_inputs_case FOREIGN KEY (case_id) REFERENCES cases(case_id)
);

CREATE TABLE analysis_segments (
    segment_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    start_turn INT NOT NULL,
    end_turn INT NOT NULL,
    segment_text TEXT NOT NULL,
    risk_score DECIMAL(6, 3) NOT NULL,
    model_label ENUM('NORMAL', 'PHISHING') NOT NULL,
    evidence_json JSON NOT NULL,
    created_at DATETIME(6) NOT NULL,
    CONSTRAINT fk_segments_case FOREIGN KEY (case_id) REFERENCES cases(case_id)
);

CREATE TABLE context_features (
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
);

CREATE TABLE case_events (
    event_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    payload_json JSON NOT NULL,
    occurred_at DATETIME(6) NOT NULL,
    INDEX idx_case_events_case_cursor (case_id, event_id),
    CONSTRAINT fk_case_events_case FOREIGN KEY (case_id) REFERENCES cases(case_id)
);
