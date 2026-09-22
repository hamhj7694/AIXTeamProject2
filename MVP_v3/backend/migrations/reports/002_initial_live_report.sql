CREATE TABLE IF NOT EXISTS case_reports (
    report_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL,
    report_type ENUM('LIVE', 'FINAL') NOT NULL DEFAULT 'LIVE',
    report_version INT NOT NULL DEFAULT 1,
    created_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL,
    UNIQUE KEY uq_case_live_report (case_id, report_type),
    CONSTRAINT fk_case_reports_case FOREIGN KEY (case_id) REFERENCES cases(case_id)
);

CREATE TABLE IF NOT EXISTS case_report_sections (
    report_id VARCHAR(64) NOT NULL,
    section_key VARCHAR(64) NOT NULL,
    content_json JSON NOT NULL,
    section_version INT NOT NULL DEFAULT 1,
    updated_at DATETIME(6) NOT NULL,
    PRIMARY KEY (report_id, section_key),
    CONSTRAINT fk_report_sections_report FOREIGN KEY (report_id) REFERENCES case_reports(report_id)
);
