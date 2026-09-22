CREATE TABLE IF NOT EXISTS bank_staff_directory (
    staff_id VARCHAR(64) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    assignment_role VARCHAR(32) NOT NULL DEFAULT 'CONSULTATION',
    role_label VARCHAR(100) NOT NULL,
    position_title VARCHAR(100) NULL,
    status_text VARCHAR(80) NOT NULL DEFAULT '근무 중',
    status_color_key VARCHAR(16) NOT NULL DEFAULT 'GREEN',
    assignment_eligible BOOLEAN NOT NULL DEFAULT TRUE,
    linked_user_id VARCHAR(64) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    deleted_at DATETIME(6) NULL,
    PRIMARY KEY (staff_id),
    INDEX idx_bank_staff_active (deleted_at, display_name),
    CONSTRAINT chk_bank_staff_assignment_role CHECK (assignment_role IN ('SUPERVISOR','MONITORING','CONSULTATION','OTHER_VIEWER','HANDOVER_PENDING')),
    CONSTRAINT chk_bank_staff_color CHECK (status_color_key IN ('GREEN','BLUE','YELLOW','ORANGE','RED','PURPLE','GRAY'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
