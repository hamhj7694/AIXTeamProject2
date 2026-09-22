-- Public transaction contract: KRW integer amounts and explicit movement types.
-- This migration intentionally does not add a deduplication key; that rule is
-- defined only after source-event metadata and existing records are audited.
SET @fractional_amounts = (
    SELECT COUNT(*) FROM case_transactions
    WHERE amount <> TRUNCATE(amount, 0)
);
SET @invalid_transaction_types = (
    SELECT COUNT(*) FROM case_transactions
    WHERE transaction_type NOT IN ('TRANSFER_OUT', 'RETURN_IN', 'CANCELLED')
);
SET @contract_guard_sql = IF(
    @fractional_amounts = 0 AND @invalid_transaction_types = 0,
    'SELECT 1',
    'THIS IS INTENTIONALLY INVALID SQL: transaction rows need manual normalization'
);
PREPARE contract_guard_stmt FROM @contract_guard_sql;
EXECUTE contract_guard_stmt;
DEALLOCATE PREPARE contract_guard_stmt;

ALTER TABLE case_transactions
    MODIFY COLUMN amount BIGINT NOT NULL,
    MODIFY COLUMN transaction_type VARCHAR(32) NOT NULL,
    ADD CONSTRAINT chk_case_transactions_type CHECK (
        transaction_type IN ('TRANSFER_OUT', 'RETURN_IN', 'CANCELLED')
    ),
    ADD CONSTRAINT chk_case_transactions_amount CHECK (amount >= 0);
