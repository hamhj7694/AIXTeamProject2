const assert = require('node:assert/strict');
const path = require('node:path');
const vm = require('node:vm');
const {buildSync} = require('esbuild');

const output = buildSync({
  entryPoints: [path.resolve(__dirname, '../src/uuid.ts')],
  bundle: true,
  platform: 'browser',
  format: 'cjs',
  write: false,
}).outputFiles[0].text;

const loadGenerator = crypto => {
  const module = {exports: {}};
  vm.runInNewContext(output, {module, exports: module.exports, crypto, Uint8Array, Array, Error});
  return module.exports.generateUuid;
};

const uuidV4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

let nativeCalls = 0;
const nativeValue = '123e4567-e89b-42d3-a456-426614174000';
const nativeUuid = loadGenerator({
  randomUUID() { nativeCalls += 1; return nativeValue; },
  getRandomValues() { throw new Error('native randomUUID must be preferred'); },
})();
assert.equal(nativeUuid, nativeValue);
assert.equal(nativeCalls, 1);
assert.match(nativeUuid, uuidV4);

let fallbackCalls = 0;
const fallbackUuid = loadGenerator({
  getRandomValues(bytes) {
    fallbackCalls += 1;
    bytes.forEach((_, index) => { bytes[index] = index; });
    return bytes;
  },
})();
assert.equal(fallbackCalls, 1);
assert.match(fallbackUuid, uuidV4);
assert.equal(fallbackUuid, '00010203-0405-4607-8809-0a0b0c0d0e0f');

assert.throws(
  () => loadGenerator({})(),
  /안전한 요청 ID를 생성할 수 없습니다/,
);

console.log('UUID helper: native randomUUID, RFC 4122 v4 getRandomValues fallback, and no-insecure-fallback guard passed');
