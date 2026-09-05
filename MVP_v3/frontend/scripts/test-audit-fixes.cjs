const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const source = file => fs.readFileSync(path.join(__dirname, '../src', file), 'utf8');
function evaluate(code, bindings = {}) {
  const context = { exports: {}, ...bindings };
  vm.runInNewContext(ts.transpileModule(code, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText, context);
  return context.exports;
}
const text = evaluate(source('userText.ts'));
const original = JSON.stringify({ report_id: 'final-audit', title: 'Report', executive_summary: 'Summary', verified_facts: ['personal_info_shared'] });
assert.equal(text.presentResponse({ actor_type: 'BANK_AGENT', message_kind: 'REPORT_CARD', content: original }).content, original);
assert.equal(text.presentResponse({content: '{"personal_info_shared": "YES"}'}).content, '{"personal_info_shared": "YES"}');
const raw = { staff_text: '  audit_reference_code\nconfirmed  ', answer_text: 'personal_info_shared', value: { key_name: 'my_code' }, note: 'unknown' };
assert.equal(JSON.stringify(text.presentResponse(raw)), JSON.stringify(raw));
assert.equal(text.userText('my_unregistered_code'), 'my_unregistered_code');
assert.equal(text.userText('Impersonation/Social Engineering'), '기관·신분 사칭/심리적 기만');
assert.equal(text.userText('SOCIAL_ENGINEERING / social-engineering'), '심리적 기만 / 심리적 기만');
assert.equal(text.userText('personal_info_shared.pdf'), 'personal_info_shared.pdf');
assert.equal(text.optionLabel('YES'), '예');
assert.equal(text.questionAnswerLabel('YES', ['YES', 'NO']), '예');
assert.equal(text.questionAnswerLabel('personal_info_shared 뜻이 뭐야?', ['YES', 'NO']), 'personal_info_shared 뜻이 뭐야?');
const options = text.presentResponse({ options: ['YES', 'NO'] }).options;
assert.equal(JSON.stringify(options), '["YES","NO"]');
assert.equal(text.presentResponse({ suggested_claim: 'Impersonation' }).suggested_claim, '기관·신분 사칭');
assert.equal(text.presentResponse({ task_id: 't1', title: 'unknown', description: 'my_text' }).title, 'unknown');
const client = evaluate(source('api/client.ts').replace('import.meta.env.VITE_API_BASE_URL', "''"), {
  require: () => text, Headers, fetch: async () => { throw new TypeError('Failed to fetch'); },
});
assert.equal(client.errorMessage({ detail: { code: 'CASE_NOT_FOUND', message: 'Case not found.' } }, 404).includes('사건'), true);
assert.equal(client.errorMessage({ detail: [{ loc: ['body', 'decision'], msg: "Input should be 'CONFIRM'" }] }, 422).includes('Input should'), false);
assert.equal(client.errorMessage({ detail: { code: 'ADMIN_AUTH_FAILED', message: 'Wrong password' } }, 403), '관리자 비밀번호가 올바르지 않습니다.');

// Execute the production delivery function with deferred API responses. No copied implementation.
function delivery(page) {
  const ast = ts.createSourceFile(page, source('pages/' + page), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  let fn;
  function visit(node) {
    if (ts.isVariableDeclaration(node) && node.name.getText(ast) === 'deliverMessage') fn = node.initializer.getText(ast);
    ts.forEachChild(node, visit);
  }
  visit(ast);
  assert.ok(fn);
  let resolve, reject;
  const pending = new Promise((yes, no) => { resolve = yes; reject = no; });
  const messages = [], callbacks = [], busy = [], errors = [];
  const state = {
    caseId: 'A', aiGenerationRef: { current: 1 }, activeCaseIdRef: { current: 'A' }, loadRequestRef: { current: 0 },
    pendingMessagesRef: { current: new Map() }, outboxRef: { current: new Map() },
    setBusy: value => busy.push(value), setError: value => errors.push(value), setNotice() {}, showMessage: msg => messages.push(msg),
    casesApi: { sendMessage: () => pending, sendCustomerMessage: () => pending },
    onMutated() {}, stripBankAiMention: s => s, enqueueAiReply: () => messages.push('AI'), enqueueCustomerAiReply: () => messages.push('AI'),
    load: () => messages.push('LOAD'), refresh: () => messages.push('LOAD'), window: { requestAnimationFrame: cb => callbacks.push(cb) },
  };
  const run = evaluate('export const deliverMessage = ' + fn, state).deliverMessage;
  const item = { message: { case_id: 'A', client_request_id: 'req' }, content: 'hello', target: 'TEAM', requestAi: true, files: [], attachmentIds: [] };
  return { state, messages, callbacks, busy, errors, resolve, reject, running: run(item) };
}
(async () => {
  await assert.rejects(client.request('/test'), /서버에 연결할 수 없습니다/);
  for (const page of ['CaseRoomPage.tsx', 'CustomerCaseRoomPage.tsx']) {
    for (const failure of [false, true]) {
      const test = delivery(page);
      test.state.activeCaseIdRef.current = 'B'; test.state.aiGenerationRef.current++;
      if (failure) test.reject(new Error('delayed failure')); else test.resolve({ case_id: 'A', message_id: 'saved' });
      await test.running;
      assert.equal(test.messages.length, 1); // initial optimistic message only
      assert.equal(test.callbacks.length, 0);
      assert.equal(test.busy.length, 1); // stale finally cannot clear B's busy state
      assert.equal(test.errors.length, 1); // no stale error added
    }
    const test = delivery(page);
    test.resolve({ case_id: 'A', message_id: 'saved' }); await test.running;
    assert.equal(test.messages.length, 2); // optimistic + persisted
    assert.equal(test.busy.at(-1), false);
    test.state.activeCaseIdRef.current = 'B'; test.state.aiGenerationRef.current++;
    test.callbacks.forEach(cb => cb());
    assert.equal(test.messages.length, 2); // no delayed AI work after navigation
  }
  console.log('Audit fixes: text/JSON/source/options/errors and both chat delivery races passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
