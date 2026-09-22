-- Retire the legacy table after every supported row has a V2 copy.

DELETE cf
FROM case_facts cf
LEFT JOIN case_context_facts_v2 v2
  ON v2.client_request_id = CONCAT('legacy-case-fact:', cf.fact_id)
WHERE v2.fact_id IS NOT NULL;

SET @remaining_legacy_case_facts = (SELECT COUNT(*) FROM case_facts);
SET @retire_case_facts_sql = IF(
    @remaining_legacy_case_facts = 0,
    'DROP TABLE case_facts',
    'THIS IS INTENTIONALLY INVALID SQL: unsupported legacy case_facts rows remain'
);
PREPARE retire_case_facts_stmt FROM @retire_case_facts_sql;
EXECUTE retire_case_facts_stmt;
DEALLOCATE PREPARE retire_case_facts_stmt;
