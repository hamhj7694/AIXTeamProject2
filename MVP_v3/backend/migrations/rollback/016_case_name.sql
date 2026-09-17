-- Run manually only after verifying that the Case name data is no longer needed.

ALTER TABLE cases
    DROP COLUMN case_name;

DELETE FROM schema_migrations WHERE migration_name='016_case_name.sql';
