// Render the real component with historical UI triggers and explicit workflow data.
const assert = require('node:assert/strict');
const path = require('node:path');
const vm = require('node:vm');
const { buildSync } = require('esbuild');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const result = buildSync({
  entryPoints: [path.resolve(__dirname, '../src/customer/CustomerProgressPanel.tsx')],
  bundle: true, platform: 'node', format: 'cjs', packages: 'external', write: false,
});
const compiled = { exports: {} };
vm.runInNewContext(result.outputFiles[0].text, { require, module: compiled, exports: compiled.exports });
const { CustomerProgressPanel } = compiled.exports;
const render = (items, status = 'CLOSED') => renderToStaticMarkup(React.createElement(CustomerProgressPanel, {
  bundle: { case: { status, mode: 'RECOVERY' }, questions: [], customer_progress: items,
    recent_messages: [{ content: '피해구제 단계 확인: 구제 신청' }] },
  recovery: true, onRequestConfirmation: async () => {},
}));
const unknown = ['SAFETY', 'EVIDENCE', 'PAYMENT_HOLD', 'REPORT', 'RELIEF'].map((step) => ({
  step, label: step, status: 'UNKNOWN', status_label: '확인되지 않음',
  summary: '처리 기록 없음', next_action: '', reference: '', confirmed_at: null, confirmation_requested: false,
}));
assert.equal((render(unknown).match(/is-confirmed/g) || []).length, 0, 'guide selection and closed case must not imply completion');
const updated = unknown.map((item) => item.step === 'RELIEF' ? {
  ...item, status: 'COMPLETED', status_label: '담당자 완료 확인', reference: '접수 TEST-1',
  next_action: '보완 요청 대기', confirmed_at: '2026-09-05T10:00:00+09:00',
} : item);
const completed = render(updated);
assert.equal((completed.match(/is-confirmed/g) || []).length, 1, 'only the independently confirmed step gets a check');
assert.ok(completed.includes('접수 TEST-1') && completed.includes('보완 요청 대기'));
assert.ok(render(undefined).includes('완료 여부는 확인되지 않았습니다'), 'missing server state is explicitly unknown');
const requested = render(unknown.map((item) => ({ ...item, confirmation_requested: true })));
assert.equal((requested.match(/담당자에게 확인 요청<\/button>/g) || []).length, 0, 'pending requests do not offer duplicate submission');
assert.equal((requested.match(/담당자 확인 요청됨/g) || []).length, 5, 'pending request state remains visible instead of removing the control');
assert.equal((render(updated.map((item) => ({ ...item, status: 'SUBMITTED' }))).match(/is-confirmed/g) || []).length, 0, 'submission is not confirmed receipt');
console.log('Customer progress render checks: 7 passed');
