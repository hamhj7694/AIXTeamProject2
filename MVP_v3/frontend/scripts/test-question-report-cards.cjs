const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

const root = path.resolve(__dirname, '..');
const conversation = fs.readFileSync(path.join(root, 'src/components/SharedConversation.tsx'), 'utf8');
const dialogs = fs.readFileSync(path.join(root, 'src/components/CaseActionDialogs.tsx'), 'utf8');
const page = fs.readFileSync(path.join(root, 'src/pages/CaseRoomPage.tsx'), 'utf8');
const casesApi = fs.readFileSync(path.join(root, 'src/api/cases.ts'), 'utf8');
const timeline = fs.readFileSync(path.join(root, 'src/timeline.ts'), 'utf8');
const styles = fs.readFileSync(path.join(root, 'src/styles.css'), 'utf8');
const transpile = relative => ts.transpileModule(fs.readFileSync(path.join(root, relative), 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.ReactJSX },
}).outputText;
const load = (code, dependencies = {}) => {
  const moduleObject = { exports: {} };
  vm.runInNewContext(code, { module: moduleObject, exports: moduleObject.exports, require: id => dependencies[id] ?? require(id) });
  return moduleObject.exports;
};

assert.match(conversation, /고객 확인 질문 ·/);
assert.match(conversation, /question-dispatch-card/);
assert.match(styles, /\.question-dispatch-card/);
assert.match(conversation, /data-question-status/);
assert.match(conversation, /question\.status === 'PENDING'/);
assert.match(conversation, /현재 고객에게 표시 중/);
assert.match(conversation, /고객 노출 전/);
assert.match(conversation, /<EntryCard\s+entry=\{entry\}/);
assert.match(conversation, /buildConversationEntries\(bundle, view, channel\)/);
assert.doesNotMatch(conversation, /보고서 내용을 표시할 수 없습니다/);
assert.match(timeline, /kind: 'FINAL_REPORT'/);
assert.match(timeline, /Boolean\(bundle\.final_report\)/);
assert.match(conversation, /PDF 다운로드/);
assert.match(conversation, /Word 다운로드/);
assert.match(dialogs, /queueQuestions\(caseId, reviewItems\)[\s\S]*await onDone\(\)/);
assert.match(dialogs, /보낼 질문 묶음/);
assert.match(dialogs, /setReviewItems\(\[\.\.\.chosen\]\)/);
assert.match(conversation, /data-question-id=\{question\.question_id\}/);
assert.match(conversation, /질문 · 답변/);
assert.match(timeline, /question\.status === 'ANSWERED' && question\.answered_at && question\.answer_text\?\.trim\(\)/);
assert.match(page, /const refreshAfterMutation = async \(\) => \{ await load\(true, false\)/);
assert.match(page, /<QuestionDialog[\s\S]*onDone=\{refreshAfterMutation\}/);
assert.match(casesApi, /bundle\?view=bank/);

const timelineModule = load(transpile('src/timeline.ts'), {
  './api/cases': { CURRENT_BANK_USER: { user_id: 'staff-1' } },
});
const conversationModule = load(transpile('src/bank/conversationEntries.ts'), {
  '../timeline': timelineModule,
});
const question = (id, target, status, sequence, answer = null) => ({
  question_id: id, case_id: 'case-1', source: 'CUSTOMER_AGENT', target_field: target,
  question_text: `${id} 질문`, reason: '확인', priority: 'P1', status, sequence,
  requested_by: '담당자', asked_at: status === 'PENDING' ? null : `2026-09-19T00:0${sequence}:00Z`,
  answered_at: status === 'ANSWERED' ? `2026-09-19T00:1${sequence}:00Z` : null,
  options: [], allow_multi_select: false, question_message_id: status === 'PENDING' ? null : `qm-${id}`,
  answer_message_id: status === 'ANSWERED' ? `am-${id}` : null, answer_text: answer,
  question_version: 1, answer_payload: null, answer_question_version: status === 'ANSWERED' ? 1 : null,
  created_at: `2026-09-19T00:0${sequence}:00Z`,
});
const questions = [
  question('default', 'transfer_status', 'ASKED', 1),
  question('ai-context-1', 'ai-context-1', 'ASKED', 2),
  question('qf1-child', 'qf1:remote_control_app:parent-1', 'ANSWERED', 3, '앱 이름은 원격도우미예요'),
  question('staff-manual', 'staff-manual', 'PENDING', 4),
];
const message = (messageId, content, actorType = 'CUSTOMER_AGENT', channel = 'CUSTOMER') => ({
  message_id: messageId, case_id: 'case-1', actor_type: actorType, actor_user_id: 'user',
  actor_display_name: '표시 이름', actor_role: null, content, channel, audience: 'CUSTOMER',
  visibility: 'CUSTOMER', message_kind: 'CHAT', private_owner_user_id: null, mentions: [],
  reply_to_message_id: null, attachments: [], created_at: '2026-09-19T00:20:00Z',
});
const bundle = {
  questions,
  recent_messages: [
    message('qm-default', questions[0].question_text),
    message('qm-ai', questions[1].question_text),
    message('qm-qf1', questions[2].question_text),
    message(questions[2].answer_message_id, questions[2].answer_text, 'CUSTOMER'),
    message('ordinary', '일반 고객 메시지', 'CUSTOMER'),
    { ...message('team', '은행 내부 메시지', 'BANK_STAFF', 'TEAM'), audience: 'BANK_INTERNAL', visibility: 'BANK_INTERNAL' },
  ],
  verification_tasks: [], recent_actions: [], recent_events: [], final_report: null,
};
const customerEntries = conversationModule.buildConversationEntries(bundle, 'conversation', 'CUSTOMER');
const questionEntries = customerEntries.filter(entry => entry.kind === 'QUESTION');
assert.deepEqual(Array.from(questionEntries, entry => entry.data.question_id), ['default', 'ai-context-1', 'qf1-child', 'staff-manual']);
assert.deepEqual(Array.from(questionEntries, entry => entry.data.status), ['ASKED', 'ASKED', 'ANSWERED', 'PENDING']);
assert.equal(customerEntries.filter(entry => entry.kind === 'ANSWER').length, 1);
assert.equal(customerEntries.find(entry => entry.kind === 'ANSWER').data.question_id, 'qf1-child');
const inconsistent = question('not-answered', 'transfer_status', 'ASKED', 5, '아직 확정되지 않은 답변');
inconsistent.answered_at = '2026-09-19T00:15:00Z';
assert.equal(timelineModule.buildTimeline({ ...bundle, questions: [inconsistent] }, false).filter(entry => entry.kind === 'ANSWER').length, 0);
assert.deepEqual(Array.from(customerEntries.filter(entry => entry.kind === 'MESSAGE'), entry => entry.data.message_id), ['ordinary']);
assert.deepEqual(Array.from(conversationModule.buildConversationEntries(bundle, 'conversation', 'TEAM'), entry => entry.data.message_id), ['team']);

console.log('Question dispatch and final report card checks: 24 passed');
