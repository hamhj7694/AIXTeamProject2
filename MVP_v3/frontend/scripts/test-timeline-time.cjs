const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

const root = path.resolve(__dirname, '..');
const source = file => fs.readFileSync(path.join(root, 'src', file), 'utf8');
const evaluate = (code, bindings = {}) => {
  const context = { exports: {}, ...bindings };
  vm.runInNewContext(ts.transpileModule(code, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText, context);
  return context.exports;
};

const presentation = evaluate(source('presentation.ts'), { require: () => ({}) });
assert.match(presentation.formatClock('2026-09-06T06:51:00+00:00'), /오후\s*03:51/);

const timelineSource = source('timeline.ts');
const timeline = evaluate(timelineSource, {
  require: () => ({ CURRENT_BANK_USER: { user_id: 'bank-user' } }),
});
const entries = timeline.buildTimeline({
  recent_messages: [{ message_id: 'message-1', actor_type: 'BANK_STAFF', actor_user_id: 'bank-user', content: '메시지', created_at: '2026-09-06T06:53:00+00:00' }],
  questions: [{ question_id: 'question-1', question_text: '질문', asked_at: '2026-09-06T06:51:00+00:00', answered_at: '2026-09-06T06:52:00+00:00', answer_text: 'NO' }],
}, false);
assert.deepEqual(Array.from(entries, entry => entry.kind), ['QUESTION', 'ANSWER', 'MESSAGE']);
assert.equal(entries.some(entry => entry.kind === 'BRIEF'), false);

const conversation = source('components/SharedConversation.tsx');
assert.match(conversation, /className="bank-initial-brief"/);
assert.equal((conversation.match(/className="bank-initial-brief"/g) ?? []).length, 1);
assert.doesNotMatch(timelineSource, /kind: 'BRIEF'/);

console.log('Timeline UTC/KST and pinned initial brief checks passed');
