import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const currentDirectory = path.dirname(fileURLToPath(import.meta.url));
const backendDirectory = path.resolve(currentDirectory, '../..');
const contractDirectory = path.join(backendDirectory, 'contracts', 'ai_internal');
const fixtureDirectory = path.join(contractDirectory, 'fixtures');

const readJson = async (filePath) => JSON.parse(await readFile(filePath, 'utf8'));

const requiredSectionKeys = [
  'summary',
  'risk_context',
  'transfer_status',
  'exposure_status',
  'verification_status',
  'current_actions',
  'unresolved_items',
  'next_checks',
];

const requestSchema = await readJson(path.join(contractDirectory, 'report_initialize_request.schema.json'));
const responseSchema = await readJson(path.join(contractDirectory, 'report_initialize_response.schema.json'));
const requestFixture = await readJson(path.join(fixtureDirectory, 'report_initialize_request.json'));
const responseFixture = await readJson(path.join(fixtureDirectory, 'report_initialize_response.json'));

assert.equal(requestSchema.properties.schema_version.const, '1.0');
assert.equal(responseSchema.properties.schema_version.const, '1.0');
assert.equal(requestFixture.schema_version, '1.0');
assert.equal(responseFixture.schema_version, '1.0');
assert.equal(responseFixture.case_id, requestFixture.case.case_id);
assert.equal(responseFixture.request_id, requestFixture.request_id);
assert.equal(responseFixture.result.report_type, 'LIVE');

const actualSectionKeys = responseFixture.result.sections.map((section) => section.section_key).sort();
assert.deepEqual(actualSectionKeys, [...requiredSectionKeys].sort());

for (const section of responseFixture.result.sections) {
  assert.equal(section.operation, 'UPSERT');
  assert.equal(typeof section.content, 'object');
  assert.ok(Array.isArray(section.source_ids));
  assert.equal('version' in section, false, 'AI 응답은 DB version을 직접 관리하지 않습니다.');
  assert.equal('report_id' in section, false, 'AI 응답은 DB report_id를 직접 관리하지 않습니다.');
}

console.log('report initialize contract fixture: passed');
