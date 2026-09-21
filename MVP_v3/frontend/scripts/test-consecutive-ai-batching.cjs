const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'src/bank/consecutiveAiBatch.ts'), 'utf8');
const bankPageSource = fs.readFileSync(path.join(root, 'src/pages/CaseRoomPage.tsx'), 'utf8');
const customerPageSource = fs.readFileSync(path.join(root, 'src/pages/CustomerCaseRoomPage.tsx'), 'utf8');
const composerSource = fs.readFileSync(path.join(root, 'src/components/ConversationComposer.tsx'), 'utf8');
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
});
const moduleObject = { exports: {} };
vm.runInNewContext(compiled.outputText, {
  module: moduleObject, exports: moduleObject.exports, require, setTimeout, clearTimeout, AbortController,
});

const { ConsecutiveAiBatcher, buildConsecutiveAiPrompt } = moduleObject.exports;
const stored = (id, order = Number(id.replace(/\D/g, '')) || 1) => ({
  messageId: id,
  createdAt: `2026-09-20T00:00:00.${String(order).padStart(3, '0')}Z`,
});
const message = (
  id, content, caseId = 'case-1', requesterUserId = 'staff-1',
  saved = Promise.resolve(stored(id)), channel = 'TEAM',
) => ({ caseId, requesterUserId, channel, messageId: id, content, saved });
const tick = () => new Promise(resolve => setTimeout(resolve, 0));

