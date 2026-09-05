import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
import general_api.app.main as main
from general_api.app.domains.cases.repository import InMemoryCaseRepository
from contracts.user_text import user_text

class ContextDisplayTest(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryCaseRepository()
        self.repo._records = [{'case_id': 'VP-1'}, {'case_id': 'VP-2'}]
        self.repo._members = [{'case_id': 'VP-1', 'user_id': 'staff', 'role': 'CHAT_OPERATOR', 'status': 'ACTIVE'}]
        self.patch = patch.object(main, 'repository', self.repo)
        self.patch.start()
        self.client = TestClient(main.app)
        self.url = '/api/cases/VP-1/context-display'

    def tearDown(self):
        self.client.close()
        self.patch.stop()

    def change(self, version, operation, text=None):
        return self.client.patch(self.url + '/SUMMARY?actor_user_id=staff', json={
            'expected_version': version, 'operation': operation, 'text': text})

    def test_edit_hide_restore_reset_and_conflict(self):
        response = self.change(0, 'EDIT', '송금 진술 확인\n기관 확인 필요')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['item_version'], 1)
        self.assertEqual(self.change(0, 'EDIT', '덮어쓰기').status_code, 409)
        self.assertEqual(self.change(1, 'DELETE').status_code, 200)
        hidden = self.client.get(self.url + '?actor_user_id=staff').json()[0]
        self.assertEqual(hidden['deleted_by'], 'staff')
        self.assertEqual(self.change(2, 'EDIT', '숨긴 내용 수정').status_code, 409)
        restored = self.change(2, 'RESTORE').json()
        self.assertEqual(restored['staff_text'], '송금 진술 확인\n기관 확인 필요')
        reset = self.change(3, 'RESET').json()
        self.assertIsNone(reset['staff_text'])
        self.assertIsNone(reset['deleted_by'])
        self.assertEqual(self.repo._case_facts, [])
        self.assertEqual(self.repo._actions, [])

    def test_member_scope_and_input_validation(self):
        # 새 Case 화면은 참여자 자동 등록과 편집본 조회가 동시에 실행될 수 있다.
        # 조회는 빈 목록으로 열리고, 실제 변경만 담당자 역할을 요구해야 한다.
        self.assertEqual(self.client.get(self.url + '?actor_user_id=outsider').json(), [])
        self.assertEqual(self.client.get('/api/cases/VP-2/context-display?actor_user_id=staff').json(), [])
        self.assertEqual(self.client.patch(self.url + '/SUMMARY?actor_user_id=outsider', json={
            'expected_version': 0, 'operation': 'EDIT', 'text': '권한 없는 변경'}).status_code, 403)
        self.assertEqual(self.client.patch('/api/cases/VP-2/context-display/SUMMARY?actor_user_id=staff', json={
            'expected_version': 0, 'operation': 'EDIT', 'text': '다른 사건 변경'}).status_code, 403)
        self.assertEqual(self.change(0, 'EDIT', '   ').status_code, 422)
        self.assertEqual(self.client.patch(self.url + '/FACT?actor_user_id=staff', json={'expected_version': 0, 'operation': 'DELETE'}).status_code, 422)

    def test_unregistered_viewer_cannot_read_staff_override(self):
        self.assertEqual(self.change(0, 'EDIT', '직원 전용 사건 정리').status_code, 200)
        self.assertEqual(self.client.get(self.url + '?actor_user_id=outsider').json(), [])
        visible = self.client.get(self.url + '?actor_user_id=staff').json()
        self.assertEqual(visible[0]['staff_text'], '직원 전용 사건 정리')

    def test_generated_labels_preserve_urls_and_do_not_translate_substrings(self):
        self.assertEqual(user_text('personal_info_shared: 예 / Impersonation'), '개인정보 제공 여부: 예 / 기관·신분 사칭')
        self.assertEqual(user_text('https://example.com/personal_info_shared'), 'https://example.com/personal_info_shared')
        self.assertEqual(user_text('not_impersonation_field'), 'not_impersonation_field')
