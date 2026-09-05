import assert from 'node:assert/strict';
import { test } from 'node:test';
import { mergeCaseDelta } from '../src/shared/caseDelta.ts';

const current = { revision: 2, fingerprint: 'a'.repeat(64), entities: { a: { entity_id: 'a', version: 1, data: { value: 'draft' } }, b: { entity_id: 'b', version: 1, data: {} } } };
test('same fingerprint and stale revisions preserve the exact local state', () => {
  assert.strictEqual(mergeCaseDelta(current, { revision: 2, fingerprint: current.fingerprint, unchanged: true, upserts: [], deleted_entity_ids: [] }, new Set()), current);
  assert.strictEqual(mergeCaseDelta(current, { revision: 1, fingerprint: 'b'.repeat(64), unchanged: false, upserts: [], deleted_entity_ids: [] }, new Set()), current);
});
test('entity ID merge updates only remote entities and preserves local drafts', () => {
  const next = mergeCaseDelta(current, { revision: 3, fingerprint: 'b'.repeat(64), unchanged: false, upserts: [{ entity_id: 'a', version: 2, data: { value: 'server' } }, { entity_id: 'c', version: 1, data: {} }], deleted_entity_ids: ['b'] }, new Set(['a']));
  assert.equal(next.entities.a.data.value, 'draft'); assert.ok(!next.entities.b); assert.ok(next.entities.c);
});
