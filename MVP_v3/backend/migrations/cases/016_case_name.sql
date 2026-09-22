-- Staff-editable display name for the Case list and Case room.

ALTER TABLE cases
    ADD COLUMN case_name VARCHAR(200) NULL AFTER case_id;
