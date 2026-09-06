const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { webcrypto } = require('node:crypto');
const { buildSync } = require('esbuild');

const root = path.resolve(__dirname, '..');
const entry = path.join(root, 'src/components/CaseActionDialogs.tsx');
const result = buildSync({
  entryPoints: [entry], bundle: true, platform: 'node', format: 'cjs', packages: 'external', write: false,
  external: ['../api/client', '../api/cases', '../api/contextWorkspace'], define: { 'import.meta.env': '{}' },
});
const moduleObject = { exports: {} };
vm.runInNewContext(result.outputFiles[0].text, {
  module: moduleObject, exports: moduleObject.exports, crypto: webcrypto,
  require: id => ({
    '../api/cases': { casesApi: {} }, '../api/contextWorkspace': {}, '../api/client': {},
  })[id] ?? require(id),
});

const { reconcileQuestionDraft } = moduleObject.exports;
const ai = (id, target, text, priority = 'P1') => ({ question_id: id, target_field: target, question_text: text, reason: '확인', priority });
const current = [
  ai('old-transfer', 'VICTIM_TRANSFER_STATUS', '사용자가 편집한 송금 질문'),
  ai('stale-auth', 'AUTH_INFO', '처리된 인증정보 질문'),
  ai('staff-manual', 'staff-manual', '직접 작성 질문'),
  ai('ai-context-abc', 'ai-context-abc', '사용자가 편집한 AI 맥락 질문'),
];
const authoritative = [
  ai('server-transfer', 'transfer_status', '서버 송금 질문'),
  ai('server-personal', 'personal_information_exposure', '개인정보 질문', 'P0'),
];
const reconciled = reconcileQuestionDraft(current, ['old-transfer', 'stale-auth', 'staff-manual', 'ai-context-abc'], authoritative);
assert.deepEqual(Array.from(reconciled.items, item => item.question_id), ['old-transfer', 'staff-manual', 'ai-context-abc', 'server-personal']);
assert.equal(reconciled.items[0].question_text, '사용자가 편집한 송금 질문');
assert.equal(reconciled.items[2].question_text, '사용자가 편집한 AI 맥락 질문');
assert.deepEqual(Array.from(reconciled.selected), ['old-transfer', 'staff-manual', 'ai-context-abc', 'server-personal']);

const source = fs.readFileSync(entry, 'utf8');
assert.match(source, /useEffect\(\(\) => \{[\s\S]*questionCandidates\(caseId\)/);
assert.match(source, /generateWorkCard\(caseId, 'QUESTION_PLAN',[\s\S]*questionCandidates\(caseId\)/);
assert.match(source, /generateWorkCard\(caseId, 'QUESTION_PLAN', itemsRef\.current\)/);
assert.match(source, /isPersistentQuestionDraft[\s\S]*ai-context-/);
const recommendationHandler = source.slice(source.indexOf('const recommendQuestions'), source.indexOf('const chosen'));
assert.doesNotMatch(recommendationHandler, /queueQuestions/);
assert.match(source, /created\.length === chosen\.length/);
assert.match(source, /created\.length === 0/);
assert.match(source, /개 중.*개를 등록했습니다/);
assert.match(source, /한 번에 하나씩 표시/);

console.log('Question dialog authoritative reconcile and 0/partial queue UX checks passed');
