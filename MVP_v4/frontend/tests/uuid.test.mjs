import assert from 'node:assert/strict';
import { webcrypto } from 'node:crypto';
import { afterEach, test } from 'node:test';
import { createUuid } from '../src/shared/uuid.ts';

const original = Object.getOwnPropertyDescriptor(globalThis, 'crypto');
const uuidV4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
function setCrypto(provider) { Object.defineProperty(globalThis, 'crypto', { configurable: true, value: provider }); }
afterEach(() => Object.defineProperty(globalThis, 'crypto', original));

test('secure context and localhost use the native provider with its receiver', () => {
  let called = 0;
  const provider = {
    randomUUID() { assert.equal(this, provider); called += 1; return '12ad9874-96ef-465a-8b4a-f3fd11be772a'; },
    getRandomValues() { throw new Error('Fallback must not run'); },
  };
  setCrypto(provider);
  assert.match(createUuid(), uuidV4);
  assert.equal(called, 1);
});

test('HTTP IP fallback sets RFC 4122 version and variant, preserving random bits', () => {
  setCrypto({ getRandomValues(bytes) { bytes.fill(255); return bytes; } });
  assert.equal(createUuid(), 'ffffffff-ffff-4fff-bfff-ffffffffffff');
  setCrypto({ getRandomValues(bytes) { bytes.fill(0); return bytes; } });
  assert.equal(createUuid(), '00000000-0000-4000-8000-000000000000');
});

test('fallback uses cryptographic entropy and produces distinct valid sample IDs', () => {
  setCrypto({ getRandomValues: webcrypto.getRandomValues.bind(webcrypto) });
  const values = Array.from({ length: 5000 }, createUuid);
  assert.equal(new Set(values).size, values.length);
  for (const value of values) assert.match(value, uuidV4);
});

test('missing secure randomness fails explicitly without Math.random', () => {
  setCrypto(undefined);
  assert.throws(createUuid, /안전한 요청 ID/);
});
