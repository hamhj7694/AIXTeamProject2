const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { buildSync } = require('esbuild');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');

const componentSource = fs.readFileSync(path.resolve(__dirname, '../src/customer/CustomerProgressPanel.tsx'), 'utf8');
const customerPageSource = fs.readFileSync(path.resolve(__dirname, '../src/pages/CustomerCaseRoomPage.tsx'), 'utf8');
const styles = fs.readFileSync(path.resolve(__dirname, '../src/styles.css'), 'utf8');
const editorSource = fs.readFileSync(path.resolve(__dirname, '../src/components/CustomerProgressEditor.tsx'), 'utf8');
const result = buildSync({
  entryPoints: [path.resolve(__dirname, '../src/customer/CustomerProgressPanel.tsx')],
  bundle: true, platform: 'node', format: 'cjs', packages: 'external', write: false,
});
const compiled = { exports: {} };
vm.runInNewContext(result.outputFiles[0].text, { require, module: compiled, exports: compiled.exports });
const { CustomerProgressPanel } = compiled.exports;

const step = (step, label, status, changes = {}) => ({
  step, label, status, status_label: status, summary: '처리 기록 없음', next_action: '',
  reference: '', confirmed_at: null, updated_at: null, updated_by: null, revision: 0,
  confirmation_requested: false, ...changes,
});
const fiveSteps = [
  step('SAFETY', '추가 송금·접촉 중단', 'COMPLETED', { summary: '추가 연락을 중단했습니다.', revision: 1 }),
  step('EVIDENCE', '증빙 자료 확보', 'NOT_APPLICABLE'),
  step('PAYMENT_HOLD', '은행 지급정지', 'IN_PROGRESS', { summary: '은행에서 확인 중입니다.', next_action: '은행 지급정지 결과를 기다려 주세요.', revision: 1 }),
  step('REPORT', '기관 신고 접수', 'SUBMITTED', { summary: '신고 요청 제출을 확인했습니다.', reference: '접수 TEST-1', confirmed_at: '2026-09-05T10:00:00+09:00', revision: 1 }),
  step('RELIEF', '피해구제 신청 접수', 'UNKNOWN'),
];
const render = (items = fiveSteps, questions = []) => renderToStaticMarkup(React.createElement(CustomerProgressPanel, {
  bundle: { case: { status: 'ACTIVE', mode: 'RECOVERY' }, questions, customer_progress: items, recent_messages: [] },
  recovery: true, onRequestConfirmation: async () => {},
}));

