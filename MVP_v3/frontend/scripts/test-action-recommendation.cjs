const assert = require('node:assert/strict');
const path = require('node:path');
const vm = require('node:vm');
const {webcrypto} = require('node:crypto');
const {buildSync} = require('esbuild');
const React = require('react');

function component(props, casesApi, saveContextCommand = async () => {}) {
  const state = [], refs = [];
  const api = {...casesApi, createAction: casesApi.createAction ?? saveContextCommand};
  let cursor = 0, refCursor = 0;
  const react = {...React,
    useEffect() {},
    useState(initial) {
      const index = cursor++;
      if (!(index in state)) state[index] = typeof initial === 'function' ? initial() : initial;
      return [state[index], value => { state[index] = typeof value === 'function' ? value(state[index]) : value; }];
    },
    useRef(initial) { const index = refCursor++; return refs[index] ??= {current: initial}; },
  };
  const result = buildSync({
    entryPoints: [path.resolve(__dirname, '../src/components/CaseActionDialogs.tsx')],
    bundle: true, platform: 'node', format: 'cjs', packages: 'external', write: false,
    external: ['../api/client', '../api/cases', '../api/contextWorkspace'],
    define: {'import.meta.env': '{}'},
  });
  const module = {exports: {}};
  vm.runInNewContext(result.outputFiles[0].text, {
    module, exports: module.exports, crypto: webcrypto, Error,
    require: id => id === 'react' ? react : ({
      '../api/cases': {casesApi: api},
      '../api/contextWorkspace': {saveContextCommand},
      '../api/client': {},
    })[id] ?? require(id),
  });
  return {render() { cursor = 0; refCursor = 0; return module.exports.ActionDialog(props); }};
}

function find(element, predicate) {
  if (!element || typeof element !== 'object') return null;
  if (Array.isArray(element)) return element.map(child => find(child, predicate)).find(Boolean);
  if (predicate(element)) return element;
  return find(element.props?.children, predicate);
}

const text = value => Array.isArray(value) ? value.map(text).join('')
  : value && typeof value === 'object' ? text(value.props?.children)
  : typeof value === 'string' ? value : '';
const button = (tree, label) => {
  const found = find(tree, node => node.type === 'button' && text(node).includes(label));
  assert.ok(found, `Missing button: ${label}`);
  return found;
};
const field = (tree, type) => find(tree, node => node.type === type);
const flush = () => new Promise(resolve => setImmediate(resolve));
const props = {caseId: 'CASE-1', recovery: false, onDone: async () => {}, onClose: () => {}};

