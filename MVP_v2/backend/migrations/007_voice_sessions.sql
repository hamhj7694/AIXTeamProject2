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
);

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
);
