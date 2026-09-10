CREATE TABLE IF NOT EXISTS case_number_sequences (
    sequence_name VARCHAR(32) PRIMARY KEY,
    current_value BIGINT UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO case_number_sequences (sequence_name, current_value)
VALUES ('cases', 0);

-- Preserve existing cases and initialize the sequence from the maximum numeric VP-N.
UPDATE case_number_sequences
SET current_value = GREATEST(
    current_value,
    (
        SELECT COALESCE(MAX(CAST(SUBSTRING(case_id, 4) AS UNSIGNED)), 0)
        FROM cases
        WHERE case_id REGEXP '^VP-[0-9]+$'
    )
)
WHERE sequence_name = 'cases';
