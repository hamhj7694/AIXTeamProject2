const assert = require('node:assert/strict');
const path = require('node:path');
const vm = require('node:vm');
const { buildSync } = require('esbuild');

const result = buildSync({
  entryPoints: [path.resolve(__dirname, '../src/presentation.ts')],
  bundle: true, platform: 'node', format: 'cjs', packages: 'external', write: false,
});
const moduleValue = { exports: {} };
const FixedDate = class extends Date {
  static now() { return new Date('2026-09-05T05:30:00Z').getTime(); }
};
vm.runInNewContext(result.outputFiles[0].text, {
  module: moduleValue, exports: moduleValue.exports, require, Date: FixedDate,
});
const { relativeTime } = moduleValue.exports;

assert.equal(relativeTime('2026-09-05T05:29:40Z'), '방금 전');
assert.equal(relativeTime('2026-09-05T05:00:00Z'), '30분 전');
assert.equal(relativeTime('2026-09-05T02:30:00Z'), '3시간 전');
const old = relativeTime('2026-09-03T05:30:00Z');
assert.match(old, /2026/);
assert.match(old, /09|9/);
assert.match(old, /03|3/);
assert.match(old, /14:30|2:30/);
console.log('Relative time checks: 4 passed');
