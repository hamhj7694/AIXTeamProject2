DROP TABLE IF EXISTS case_context_signals;
DROP TABLE IF EXISTS case_semantic_relations;
DROP TABLE IF EXISTS case_semantic_atoms;
DELETE FROM schema_migrations WHERE migration_name='017_structured_context_resources.sql';
