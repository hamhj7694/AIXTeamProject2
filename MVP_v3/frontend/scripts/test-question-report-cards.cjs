const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const conversation = fs.readFileSync(path.join(root, 'src/components/SharedConversation.tsx'), 'utf8');
const timeline = fs.readFileSync(path.join(root, 'src/timeline.ts'), 'utf8');
const styles = fs.readFileSync(path.join(root, 'src/styles.css'), 'utf8');

assert.match(conversation, /고객에게 확인 질문 발송/);
assert.match(conversation, /question-dispatch-card/);
assert.match(styles, /\.question-dispatch-card/);
assert.doesNotMatch(conversation, /보고서 내용을 표시할 수 없습니다/);
assert.match(timeline, /kind: 'FINAL_REPORT'/);
assert.match(timeline, /Boolean\(bundle\.final_report\)/);
assert.match(conversation, /PDF 다운로드/);
assert.match(conversation, /Word 다운로드/);

console.log('Question dispatch and final report card checks: 8 passed');
