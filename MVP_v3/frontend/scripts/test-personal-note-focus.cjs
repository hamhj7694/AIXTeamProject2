const assert = require('node:assert/strict');
const path = require('node:path');
const vm = require('node:vm');
const {buildSync} = require('esbuild');
const React = require('react');

const sameDeps = (left, right) => left && right && left.length === right.length && left.every((value, index) => Object.is(value, right[index]));

function component(props, casesApi, browserWindow) {
  const state = [], refs = [], effects = [], callbacks = [];
  let stateCursor = 0, refCursor = 0, effectCursor = 0, callbackCursor = 0;
  const pendingEffects = [];
  const react = {...React,
    useState(initial) {
      const index = stateCursor++;
      if (!(index in state)) state[index] = typeof initial === 'function' ? initial() : initial;
      return [state[index], value => { state[index] = typeof value === 'function' ? value(state[index]) : value; }];
    },
    useRef(initial) { const index = refCursor++; return refs[index] ??= {current: initial}; },
    useCallback(callback, deps) {
      const index = callbackCursor++;
      if (!callbacks[index] || !sameDeps(callbacks[index].deps, deps)) callbacks[index] = {value: callback, deps};
      return callbacks[index].value;
    },
    useEffect(callback, deps) {
      const index = effectCursor++;
      if (!effects[index] || !sameDeps(effects[index].deps, deps)) pendingEffects.push({index, callback, deps});
    },
  };
  const result = buildSync({
    entryPoints: [path.resolve(__dirname, '../src/components/BankPersonalNotes.tsx')],
    bundle: true, platform: 'node', format: 'cjs', packages: 'external', write: false,
    external: ['../api/client', '../api/cases'], define: {'import.meta.env': '{}'},
  });
  const module = {exports: {}};
  vm.runInNewContext(result.outputFiles[0].text, {
    module, exports: module.exports, window: browserWindow, Error,
    require: id => id === 'react' ? react : ({'../api/cases': {casesApi}, '../api/client': {}})[id] ?? require(id),
  });
  return {
    refs,
    render() {
      stateCursor = 0; refCursor = 0; effectCursor = 0; callbackCursor = 0; pendingEffects.length = 0;
      const tree = module.exports.BankPersonalNotes(props);
      return tree;
    },
    commit() {
      for (const item of pendingEffects.splice(0)) {
        effects[item.index]?.cleanup?.();
        effects[item.index] = {deps: item.deps, cleanup: item.callback()};
      }
    },
  };
}

function find(element, predicate) {
  if (!element || typeof element !== 'object') return null;
  if (Array.isArray(element)) return element.map(child => find(child, predicate)).find(Boolean);
  if (predicate(element)) return element;
  return find(element.props?.children, predicate);
}

const flush = () => new Promise(resolve => setImmediate(resolve));

(async () => {
  const listeners = new Map();
  const browserWindow = {
    addEventListener(type, listener) { listeners.set(type, listener); },
    removeEventListener(type, listener) { if (listeners.get(type) === listener) listeners.delete(type); },
    confirm: () => true,
  };
  let loads = 0, creates = 0, firstClose = 0, latestClose = 0, focusCalls = 0;
  const props = {caseId: 'CASE-1', open: true, onClose: () => { firstClose += 1; }};
  const notes = component(props, {
    personalNotes: async () => { loads += 1; return []; },
    createPersonalNote: async (caseId, content) => {
      creates += 1; return {note_id: 'NOTE-1', case_id: caseId, author_id: 'staff', content, created_at: '2026-09-06T00:00:00Z', updated_at: '2026-09-06T00:00:00Z'};
    },
  }, browserWindow);

  let tree = notes.render();
  notes.refs[0].current = {focus() { focusCalls += 1; }};
  notes.commit(); await flush();
  tree = notes.render(); notes.commit();
  assert.equal(loads, 1); assert.equal(focusCalls, 1);

  const composer = () => find(notes.render(), node => node.type === 'textarea' && node.props?.placeholder);
  composer().props.onChange({target: {value: '검찰에서 계좌가...'}});
  props.onClose = () => { latestClose += 1; };
  for (let pollingCycle = 0; pollingCycle < 12; pollingCycle += 1) {
    tree = notes.render(); notes.commit();
    assert.equal(composer().props.value, '검찰에서 계좌가...');
  }
  assert.equal(loads, 1, 'parent polling rerenders must not reload the memo drawer');
  assert.equal(focusCalls, 1, 'parent polling rerenders must not move focus to the close button');
  assert.equal(composer().key, null, 'the composer textarea must not use a polling-dependent key');

  listeners.get('keydown')({key: 'Escape'});
  assert.equal(firstClose, 0); assert.equal(latestClose, 1, 'Escape must use the latest close callback');

  find(notes.render(), node => node.type === 'form').props.onSubmit({preventDefault() {}}); await flush();
  assert.equal(creates, 1); assert.equal(composer().props.value, '');
  assert.equal(focusCalls, 1, 'saving a memo must not steal focus');

  props.open = false; notes.render(); notes.commit();
  assert.equal(listeners.has('keydown'), false);
  props.open = true; notes.render(); notes.commit(); await flush();
  assert.equal(loads, 2); assert.equal(focusCalls, 2, 'reopening keeps the existing initial-focus behavior');

  console.log('Personal note focus: 12 polling-equivalent rerenders preserve draft and avoid focus steal; Escape, save, close, and reopen passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