(async () => {
  let writes = 0;
  const empty = component(props, {generateWorkCard: async (caseId, cardType) => {
    assert.equal(caseId, 'CASE-1'); assert.equal(cardType, 'BANK_ACTION');
    return {suggested_action_type: 'EVIDENCE_PRESERVATION', suggested_action_note: '대화 캡처와 송금 내역을 보존합니다.'};
  }}, async () => { writes += 1; });
  button(empty.render(), 'AI에게 추천 받기').props.onClick(); await flush();
  assert.equal(field(empty.render(), 'select').props.value, 'EVIDENCE_PRESERVATION');
  assert.equal(field(empty.render(), 'textarea').props.value, '대화 캡처와 송금 내역을 보존합니다.');
  assert.equal(writes, 0, 'AI recommendation must not save or execute a task');
  field(empty.render(), 'select').props.onChange({target: {value: 'CUSTOMER_CALLBACK'}});
  field(empty.render(), 'textarea').props.onChange({target: {value: '담당자가 수정한 추천 초안'}});
  assert.equal(field(empty.render(), 'select').props.value, 'CUSTOMER_CALLBACK');
  assert.equal(field(empty.render(), 'textarea').props.value, '담당자가 수정한 추천 초안');

  const drafted = component(props, {generateWorkCard: async () => ({
    suggested_action_type: 'PAYMENT_HOLD_REVIEW', suggested_action_note: '지급정지 가능 여부를 확인합니다.',
  })});
  field(drafted.render(), 'select').props.onChange({target: {value: 'CUSTOMER_CALLBACK'}});
  field(drafted.render(), 'textarea').props.onChange({target: {value: '사용자가 작성한 내용'}});
  button(drafted.render(), 'AI에게 추천 받기').props.onClick(); await flush();
  assert.equal(field(drafted.render(), 'select').props.value, 'CUSTOMER_CALLBACK');
  assert.equal(field(drafted.render(), 'textarea').props.value, '사용자가 작성한 내용');
  button(drafted.render(), '추천 적용').props.onClick();
  assert.equal(field(drafted.render(), 'select').props.value, 'PAYMENT_HOLD_REVIEW');
  assert.equal(field(drafted.render(), 'textarea').props.value, '지급정지 가능 여부를 확인합니다.');

  let attempts = 0;
  const retry = component(props, {generateWorkCard: async () => {
    if (attempts++ === 0) throw new Error('일시적인 AI 오류');
    return {suggested_action_type: 'NOT_AN_OPTION', suggested_action_note: '담당자가 추가 조치를 검토합니다.'};
  }});
  field(retry.render(), 'textarea').props.onChange({target: {value: '보존할 사용자 초안'}});
  button(retry.render(), 'AI에게 추천 받기').props.onClick(); await flush();
  assert.equal(field(retry.render(), 'textarea').props.value, '보존할 사용자 초안');
  assert.equal(find(retry.render(), node => node.type?.name === 'DialogError' && node.props?.message)?.props.message, '일시적인 AI 오류');
  button(retry.render(), 'AI에게 추천 받기').props.onClick(); await flush();
  button(retry.render(), '추천 적용').props.onClick();
  assert.equal(field(retry.render(), 'select').props.value, 'OTHER');
  assert.equal(field(retry.render(), 'textarea').props.value, '담당자가 추가 조치를 검토합니다.');

  let resolveRecommendation;
  const pending = component(props, {generateWorkCard: () => new Promise(resolve => { resolveRecommendation = resolve; })});
  button(pending.render(), 'AI에게 추천 받기').props.onClick();
  assert.equal(button(pending.render(), 'AI에게 추천 받기').props.disabled, true);
  field(pending.render(), 'textarea').props.onChange({target: {value: '요청 중 작성한 내용'}});
  resolveRecommendation({suggested_action_type: 'CUSTOMER_CALLBACK', suggested_action_note: 'AI 초안'}); await flush();
  assert.equal(field(pending.render(), 'textarea').props.value, '요청 중 작성한 내용');
  assert.ok(button(pending.render(), '추천 적용'));

  const caseProps = {...props};
  let resolveOldCase;
  const changingCase = component(caseProps, {generateWorkCard: () => new Promise(resolve => { resolveOldCase = resolve; })});
  button(changingCase.render(), 'AI에게 추천 받기').props.onClick();
  caseProps.caseId = 'CASE-2'; changingCase.render();
  resolveOldCase({suggested_action_type: 'OTHER', suggested_action_note: '이전 Case 추천'}); await flush();
  assert.equal(field(changingCase.render(), 'textarea').props.value, '');

  let failureWrites = 0;
  const failure = component(props, {generateWorkCard: async () => { throw new Error('AI 연결 실패'); }}, async () => { failureWrites += 1; });
  field(failure.render(), 'textarea').props.onChange({target: {value: '직접 작성한 업무'}});
  button(failure.render(), 'AI에게 추천 받기').props.onClick(); await flush();
  assert.equal(field(failure.render(), 'textarea').props.value, '직접 작성한 업무');
  failure.render(); failure.render();
  assert.equal(field(failure.render(), 'textarea').props.value, '직접 작성한 업무', 'parent rerenders must preserve the local draft');
  find(failure.render(), node => node.type === 'form').props.onSubmit({preventDefault() {}}); await flush();
  assert.equal(failureWrites, 1, 'manual task save must remain available after AI failure');

  let cancelled = 0, cancelledWrites = 0;
  const cancel = component({...props, onClose: () => { cancelled += 1; }}, {generateWorkCard: async () => ({
    suggested_action_type: 'CUSTOMER_CALLBACK', suggested_action_note: '저장하지 않을 추천',
  })}, async () => { cancelledWrites += 1; });
  button(cancel.render(), 'AI에게 추천 받기').props.onClick(); await flush();
  button(cancel.render(), '취소').props.onClick();
  assert.equal(cancelled, 1); assert.equal(cancelledWrites, 0);

  console.log('Action recommendation: loading, BANK_ACTION mapping, editable/apply drafts, retry/fallback, case isolation, rerender stability, manual save, and cancel passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
