-- Retire the legacy raw transcript table.
-- This migration is deliberately fail-closed: it drops the table only when
-- it is empty. Any existing transcript data blocks the migration for manual
-- review instead of being deleted implicitly.
SET @csr_transcript_table_exists = (
    SELECT COUNT(*)
    FROM information_schema.TABLES
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'transcript_segments'
);
SET @csr_transcript_rows = IF(
    @csr_transcript_table_exists = 1,
    (SELECT COUNT(*) FROM transcript_segments),
    0
);
SET @csr_retire_transcript_sql = IF(
    @csr_transcript_table_exists = 0,
    'SELECT 1',
    IF(
        @csr_transcript_rows = 0,
        'DROP TABLE transcript_segments',
        'SELECT * FROM information_schema.CSR_TRANSCRIPT_RETIRE_BLOCKED'
    )
);
PREPARE csr_retire_transcript FROM @csr_retire_transcript_sql;
EXECUTE csr_retire_transcript;
DEALLOCATE PREPARE csr_retire_transcript;
