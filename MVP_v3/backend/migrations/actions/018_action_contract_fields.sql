-- Additive Action contract expansion for the shared migration sequence.
-- Existing Action rows and note content are retained; note remains the
-- compatibility description field. Apply only after migrations 001-017.

ALTER TABLE actions
    ADD COLUMN title VARCHAR(300) NULL AFTER action_type,
    ADD COLUMN version BIGINT NOT NULL DEFAULT 1 AFTER actor_type,
    ADD COLUMN updated_at DATETIME(6) NULL AFTER created_at,
    ADD COLUMN updated_by VARCHAR(128) NULL AFTER updated_at,
    ADD COLUMN visibility VARCHAR(32) NOT NULL DEFAULT 'BANK_INTERNAL' AFTER updated_by;

-- Historical rows have no independent modification timestamp. Preserve their
-- known creation timestamp rather than assigning migration execution time.
UPDATE actions
SET updated_at = created_at
WHERE updated_at IS NULL;

ALTER TABLE actions
    MODIFY COLUMN updated_at DATETIME(6) NOT NULL,
    ADD CONSTRAINT chk_actions_version CHECK (version >= 1),
    ADD CONSTRAINT chk_actions_visibility CHECK (visibility IN ('BANK_INTERNAL', 'CUSTOMER_SHARED'));
