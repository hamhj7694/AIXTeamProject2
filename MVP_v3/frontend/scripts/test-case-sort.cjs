const assert = require('node:assert/strict');
const path = require('node:path');
const vm = require('node:vm');
const { buildSync } = require('esbuild');

const result = buildSync({
  entryPoints: [path.resolve(__dirname, '../src/caseSort.ts')],
  bundle: true, platform: 'node', format: 'cjs', packages: 'external', write: false,
});
const moduleValue = { exports: {} };
vm.runInNewContext(result.outputFiles[0].text, { module: moduleValue, exports: moduleValue.exports, require });
const { compareCases } = moduleValue.exports;

const cases = [
  { case_id: 'VP-10', created_at: '2026-09-03T00:00:00Z', updated_at: '2026-09-04T00:00:00Z' },
  { case_id: 'VP-2', created_at: '2026-09-01T00:00:00Z', updated_at: '2026-09-06T00:00:00Z' },
  { case_id: 'VP-1', created_at: '2026-09-02T00:00:00Z', updated_at: '2026-09-05T00:00:00Z' },
];
const ids = (field, direction) => [...cases].sort((a, b) => compareCases(a, b, field, direction)).map((item) => item.case_id);
assert.deepEqual(ids('CASE_ID', 'ASC'), ['VP-1', 'VP-2', 'VP-10']);
assert.deepEqual(ids('CASE_ID', 'DESC'), ['VP-10', 'VP-2', 'VP-1']);
assert.deepEqual(ids('CREATED_AT', 'ASC'), ['VP-2', 'VP-1', 'VP-10']);
assert.deepEqual(ids('CREATED_AT', 'DESC'), ['VP-10', 'VP-1', 'VP-2']);
assert.deepEqual(ids('UPDATED_AT', 'ASC'), ['VP-10', 'VP-1', 'VP-2']);
assert.deepEqual(ids('UPDATED_AT', 'DESC'), ['VP-2', 'VP-1', 'VP-10']);
console.log('Case sort checks: 6 passed');
