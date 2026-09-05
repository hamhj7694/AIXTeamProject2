import json
import unittest
from pathlib import Path

from ai_api.app.domains.case_support import CaseSnapshotAiAdapter


class ContextReviewRegressionTest(unittest.TestCase):
    def snapshot(self):
        fixture = Path(__file__).resolve().parents[2] / 'contracts/ai_internal/fixtures/diagnosis.high.v1.json'
        return {'case_id': 'VP-REVIEW', 'diagnosis': json.loads(fixture.read_text(encoding='utf-8'))['response']}

    def test_checklist_is_not_a_performed_response_action(self):
        snapshot = self.snapshot()
        snapshot['actions'] = [
            {'action_id': 'a1', 'action_type': 'AI_CHECKLIST:P0:transfer_status', 'status': 'REQUESTED', 'note': '고객 답변 대기: 송금했나요?'},
            {'action_id': 'a2', 'action_type': 'PAYMENT_HOLD_REVIEW', 'status': 'IN_PROGRESS', 'note': '지급정지 가능 여부 검토'},
        ]
        adapter = CaseSnapshotAiAdapter()
        result = adapter.build_presentation(snapshot)
        self.assertNotIn('송금했나요?', result.case_brief.summary)
        self.assertNotIn('대응 업무 진행: 고객 답변 대기', '\n'.join(result.case_brief.next_checks))
        self.assertIn('지급정지 가능 여부 검토', result.case_brief.summary)
        self.assertEqual(result.case_brief.summary, adapter.build_presentation(snapshot).case_brief.summary)
        self.assertLessEqual(len(result.case_brief.summary.splitlines()), 4)

    def test_legacy_signal_is_projected_without_overwriting_natural_language(self):
        adapter = CaseSnapshotAiAdapter()
        self.assertEqual(adapter._readable_signal('Impersonation 신호', 'IMPERSONATION'), '기관 또는 다른 사람의 신분을 내세운 정황')
        self.assertEqual(adapter._readable_signal('직원 확인: 검찰 소속이라고 주장함', 'IMPERSONATION'), '직원 확인: 검찰 소속이라고 주장함')
        self.assertEqual(adapter._field_label('unrecognized_code'), '추가 확인 사항')

    def test_summary_does_not_carry_forward_long_history_or_all_action_notes(self):
        snapshot = self.snapshot()
        snapshot['diagnosis']['context']['summary'] = '지난 질문과 답변을 이어 붙인 오래된 기록입니다. ' * 50
        snapshot['actions'] = [
            {'action_id': f'a{i}', 'action_type': 'PAYMENT_HOLD_REVIEW', 'status': 'REQUESTED', 'note': f'업무 기록 {i}'}
            for i in range(25)
        ]
        result = CaseSnapshotAiAdapter().build_presentation(snapshot)
        self.assertNotIn('오래된 기록', result.case_brief.summary)
        self.assertNotIn('업무 기록 0 ', result.case_brief.summary)
        self.assertIn('업무 기록 24', result.case_brief.summary)
        self.assertLessEqual(len(result.case_brief.summary.splitlines()), 4)
