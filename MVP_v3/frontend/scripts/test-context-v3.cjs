const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const source = (relative) => fs.readFileSync(path.resolve(__dirname, '..', relative), 'utf8');
const types = source('src/context-v3/types.ts');
const panel = source('src/context-v3/ContextPanelV3.tsx');
const sections = source('src/context-v3/sections.tsx');
const room = source('src/pages/CaseRoomPage.tsx');
const question = source('src/customer/CustomerQuestionCard.tsx');

for (const section of ['SUMMARY', 'EXPOSURE', 'IMPERSONATION_CONTACT', 'FRAUD_CIRCUMSTANCES', 'FACT_VERIFICATION', 'STAFF_ACTIONS', 'CUSTOMER_SHARE']) {
  assert.match(types, new RegExp(`\\b${section}\\b`));
}
assert.match(room, /import \{ ContextPanelV3 \}/);
assert.match(room, /<ContextPanelV3/);
assert.doesNotMatch(room, /import \{ CaseContextPanel \}/);
assert.match(panel, /reviewContextFact/);
assert.match(panel, /reviewContextSuggestion/);
assert.match(panel, /createContextTask/);
assert.match(panel, /completeContextTask/);
assert.match(sections, /기관 확인 열기/);
assert.match(question, /aria-pressed=\{active\}/);
assert.match(question, /question\.allow_multi_select/);
assert.match(question, /selected_option_ids/);
assert.match(question, /free_text/);

console.log('Context V3: exact sections, default switch, review/task/verification controls, and structured multi-answer contract passed');
