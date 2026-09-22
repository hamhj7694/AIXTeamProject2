-- Retire the demo-only attachment tables.
-- Fail closed: existing rows block the migration so data cannot be deleted implicitly.
SET @csr_case_attachment_table_exists = (
    SELECT COUNT(*) FROM information_schema.TABLES
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'case_attachments'
);
SET @csr_message_attachment_table_exists = (
    SELECT COUNT(*) FROM information_schema.TABLES
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'message_attachments'
);
SET @csr_case_attachment_rows = IF(
    @csr_case_attachment_table_exists = 1,
    (SELECT COUNT(*) FROM case_attachments),
    0
);
SET @csr_message_attachment_rows = IF(
    @csr_message_attachment_table_exists = 1,
    (SELECT COUNT(*) FROM message_attachments),
    0
);
SET @csr_retire_attachment_sql = IF(
    @csr_case_attachment_rows = 0 AND @csr_message_attachment_rows = 0,
    'DROP TABLE IF EXISTS message_attachments, case_attachments',
    'SELECT * FROM information_schema.CSR_ATTACHMENT_RETIRE_BLOCKED'
);
PREPARE csr_retire_attachments FROM @csr_retire_attachment_sql;
EXECUTE csr_retire_attachments;
DEALLOCATE PREPARE csr_retire_attachments;
