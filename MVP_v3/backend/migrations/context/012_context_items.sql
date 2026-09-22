-- Additive foundation only; existing Case/Action/Fact records are untouched.
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
