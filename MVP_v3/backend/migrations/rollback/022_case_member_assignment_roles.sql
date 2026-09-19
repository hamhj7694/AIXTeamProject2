ALTER TABLE case_members
    DROP CONSTRAINT chk_case_member_assignment_role,
    DROP COLUMN assignment_role;
