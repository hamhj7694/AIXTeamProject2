const assert = require('node:assert/strict');
const path = require('node:path');
const vm = require('node:vm');
const { buildSync } = require('esbuild');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
function load(file) {
  const result = buildSync({entryPoints: [path.resolve(__dirname, '../src/' + file)], bundle: true, platform: 'node', format: 'cjs', packages: 'external', write: false, define: {'import.meta.env': '{}'}});
  const module = {exports: {}};
  vm.runInNewContext(result.outputFiles[0].text, {require, module, exports: module.exports});
  return module.exports;
}
const {userText, presentResponse, eventLabel, priorityLabel} = load('userText.ts');
assert.equal(userText('personal_info_shared: 예 / Impersonation'), '개인정보 제공 여부: 예 / 기관·신분 사칭');
assert.equal(userText('https://example.com/personal_info_shared'), 'https://example.com/personal_info_shared');
const record = presentResponse({field: 'personal_info_shared', note: 'personal_info_shared 확인', actor_type: 'CUSTOMER', content: 'personal_info_shared 뜻이 뭐야?'});
assert.equal(record.field, 'personal_info_shared');
assert.equal(record.note, '개인정보 제공 여부 확인');
assert.equal(record.content, 'personal_info_shared 뜻이 뭐야?');
assert.equal(eventLabel('UNKNOWN_INTERNAL_EVENT'), '사건 기록 변경');
assert.equal(priorityLabel('P0'), '긴급');
const {ContextEditing, EditableContext} = load('components/EditableContext.tsx');
const html = renderToStaticMarkup(React.createElement(ContextEditing, {caseId: 'VP-1'}, React.createElement(EditableContext, {section: 'SUMMARY', title: '현재 사건 요약', lines: ['사건 하나\n사건 둘\n사건 셋\n사건 넷\n사건 다섯'], summary: true})));
assert.equal((html.match(/<li/g) || []).length, 4);
assert.ok(html.includes('전체 내용 보기'));
assert.ok(html.includes('항목 추가·수정') && html.includes('숨기기'));
console.log('Context display checks: 10 passed');