(async () => {
  // A: debounce 안의 A/B/C는 저장 순서대로 한 번만 호출한다.
  const batchesA = [];
  let savedCount = 0;
  const saved = id => Promise.resolve().then(() => { savedCount += 1; return stored(id); });
  const batcherA = new ConsecutiveAiBatcher(async items => {
    assert.equal(savedCount, 3);
    batchesA.push(items);
  }, 60_000);
  batcherA.enqueue(message('m1', '첫째', 'case-1', 'staff-1', saved('m1')));
  batcherA.enqueue(message('m2', '둘째', 'case-1', 'staff-1', saved('m2')));
  batcherA.enqueue(message('m3', '셋째', 'case-1', 'staff-1', saved('m3')));
  await batcherA.flushNow();
  assert.deepEqual(batchesA.map(items => Array.from(items, item => item.messageId)), [['m1', 'm2', 'm3']]);
  assert.match(buildConsecutiveAiPrompt(batchesA[0]), /1\. 첫째[\s\S]*2\. 둘째[\s\S]*3\. 셋째/);

  // B/C: A 실행 중 저장된 B/C는 A를 supersede하고 A+B+C로 한 번만 재호출한다.
  let releaseFirst;
  const firstPending = new Promise(resolve => { releaseFirst = resolve; });
  const batchesB = [];
  const supersededAtCompletion = [];
  const batcherB = new ConsecutiveAiBatcher(async (items, control) => {
    batchesB.push(Array.from(items, item => item.messageId));
    if (batchesB.length === 1) await firstPending;
    supersededAtCompletion.push(control.isSuperseded());
  }, 60_000);
  batcherB.enqueue(message('m1', 'A'));
  const firstDrain = batcherB.flushNow();
  await tick();
  batcherB.enqueue(message('m2', 'B'));
  batcherB.enqueue(message('m3', 'C'));
  await tick();
  releaseFirst();
  await firstDrain;
  await batcherB.flushNow();
  assert.deepEqual(batchesB, [['m1'], ['m1', 'm2', 'm3']]);
  assert.deepEqual(supersededAtCompletion, [true, false]);

  // D: superseded generation의 늦은 실패는 drain 실패로 전파하지 않고 최종 batch를 계속한다.
  let rejectFirst;
  const lateFailure = new Promise((_, reject) => { rejectFirst = reject; });
  const batchesC = [];
  const batcherC = new ConsecutiveAiBatcher(async items => {
    batchesC.push(Array.from(items, item => item.messageId));
    if (batchesC.length === 1) await lateFailure;
  }, 60_000);
  batcherC.enqueue(message('m1', 'A'));
  const failingDrain = batcherC.flushNow();
  await tick();
  batcherC.enqueue(message('m2', 'B'));
  await tick();
  rejectFirst(new Error('late provider failure'));
  await failingDrain;
  await batcherC.flushNow();
  assert.deepEqual(batchesC, [['m1'], ['m1', 'm2']]);

  // 서버가 먼저 STALE을 반환해도 로컬 pending이 있으면 active A를 재결합한다.
  let releaseStale;
  let saveSecond;
  const staleResponse = new Promise(resolve => { releaseStale = resolve; });
  const secondSaved = new Promise(resolve => { saveSecond = resolve; });
  const staleRaceBatches = [];
  const staleRace = new ConsecutiveAiBatcher(async (items, control) => {
    staleRaceBatches.push(Array.from(items, item => item.messageId));
    if (staleRaceBatches.length === 1) {
      await staleResponse;
      assert.equal(control.supersedeIfPending(), true);
    }
  }, 60_000);
  staleRace.enqueue(message('m1', 'A'));
  const staleDrain = staleRace.flushNow();
  await tick();
  staleRace.enqueue(message('m2', 'B', 'case-1', 'staff-1', secondSaved));
  releaseStale();
  await staleDrain;
  saveSecond(stored('m2'));
  await staleRace.flushNow();
  assert.deepEqual(staleRaceBatches, [['m1'], ['m1', 'm2']]);

  // E/F: 다른 Case/requester/channel은 서로 supersede하거나 같은 batch에 섞이지 않는다.
  const batchesD = [];
  const batcherD = new ConsecutiveAiBatcher(async items => { batchesD.push(items); }, 60_000);
  batcherD.enqueue(message('m1', 'case 1'));
  batcherD.enqueue(message('m2', 'case 2', 'case-2'));
  batcherD.enqueue(message('m3', 'staff 2', 'case-1', 'staff-2'));
  batcherD.enqueue(message('m4', 'customer', 'case-1', 'staff-1', Promise.resolve(stored('m4', 4)), 'CUSTOMER'));
  await batcherD.flushNow();
  assert.equal(batchesD.length, 4);
  assert.ok(batchesD.every(items => new Set(items.map(item => `${item.caseId}:${item.requesterUserId}:${item.channel}`)).size === 1));

  // G: 저장 실패 MESSAGE는 source batch에 포함하지 않는다.
  const batchesFailed = [];
  const failed = new ConsecutiveAiBatcher(async items => { batchesFailed.push(items); }, 60_000);
  failed.enqueue(message('ok', '저장 성공'));
  failed.enqueue(message('failed', '저장 실패', 'case-1', 'staff-1', Promise.resolve(false)));
  await failed.flushNow();
  assert.deepEqual(Array.from(batchesFailed[0], item => item.messageId), ['ok']);

  // H: 새 coordinator는 reload 전 과거 MESSAGE를 임의로 복원하거나 재호출하지 않는다.
  batcherD.dispose();
  let reconnectCalls = 0;
  const reconnected = new ConsecutiveAiBatcher(async () => { reconnectCalls += 1; }, 60_000);
  await reconnected.flushNow();
  assert.equal(reconnectCalls, 0);

  // 실제 Bank/Customer page가 저장 결과와 source_message_ids를 coordinator에 연결한다.
  assert.match(bankPageSource, /const saved = deliverMessage\(item\)/);
  assert.match(bankPageSource, /messages\.map\(\(message\) => message\.messageId\)/);
  assert.match(bankPageSource, /control\?\.isSuperseded\(\)/);
  assert.match(customerPageSource, /const saved = deliverMessage\(item\)/);
  assert.match(customerPageSource, /buildConsecutiveCustomerAiPrompt\(messages\)/);
  assert.match(customerPageSource, /control\.isSuperseded\(\)/);
  assert.match(composerSource, /const sendBlocked = busy && target !== 'TEAM'/);

  console.log('Consecutive Bank/Customer AI batching and supersede scenarios A-H passed');
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
