import unittest
import os
from unittest.mock import patch
from fastapi.testclient import TestClient
import general_api.app.main as main
from general_api.app.domains.cases.repository import InMemoryCaseRepository
from contracts.user_text import user_text

class ContextDisplayTest(unittest.TestCase):
    def setUp(self):
        permission_patch = patch.dict(os.environ, {"MVP_OPEN_PERMISSIONS": "0"})
        permission_patch.start()
        self.addCleanup(permission_patch.stop)
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

    def archive(self, section, version, archived_text, archive_index, text=None):
        payload = {'expected_version': version, 'operation': 'ARCHIVE',
                   'archived_text': archived_text, 'archive_index': archive_index}
        if text is not None:
            payload['text'] = text
        return self.client.patch(self.url + f'/{section}?actor_user_id=staff', json=payload)

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

    def test_deleted_lines_are_archived_per_section_and_can_be_restored(self):
        sections = ('SUMMARY', 'EXPOSURE', 'CLAIM', 'DEMAND')
        for section in sections:
            response = self.archive(section, 0, f'{section} 삭제 항목', 0, f'{section} 활성 항목')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['display']['staff_text'], f'{section} 활성 항목')
            self.assertEqual(response.json()['archive']['deleted_by'], 'staff')

        refreshed = self.client.get(self.url + '?actor_user_id=staff').json()
        for section in sections:
            section_items = [item for item in refreshed if item['section'] == section]
            self.assertEqual(len(section_items), 2)
            self.assertEqual(next(item for item in section_items if item['semantic_key'] == 'display')['staff_text'], f'{section} 활성 항목')
            self.assertEqual(next(item for item in section_items if item['semantic_key'].startswith('display-archive:'))['staff_text'], f'{section} 삭제 항목')

        claim_items = [item for item in refreshed if item['section'] == 'CLAIM']
        display = next(item for item in claim_items if item['semantic_key'] == 'display')
        archive = next(item for item in claim_items if item['semantic_key'].startswith('display-archive:'))
        restored = self.client.patch(self.url + '/CLAIM?actor_user_id=staff', json={
            'expected_version': display['item_version'], 'operation': 'RESTORE_ARCHIVE',
            'archive_item_id': archive['item_id'], 'archive_version': archive['item_version'],
        })
        self.assertEqual(restored.status_code, 200, restored.text)
        self.assertEqual(restored.json()['display']['staff_text'], 'CLAIM 삭제 항목\nCLAIM 활성 항목')
        claim_after_refresh = [item for item in self.client.get(self.url + '?actor_user_id=staff').json() if item['section'] == 'CLAIM']
        self.assertEqual(len(claim_after_refresh), 1)
        self.assertEqual(claim_after_refresh[0]['semantic_key'], 'display')

    def test_archive_request_validation(self):
        self.assertEqual(self.client.patch(self.url + '/SUMMARY?actor_user_id=staff', json={
            'expected_version': 0, 'operation': 'ARCHIVE', 'archived_text': '누락된 위치',
        }).status_code, 422)
        self.assertEqual(self.client.patch(self.url + '/SUMMARY?actor_user_id=staff', json={
            'expected_version': 0, 'operation': 'RESTORE_ARCHIVE', 'archive_item_id': 'missing',
        }).status_code, 422)

    def test_multiple_deleted_lines_restore_in_original_order(self):
        self.assertEqual(self.archive('SUMMARY', 0, '첫째', 0, '둘째').status_code, 200)
        self.assertEqual(self.archive('SUMMARY', 1, '둘째', 0).status_code, 200)
        items = self.client.get(self.url + '?actor_user_id=staff').json()
        display = next(item for item in items if item['semantic_key'] == 'display')
        archives = sorted((item for item in items if item['semantic_key'].startswith('display-archive:')),
                          key=lambda item: item['archive_index'])
        self.assertEqual([item['archive_index'] for item in archives], [0, 1])
        self.assertIsNotNone(display['deleted_by'])

        for archive in reversed(archives):
            response = self.client.patch(self.url + '/SUMMARY?actor_user_id=staff', json={
                'expected_version': display['item_version'], 'operation': 'RESTORE_ARCHIVE',
                'archive_item_id': archive['item_id'], 'archive_version': archive['item_version'],
            })
            self.assertEqual(response.status_code, 200, response.text)
            display = response.json()['display']
        self.assertEqual(display['staff_text'], '첫째\n둘째')
        self.assertEqual(len(self.client.get(self.url + '?actor_user_id=staff').json()), 1)

    def test_generated_labels_preserve_urls_and_do_not_translate_substrings(self):
        self.assertEqual(user_text('personal_info_shared: 예 / Impersonation'), '개인정보 제공 여부: 예 / 기관·신분 사칭')
        self.assertEqual(user_text('https://example.com/personal_info_shared'), 'https://example.com/personal_info_shared')
        self.assertEqual(user_text('not_impersonation_field'), 'not_impersonation_field')
