const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'src/components/FactReviewDialog.tsx'), 'utf8');
const page = fs.readFileSync(path.join(root, 'src/pages/CaseRoomPage.tsx'), 'utf8');
const output = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
}).outputText;
const moduleObject = { exports: {} };
vm.runInNewContext(output, {
  module: moduleObject, exports: moduleObject.exports,
  require: (id) => id === 'react' || id === 'lucide-react' ? require(id) : {},
});

const { manualValue } = moduleObject.exports;
assert.equal(JSON.stringify(manualValue('transfer.actual.status', 'NOT_TRANSFERRED')), JSON.stringify({ status: 'NOT_TRANSFERRED' }));
assert.equal(JSON.stringify(manualValue('offender.claimed_organization', '검찰')), JSON.stringify({ name: '검찰', claimed: true }));
assert.equal(JSON.stringify(manualValue('offender.incident_claim', '계좌가 연루됨')), JSON.stringify({ text: '계좌가 연루됨' }));
const createFlow = source.slice(source.indexOf('const create = async'), source.indexOf('const confirm = async'));
assert.match(createFlow, /createContextFact\(caseId/);
assert.doesNotMatch(createFlow, /reviewContextFact/);
assert.match(source, /reviewContextFact\(caseId, fact\.fact_id, fact\.version, 'CONFIRM'/);
assert.match(source, /workspace\?\.proposed_facts/);
assert.match(page, /<FactReviewDialog caseId=\{caseId\}/);

console.log('Fact proposal, explicit review, and Case ROOM wiring checks passed');
