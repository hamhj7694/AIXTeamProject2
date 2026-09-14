-- Rollback is intentionally explicit and removes only V3-added persistence.
DROP TABLE IF EXISTS message_context_extractions;
DROP TRIGGER IF EXISTS trg_questions_context_revision_update;
ALTER TABLE customer_questions
    DROP COLUMN answer_question_version,
    DROP COLUMN answer_payload_json,
    DROP COLUMN question_version,
    DROP COLUMN allow_multi_select;
CREATE TRIGGER trg_questions_context_revision_update AFTER UPDATE ON customer_questions FOR EACH ROW
UPDATE cases SET context_revision=context_revision+IF(
    NOT (OLD.target_field <=> NEW.target_field) OR NOT (OLD.question_text <=> NEW.question_text)
    OR NOT (OLD.reason <=> NEW.reason) OR NOT (OLD.priority <=> NEW.priority)
    OR NOT (OLD.status <=> NEW.status) OR NOT (OLD.answer_text <=> NEW.answer_text), 1, 0
) WHERE case_id=NEW.case_id;
DELETE FROM schema_migrations WHERE migration_name='015_context_panel_v3.sql';
