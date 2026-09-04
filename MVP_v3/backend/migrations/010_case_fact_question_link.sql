-- Preserve the originating customer question for human-readable Fact review.
-- Run after migrations 001-009.

ALTER TABLE case_facts
    ADD COLUMN source_question_id VARCHAR(100) NULL,
    ADD INDEX idx_case_facts_question (case_id, source_question_id);
