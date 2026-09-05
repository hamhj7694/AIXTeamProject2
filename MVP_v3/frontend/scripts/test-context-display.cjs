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
assert.equal(record.note, 'personal_info_shared 확인'); // editable source, not a display label
assert.equal(record.content, 'personal_info_shared 뜻이 뭐야?');
assert.equal(eventLabel('UNKNOWN_INTERNAL_EVENT'), '사건 기록 변경');
assert.equal(priorityLabel('P0'), '긴급');
const {ContextEditing, EditableContext} = load('components/EditableContext.tsx');
const html = renderToStaticMarkup(React.createElement(ContextEditing, {caseId: 'VP-1'}, React.createElement(EditableContext, {section: 'SUMMARY', title: '현재 사건 요약', lines: ['사건 하나\n사건 둘\n사건 셋\n사건 넷\n사건 다섯'], summary: true})));
assert.equal((html.match(/<li/g) || []).length, 4);
assert.ok(html.includes('전체 내용 보기'));
assert.ok(html.includes('항목 추가·수정') && html.includes('숨기기'));
console.log('Context display checks: 10 passed');

const {SharedConversation} = load('components/SharedConversation.tsx');
const date = '2026-09-05T01:00:00Z';
const caseItem = {case_id: 'AUDIT', initial_brief: '사건 요약', created_at: date};
const report = {report_id: 'final-AUDIT', report_version: 1, title: '상세 보고서', executive_summary: 'Social Engineering', incident_summary: '기관 사칭', verified_facts: ['personal_info_shared: UNKNOWN'], actions_taken: [], resolution: '담당자 검토', follow_up: [], cautions: []};
const bundle = presentResponse({case: caseItem, recent_messages: [{message_id: 'report-msg', case_id: 'AUDIT', actor_type: 'BANK_AGENT', message_kind: 'REPORT_CARD', visibility: 'BANK_INTERNAL', content: JSON.stringify(report), created_at: date}]});
const reportHtml = renderToStaticMarkup(React.createElement(SharedConversation, {caseItem, bundle, view: 'conversation', bookmarkedIds: new Set(), onToggleBookmark() {}, onEditVerification() {}, onRetryMessage() {}, onDismissMessage() {}}));
assert.ok(reportHtml.includes('상세 보고서'));
assert.ok(reportHtml.includes('심리적 기만'));
assert.ok(reportHtml.includes('개인정보 제공 여부: 확인되지 않음'));
assert.ok(!reportHtml.includes('이전 보고서 형식'));
const canonical = { ...bundle, recent_messages: [], final_report: {report_id:'final-AUDIT', case_id:'AUDIT', report_version:1, created_at:date, sections:[{section_key:'verified_facts',content:{items:['personal_info_shared: UNKNOWN']}}]} };
const canonicalHtml = renderToStaticMarkup(React.createElement(SharedConversation, {caseItem,bundle:canonical,view:'conversation',bookmarkedIds:new Set()}));
assert.ok(canonicalHtml.includes('개인정보 제공 여부: 확인되지 않음'));
console.log('Report response → parse → render checks: 5 passed');