const mixed = render();
assert.equal((mixed.match(/class="customer-progress-step /g) ?? []).length, 5, 'exactly five compact rows render');
for (const label of ['추가 송금·접촉 중단', '증빙 자료 확보', '은행 지급정지', '기관 신고 접수', '피해구제 신청 접수']) assert.match(mixed, new RegExp(label));
assert.doesNotMatch(mixed, /public-progress-list|customer-progress-summary|피해 대응|상황 확인/);
assert.equal((mixed.match(/<details>/g) ?? []).length, 5, 'each compact row keeps an accessible detail disclosure');
assert.equal((mixed.match(/class="customer-progress-primary-action"/g) ?? []).length, 1, 'one unambiguous active next action is promoted');
assert.match(mixed, /지금 할 일[\s\S]*은행 지급정지 결과를 기다려 주세요/);

const completedRow = mixed.match(/<li[^>]*is-completed[\s\S]*?<\/li>/)?.[0] ?? '';
const submittedRow = mixed.match(/<li[^>]*is-submitted[\s\S]*?<\/li>/)?.[0] ?? '';
const progressRow = mixed.match(/<li[^>]*is-in_progress[\s\S]*?<\/li>/)?.[0] ?? '';
const unknownRow = mixed.match(/<li[^>]*is-unknown[\s\S]*?<\/li>/)?.[0] ?? '';
const notApplicableRow = mixed.match(/<li[^>]*is-not_applicable[\s\S]*?<\/li>/)?.[0] ?? '';
assert.match(completedRow, />완료</);
assert.match(progressRow, />처리 중</);
assert.match(submittedRow, />제출 확인 · 결과 대기</); assert.doesNotMatch(submittedRow, />완료</);
assert.match(unknownRow, />확인 전</); assert.doesNotMatch(unknownRow, />완료</);
assert.match(notApplicableRow, />해당 없음</); assert.doesNotMatch(notApplicableRow, />완료</);
assert.doesNotMatch(completedRow, /customer-progress-confirm/, 'completed step has no confirmation action');
assert.doesNotMatch(notApplicableRow, /customer-progress-confirm/, 'not-applicable step has no confirmation action');
assert.match(progressRow, /customer-progress-confirm/, 'in-progress step keeps confirmation action');
assert.match(submittedRow, /customer-progress-confirm/, 'submitted step keeps confirmation action');
assert.match(unknownRow, /customer-progress-confirm/, 'unknown step keeps confirmation action');
assert.match(submittedRow, /접수 TEST-1/); assert.match(submittedRow, /확인 시각/);

const allUnknown = ['SAFETY', 'EVIDENCE', 'PAYMENT_HOLD', 'REPORT', 'RELIEF'].map((id, index) => step(id, `확인 단계 ${index + 1}`, 'UNKNOWN'));
const unknownMarkup = render(allUnknown);
assert.equal((unknownMarkup.match(/>확인 전</g) ?? []).length, 5);
assert.doesNotMatch(unknownMarkup, /class="customer-progress-primary-action"|>완료</);
assert.match(render([]), /아직 확인된 진행 정보가 없습니다\. 완료 여부는 확인되지 않았습니다/);

const requested = render(fiveSteps.map((item) => ({ ...item, confirmation_requested: true })));
assert.equal((requested.match(/customer-progress-confirm/g) ?? []).length, 0, 'requested steps do not offer duplicate submission');
assert.equal((requested.match(/담당자 확인 요청됨 · 답변 대기 중/g) ?? []).length, 5);
assert.match(mixed, /aria-label="은행 지급정지 단계 담당자 확인 요청"/);
assert.match(componentSource, /disabled=\{pending !== null\}/);
assert.match(componentSource, /pending === item\.step \? '요청 저장 중…'/);
assert.match(componentSource, /error\?\.step === item\.step && <p role="alert"/);

assert.doesNotMatch(render(fiveSteps, []), /답변할 질문/);
const questions = [{ status: 'ASKED' }, { status: 'PENDING' }, { status: 'ANSWERED' }];
assert.match(render(fiveSteps, questions), /답변할 질문 2개/);
assert.match(mixed, /안내나 채팅만으로 신청·신고가 접수되지는 않습니다/);

assert.match(styles, /\.customer-progress-list/);
assert.match(styles, /\.customer-progress-list \{ margin: 10px 0 0; padding: 0; \}/);
assert.match(styles, /\.customer-progress-row/);
assert.match(styles, /@media \(max-width: 620px\)[\s\S]*\.customer-progress-status \{ grid-column: 2/);
assert.match(editorSource, /className="context-section public-progress-editor"/);
assert.match(editorSource, /className="public-progress-list"/);
assert.match(customerPageSource, /className="customer-details-toggle"/);
assert.match(customerPageSource, /aria-expanded=\{detailsOpen\}/);
assert.match(customerPageSource, /aria-controls="customer-side-panel"/);
assert.match(customerPageSource, /detailsOpen && <button[^>]+className="customer-side-scrim"/);
assert.match(customerPageSource, /customer-side-panel \$\{detailsOpen \? 'is-open' : ''\}/);
assert.match(customerPageSource, /event\.key === 'Escape'/);
assert.match(styles, /@media \(max-width: 980px\)[\s\S]*\.customer-header-actions > \.customer-details-toggle \{ display: inline-grid; \}/);
assert.match(styles, /\.customer-side-panel\.is-open \{ transform: translateX\(0\); \}/);
assert.match(styles, /\.customer-side-scrim \{ position: fixed;/);
assert.match(styles, /@media \(max-width: 1180px\)[\s\S]*\.app-context-toggle \{ display: inline-grid; \}/);
assert.doesNotMatch(styles, /@media \(max-width: 520px\)[\s\S]*\.customer-preview-link \{ display: none; \}/);
assert.match(styles, /\.customer-progress \.customer-progress-row strong \{ font-size: 12px; \}/);
assert.match(styles, /\.customer-progress \.customer-progress-status,[\s\S]*font-size: 10px/);
assert.match(styles, /\.customer-progress \.customer-progress-detail p,[\s\S]*font-size: 11px/);

console.log('Customer progress compact list and mobile panel checks: 44 passed');
