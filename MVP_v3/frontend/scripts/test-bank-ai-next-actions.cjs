const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

const root = path.resolve(__dirname, '..');
const read = (relative) => fs.readFileSync(path.join(root, relative), 'utf8');
const source = read('src/bank/aiNextActions.ts');
const moduleObject = { exports: {} };
vm.runInNewContext(ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText, { module: moduleObject, exports: moduleObject.exports });

const { reviewableVerifications } = moduleObject.exports;
const tasks = ['PENDING', 'IN_PROGRESS', 'ON_HOLD', 'COMPLETED', 'FAILED'].map((status, index) => ({
  verification_task_id: `v-${index}`, target: `기관 ${index}`, status,
}));
assert.deepEqual(Array.from(reviewableVerifications(tasks), (task) => task.status), ['PENDING', 'IN_PROGRESS', 'ON_HOLD']);
assert.equal(reviewableVerifications([]).length, 0);

const conversation = read('src/components/SharedConversation.tsx');
const page = read('src/pages/CaseRoomPage.tsx');
const dialog = read('src/components/CaseActionDialogs.tsx');
assert.match(conversation, /const latestBankAiEntry = \[\.\.\.entries\]\.reverse\(\)\.find\(/);
assert.match(conversation, /entry\.id === latestBankAiEntry\?\.id \? verificationTasks : \[\]/);
assert.match(conversation, /channel === 'TEAM' && onEditVerification \? reviewableVerifications\(bundle\.verification_tasks \?\? \[\]\) : \[\]/);
assert.match(conversation, /bankAiResponse && verificationTasks\.length > 0/);
assert.match(conversation, /onClick=\{\(\) => onEditVerification\(task\)\}/);
assert.match(conversation, /bankAiSummary\(message\.content\)/);
assert.match(conversation, /고객 확인 질문으로 가져오기/);
assert.match(page, /onEditVerification=\{\(task\) => setDialog\(\{ type: 'verification', task \}\)\}/);
assert.match(page, /<VerificationDialog caseId=\{caseId\} task=\{dialog\.task\}/);
assert.match(dialog, /const submit = async \(event: FormEvent\) => \{[\s\S]*?casesApi\.updateVerification\(caseId, task/);
assert.match(conversation, /onClick=\{onOpenQuestions\}/);
assert.doesNotMatch(conversation, /casesApi\.(queueQuestions|updateVerification|createVerification|finalize)\(/);

console.log('Bank AI next Action checks passed');
