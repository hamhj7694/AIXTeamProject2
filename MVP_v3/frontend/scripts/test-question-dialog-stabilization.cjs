const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { webcrypto } = require('node:crypto');
const ts = require('typescript');

const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'src/components/CaseActionDialogs.tsx'), 'utf8');
const result = ts.transpileModule(source, {
  compilerOptions: { jsx: ts.JsxEmit.React, module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, esModuleInterop: true },
});
const moduleObject = { exports: {} };
vm.runInNewContext(result.outputText, {
  module: moduleObject, exports: moduleObject.exports, crypto: webcrypto,
  require: id => ({
    '../api/cases': { casesApi: {} }, '../api/contextWorkspace': {}, '../api/client': {},
    '../userText': { priorityLabel: (value) => value },
    '../presentation': { actionLabel: (value) => value },
    '../uuid': { generateUuid: () => 'test-id' },
  })[id] ?? require(id),
});

const { reconcileQuestionDraft } = moduleObject.exports;
const ai = (id, target, text, priority = 'P1') => ({ question_id: id, target_field: target, question_text: text, reason: '확인', priority });
const current = [
  ai('old-transfer', 'VICTIM_TRANSFER_STATUS', '사용자가 편집한 송금 질문'),
  ai('stale-auth', 'AUTH_INFO', '처리된 인증정보 질문'),
  ai('staff-manual', 'staff-manual', '직접 작성 질문'),
  ai('ai-context-abc', 'ai-context-abc', '사용자가 편집한 AI 맥락 질문'),
  ai('qf1:remote_control_app:parent-1', 'qf1:remote_control_app:parent-1', '설치한 앱의 이름을 알려주실 수 있나요?'),
];
const authoritative = [
  ai('server-transfer', 'transfer_status', '서버 송금 질문'),
  ai('server-personal', 'personal_information_exposure', '개인정보 질문', 'P0'),
];
const reconciled = reconcileQuestionDraft(current, ['old-transfer', 'stale-auth', 'staff-manual', 'ai-context-abc', 'qf1:remote_control_app:parent-1'], authoritative);
assert.deepEqual(Array.from(reconciled.items, item => item.question_id), ['old-transfer', 'server-personal', 'staff-manual', 'ai-context-abc', 'qf1:remote_control_app:parent-1']);
assert.equal(reconciled.items[0].question_text, '사용자가 편집한 송금 질문');
assert.equal(reconciled.items[3].question_text, '사용자가 편집한 AI 맥락 질문');
assert.equal(reconciled.items[4].question_text, '설치한 앱의 이름을 알려주실 수 있나요?');
assert.deepEqual(Array.from(reconciled.selected), ['old-transfer', 'staff-manual', 'ai-context-abc', 'qf1:remote_control_app:parent-1', 'server-personal']);
const remoteDraft = ai('candidate-remote_control_app', 'remote_control_app', '휴대폰에 원격 제어 앱을 설치하라는 안내를 받으셨나요?', 'P0');
const remoteCurrent = ai('candidate-remote_control_app', 'remote_control_app', '원격 제어 앱을 실제로 설치하셨나요?', 'P0');
const remoteReconciled = reconcileQuestionDraft([remoteDraft], [remoteDraft.question_id], [remoteCurrent]);
assert.equal(remoteReconciled.items[0].question_text, remoteCurrent.question_text);
const sevenCandidates = Array.from({ length: 7 }, (_, index) => ai(`q-${index}`, `target-${index}`, `질문 ${index}`));
assert.equal(sevenCandidates.length, 7);

assert.match(source, /useEffect\(\(\) => \{[\s\S]*questionCandidates\(caseId\)/);
assert.match(source, /generateWorkCard\(caseId, 'QUESTION_PLAN',[\s\S]*questionCandidates\(caseId\)/);
assert.match(source, /generateWorkCard\(caseId, 'QUESTION_PLAN', itemsRef\.current\)/);
assert.match(source, /isPersistentQuestionDraft[\s\S]*isDynamicQuestionDraft/);
assert.match(source, /isDynamicQuestionDraft[\s\S]*qf1:/);
assert.match(source, /AI 동적 추천/);
const recommendationHandler = source.slice(source.indexOf('const recommendQuestions'), source.indexOf('const chosen'));
assert.doesNotMatch(recommendationHandler, /queueQuestions/);
assert.match(source, /created\.length === reviewItems\.length/);
assert.match(source, /created\.length === 0/);
assert.match(source, /개 중.*개를 등록했습니다/);
assert.match(source, /한 번에 하나씩 표시/);
assert.doesNotMatch(source, /추가 후보.*개 보기/);
assert.doesNotMatch(source, /items\.slice\(5\).*selected\.includes/);

console.log('Question dialog authoritative reconcile and 0/partial queue UX checks passed');
