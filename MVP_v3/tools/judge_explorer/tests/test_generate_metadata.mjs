import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { createReader, generate } from '../generate_metadata.mjs';

const toolRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const root = path.resolve(toolRoot, '..', '..');
const run = (suffix, generatedAt) => generate({ root, output: path.join(os.tmpdir(), `judge-explorer-test-${suffix}`), generatedAt });
const stable = (value) => JSON.stringify(value, Object.keys(value).sort());

test('AUTO content and manifest hash are deterministic', () => {
  const first = run('node-a', '2026-01-01T00:00:00Z').manifests;
  const second = run('node-b', '2026-01-02T00:00:00Z').manifests;
  for (const name of Object.keys(first)) {
    if (name === 'build_snapshot.json') continue;
    assert.deepEqual(first[name], second[name]);
  }
  assert.equal(first['build_snapshot.json'].manifest_hash, second['build_snapshot.json'].manifest_hash);
  assert.notEqual(first['build_snapshot.json'].metadata_generated_at, second['build_snapshot.json'].metadata_generated_at);
});

test('Scanner avoids env files and absolute paths', () => {
  const result = run('node-safety', '2026-01-01T00:00:00Z');
  assert.ok(result.readPaths.length > 0);
  assert.equal(result.readPaths.some((item) => path.basename(item).startsWith('.env')), false);
  const serialized = JSON.stringify(result.manifests);
  assert.equal(serialized.includes(root), false);
  assert.doesNotMatch(serialized, /[A-Za-z]:[/\\]Users[/\\]/);
});

test('Secret denylist rejects every dot-env filename before filesystem access', () => {
  const reader = createReader(root);
  assert.throws(() => reader.text(path.join(root, '.env')), /Denied environment file/);
  assert.throws(() => reader.text(path.join(root, '.env.example')), /Denied environment file/);
  assert.throws(() => reader.text(path.join(root, '.env.production')), /Denied environment file/);
});

test('CURRENT items always contain evidence', () => {
  const manifests = run('node-evidence', '2026-01-01T00:00:00Z').manifests;
  for (const component of manifests['architecture.json'].components) {
    if (component.status === 'CURRENT') assert.ok(component.evidence.length, component.id);
  }
  for (const service of manifests['ai_manifest.json'].services) {
    if (service.status === 'CURRENT') assert.ok(service.evidence.length, service.id);
  }
});

test('Artifact inspection is hash-only and safety facts follow code', () => {
  const ai = run('node-ai', '2026-01-01T00:00:00Z').manifests['ai_manifest.json'];
  assert.equal(ai.ml_artifact.inspection, 'FILE_METADATA_AND_SHA256_ONLY');
  assert.equal(ai.ml_artifact.hash_matches_code, true);
  assert.equal(ai.safety_facts.lexical_retrieval_owner, 'general-api');
  assert.equal(ai.safety_facts.case_support_snapshot, 'RULE_BASED_PROJECTION');
  assert.equal(ai.safety_facts.raw_input_storage_detected, true);
  assert.equal(ai.safety_facts.inactive_case_brief_llm_path, true);
  const source = fs.readFileSync(path.join(toolRoot, 'generate_metadata.mjs'), 'utf8');
  assert.equal(source.includes("from 'joblib'"), false);
  assert.equal(source.includes("from 'pickle'"), false);
});
