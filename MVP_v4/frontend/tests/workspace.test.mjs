import assert from 'node:assert/strict';
import { test } from 'node:test';
import { latestRisk, timelineFromEntityState, workspaceEntityState } from '../src/shared/workspace.ts';

const workspace = {
  case: { id: 'case-1', version: 2, revision: 2, fingerprint: 'a'.repeat(64), status: 'TRIAGE', mode: 'PREVENT' },
  participants: [{ id: 'participant-1', version: 1 }],
  events: [{ id: 'event-1', case_revision: 1, entity_type: 'CASE', event_type: 'CASE_CREATED', created_at: '2026-09-06T00:00:00Z', payload: {} }, { id: 'event-2', case_revision: 2, entity_type: 'CONTEXT_FEATURE', event_type: 'ENTITY_CREATED', created_at: '2026-09-06T00:01:00Z', payload: { risk_score: 97.6, classification: 'PHISHING' } }],
  context_features: [], facts: [], verifications: [],
};

test('workspace starts as entity-ID state and retains actual event order', () => {
  const state = workspaceEntityState(workspace);
  assert.equal(state.revision, 2);
  assert.equal(state.entities['case-1'].version, 2);
  assert.deepEqual(timelineFromEntityState(state).map((item) => item.id), ['event-1', 'event-2']);
});

test('risk uses stored model result first and a delta event only when feature content is not yet reloaded', () => {
  const state = workspaceEntityState(workspace);
  assert.deepEqual(latestRisk([], timelineFromEntityState(state)), { score: 97.6, classification: 'PHISHING' });
  assert.deepEqual(latestRisk([{ payload: { model_result: { final_risk_score: 20, label: 'NORMAL' } } }], []), { score: 20, classification: 'NORMAL' });
});
