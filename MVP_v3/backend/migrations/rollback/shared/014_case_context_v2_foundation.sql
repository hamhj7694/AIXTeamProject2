-- Destructive rollback for 014. Run only before v2 data is written, or after a
-- verified backup/export. Never run this file through apply_migrations.py.

DROP TRIGGER IF EXISTS trg_case_decisions_delete;
DROP TRIGGER IF EXISTS trg_case_decisions_insert;
DROP TRIGGER IF EXISTS trg_case_tasks_delete;
DROP TRIGGER IF EXISTS trg_case_tasks_update;
DROP TRIGGER IF EXISTS trg_case_tasks_insert;
DROP TRIGGER IF EXISTS trg_ai_suggestions_delete;
DROP TRIGGER IF EXISTS trg_ai_suggestions_update;
DROP TRIGGER IF EXISTS trg_ai_suggestions_insert;
DROP TRIGGER IF EXISTS trg_case_gaps_delete;
DROP TRIGGER IF EXISTS trg_case_gaps_update;
DROP TRIGGER IF EXISTS trg_case_gaps_insert;
DROP TRIGGER IF EXISTS trg_context_facts_v2_delete;
DROP TRIGGER IF EXISTS trg_context_facts_v2_update;
DROP TRIGGER IF EXISTS trg_context_facts_v2_insert;

DROP TABLE IF EXISTS case_context_v2_history;
DROP TABLE IF EXISTS case_decisions;
DROP TABLE IF EXISTS case_tasks;
DROP TABLE IF EXISTS case_ai_suggestions;
DROP TABLE IF EXISTS case_gaps;
DROP TABLE IF EXISTS case_context_facts_v2;

DELETE FROM schema_migrations WHERE migration_name='014_case_context_v2_foundation.sql';
