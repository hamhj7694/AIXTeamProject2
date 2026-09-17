-- Durable, privacy-safe storage for the A-part structured diagnosis result.
-- Raw call text is never copied into these tables.

CREATE TABLE IF NOT EXISTS case_semantic_atoms (
    case_id VARCHAR(32) NOT NULL,
    atom_id VARCHAR(80) NOT NULL,
    atom_class VARCHAR(80) NOT NULL,
    predicate VARCHAR(120) NOT NULL,
    source_turn_id INT NOT NULL,
    semantic_fingerprint VARCHAR(128) NOT NULL,
    payload_json JSON NOT NULL,
    source_revision BIGINT NOT NULL DEFAULT 1,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (case_id, atom_id),
    UNIQUE KEY uq_case_atom_fingerprint (case_id, semantic_fingerprint),
    INDEX idx_case_atoms_turn (case_id, source_turn_id),
    CONSTRAINT fk_case_atoms_case FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS case_semantic_relations (
    case_id VARCHAR(32) NOT NULL,
    relation_id VARCHAR(100) NOT NULL,
    relation_type VARCHAR(32) NOT NULL,
    source_atom_id VARCHAR(80) NOT NULL,
    target_atom_id VARCHAR(80) NOT NULL,
    confidence DECIMAL(5,4) NOT NULL,
    payload_json JSON NOT NULL,
    source_revision BIGINT NOT NULL DEFAULT 1,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (case_id, relation_id),
    INDEX idx_case_relations_atoms (case_id, source_atom_id, target_atom_id),
    CONSTRAINT fk_case_relations_case FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE,
    CONSTRAINT chk_case_relation_confidence CHECK (confidence >= 0 AND confidence <= 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS case_context_signals (
    case_id VARCHAR(32) NOT NULL,
    signal_id VARCHAR(100) NOT NULL,
    signal_code VARCHAR(120) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    confidence DECIMAL(5,4) NOT NULL,
    claim_status VARCHAR(32) NOT NULL,
    visibility VARCHAR(32) NOT NULL DEFAULT 'BANK_INTERNAL',
    payload_json JSON NOT NULL,
    source_revision BIGINT NOT NULL DEFAULT 1,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (case_id, signal_id),
    INDEX idx_case_signals_state (case_id, severity, visibility),
    CONSTRAINT fk_case_signals_case FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE,
    CONSTRAINT chk_case_signal_confidence CHECK (confidence >= 0 AND confidence <= 1),
    CONSTRAINT chk_case_signal_visibility CHECK (visibility IN ('BANK_INTERNAL', 'CUSTOMER_SHARED', 'SHARED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
