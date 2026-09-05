import assert from 'node:assert/strict';
import { webcrypto } from 'node:crypto';
import { afterEach, test } from 'node:test';
import { getHealth } from '../src/api/health.ts';

const originalFetch = globalThis.fetch;
const originalCrypto = Object.getOwnPropertyDescriptor(globalThis, 'crypto');
afterEach(() => {
  globalThis.fetch = originalFetch;
  Object.defineProperty(globalThis, 'crypto', originalCrypto);
});

test('actual request builder uses same-origin API and fallback UUID header', async () => {
  Object.defineProperty(globalThis, 'crypto', { configurable: true, value: {
    getRandomValues: webcrypto.getRandomValues.bind(webcrypto),
  } });
  const controller = new AbortController();
  globalThis.fetch = async (url, options) => {
    assert.equal(url, '/api/v4/health');
    assert.equal(options.credentials, 'same-origin');
    assert.equal(options.signal, controller.signal);
    assert.match(options.headers['X-Request-ID'], /^[\da-f]{8}-[\da-f]{4}-4[\da-f]{3}-[89ab][\da-f]{3}-[\da-f]{12}$/);
    return Response.json({ service: 'csr-general-api', status: 'ok', contract_version: 'v4.health.1' });
  };
  assert.equal((await getHealth(controller.signal)).status, 'ok');
});

test('AI service or malformed response cannot pass as General API health', async () => {
  globalThis.fetch = async () => Response.json({ service: 'csr-ai-api', status: 'ok', contract_version: 'v4.health.1' });
  await assert.rejects(getHealth(), /서버 응답/);
});

test('server failure remains visible to caller', async () => {
  globalThis.fetch = async () => new Response(null, { status: 503 });
  await assert.rejects(getHealth(), /서버에 연결하지 못했습니다/);
});
