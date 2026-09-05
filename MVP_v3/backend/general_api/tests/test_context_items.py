import unittest

from pydantic import ValidationError
from general_api.app.domains.cases.context_items import (
    ContextItem, ContextItemChange, ContextItemConflictError, apply_staff_change, merge_ai_proposal,
)


class ContextItemTest(unittest.TestCase):
    def setUp(self):
        self.item = ContextItem(item_id='ctx-1', case_id='VP-1', section='CLAIM',
                                semantic_key='claim:prosecution', item_version=1, ai_text='검찰 소속 주장')

    def test_employee_wording_survives_ai_proposal(self):
        edited = apply_staff_change(self.item, ContextItemChange(expected_version=1, operation='EDIT', text='검찰 사칭 주장 확인 중'), 'staff-1')
        merged = merge_ai_proposal(edited, '수사기관 소속이라고 주장', ['event-1'])
        self.assertEqual(merged.effective_text, '검찰 사칭 주장 확인 중')
        self.assertEqual(merged.ai_text, '수사기관 소속이라고 주장')
        self.assertEqual(merged.item_id, self.item.item_id)

    def test_deleted_item_does_not_reappear_after_ai_rephrasing(self):
        deleted = apply_staff_change(self.item, ContextItemChange(expected_version=1, operation='DELETE'), 'staff-1')
        merged = merge_ai_proposal(deleted, '새 표현', ['event-2'])
        self.assertEqual(merged.deleted_by, 'staff-1')
        restored = apply_staff_change(merged, ContextItemChange(expected_version=3, operation='RESTORE'), 'staff-2')
        self.assertIsNone(restored.deleted_by)

    def test_stale_edits_are_rejected(self):
        with self.assertRaises(ContextItemConflictError):
            apply_staff_change(self.item, ContextItemChange(expected_version=2, operation='EDIT', text='오래된 초안'), 'staff-1')

    def test_idempotent_ai_does_not_increment_version(self):
        self.assertEqual(merge_ai_proposal(self.item, self.item.ai_text, []), self.item)

    def test_empty_edit_and_unsupported_source_sections_are_rejected(self):
        with self.assertRaises(ValidationError):
            ContextItemChange(expected_version=1, operation='EDIT', text='  ')
        with self.assertRaises(ValidationError):
            ContextItemChange(expected_version=1, operation='DELETE', text='본문도 변경')
        with self.assertRaises(ValidationError):
            ContextItem(item_id='x', case_id='VP-1', section='CONFIRMED_FACT', semantic_key='x', item_version=1)

    def test_editing_deleted_item_requires_explicit_restore(self):
        deleted = apply_staff_change(self.item, ContextItemChange(expected_version=1, operation='DELETE'), 'staff-1')
        with self.assertRaises(ContextItemConflictError):
            apply_staff_change(deleted, ContextItemChange(expected_version=2, operation='EDIT', text='수정'), 'staff-1')
