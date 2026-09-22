-- Align historical 021 staff-role installations with the current 020 contract.
-- Widen only; no role reassignment, seed overwrite or business-row deletion.
ALTER TABLE bank_staff_directory
    MODIFY COLUMN assignment_role VARCHAR(32) NOT NULL DEFAULT 'CONSULTATION',
    DROP CHECK chk_bank_staff_assignment_role,
    ADD CONSTRAINT chk_bank_staff_assignment_role CHECK (
        assignment_role IN ('SUPERVISOR','MONITORING','CONSULTATION','OTHER_VIEWER','HANDOVER_PENDING')
    );
