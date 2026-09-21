const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

const root = path.resolve(__dirname, '..');
const read = (relative) => fs.readFileSync(path.join(root, relative), 'utf8');
const summary = read('src/bank/aiSummary.ts');
const conversation = read('src/components/SharedConversation.tsx');
const page = read('src/pages/CaseRoomPage.tsx');
const dialog = read('src/components/CaseActionDialogs.tsx');
const moduleObject = { exports: {} };
vm.runInNewContext(ts.transpileModule(summary, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText, {
  module: moduleObject, exports: moduleObject.exports,
});

const { bankAiSummary } = moduleObject.exports;
assert.equal(bankAiSummary('현재 송금 여부는 미확인입니다. 추가 확인이 필요합니다.'), '현재 송금 여부는 미확인입니다.');
assert.equal(bankAiSummary('[상황 판단]\n고객 진술은 확인 전입니다. 거래 기록을 검토하세요.'), '고객 진술은 확인 전입니다.');
assert.equal(bankAiSummary('현재 근거로 확정하기 어렵습니다.'), '현재 근거로 확정하기 어렵습니다.');
assert.equal(bankAiSummary(''), '');
assert.match(conversation, /message\.message_kind === 'AI_RESPONSE' && message\.actor_type === 'BANK_AGENT' && message\.channel === 'TEAM'/);
assert.match(conversation, /bankAiSummary\(message\.content\)/);
assert.match(conversation, /고객 확인 질문으로 가져오기/);
assert.match(page, /onOpenQuestions=\{\(\) => setDialog\(\{ type: 'questions' \}\)\}/);
assert.match(dialog, /casesApi\.questionCandidates\(caseId\)/);
assert.match(dialog, /casesApi\.queueQuestions\(caseId, reviewItems\)/);
const beforeSubmit = dialog.slice(dialog.indexOf('export const QuestionDialog'), dialog.indexOf('const submit = async'));
assert.doesNotMatch(beforeSubmit, /queueQuestions\(/);

console.log('Bank AI summary and question dialog handoff checks passed');
