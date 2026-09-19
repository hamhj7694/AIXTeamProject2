const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'src/bank/consecutiveAiBatch.ts'), 'utf8');
const pageSource = fs.readFileSync(path.join(root, 'src/pages/CaseRoomPage.tsx'), 'utf8');
const composerSource = fs.readFileSync(path.join(root, 'src/components/ConversationComposer.tsx'), 'utf8');
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
});
const moduleObject = { exports: {} };
vm.runInNewContext(compiled.outputText, { module: moduleObject, exports: moduleObject.exports, require, setTimeout, clearTimeout });

const { ConsecutiveAiBatcher, buildConsecutiveAiPrompt } = moduleObject.exports;
const message = (id, content, caseId = 'case-1', requesterUserId = 'staff-1', saved = Promise.resolve(true)) => ({
  caseId, requesterUserId, messageId: id, content, saved,
});

(async () => {
  // A: 연속 3건은 원본 순서 그대로 한 번만 호출한다.
  const batchesA = [];
  let savedCount = 0;
  const saved = () => Promise.resolve().then(() => { savedCount += 1; return true; });
  const batcherA = new ConsecutiveAiBatcher(async items => {
    assert.equal(savedCount, 3);
    batchesA.push(items);
  }, 60_000);
  batcherA.enqueue(message('m1', '첫째', 'case-1', 'staff-1', saved()));
  batcherA.enqueue(message('m2', '둘째', 'case-1', 'staff-1', saved()));
  batcherA.enqueue(message('m3', '셋째', 'case-1', 'staff-1', saved()));
  await batcherA.flushNow();
  assert.equal(batchesA.length, 1);
  assert.deepEqual(Array.from(batchesA[0], item => item.messageId), ['m1', 'm2', 'm3']);
  assert.match(buildConsecutiveAiPrompt(batchesA[0]), /1\. 첫째[\s\S]*2\. 둘째[\s\S]*3\. 셋째/);

  // B: 앞 응답이 끝난 뒤 입력은 별도 요청이 된다.
  const batchesB = [];
  const batcherB = new ConsecutiveAiBatcher(async items => { batchesB.push(items); }, 60_000);
  batcherB.enqueue(message('m1', '첫 요청'));
  await batcherB.flushNow();
  batcherB.enqueue(message('m2', '다음 요청'));
  await batcherB.flushNow();
  assert.equal(batchesB.length, 2);

  // C: AI 실행 중 추가 입력은 유실·병렬 실행 없이 다음 묶음으로 처리한다.
  let releaseFirst;
  const firstPending = new Promise(resolve => { releaseFirst = resolve; });
  const batchesC = [];
  let active = 0;
  let maxActive = 0;
  const batcherC = new ConsecutiveAiBatcher(async items => {
    active += 1;
    maxActive = Math.max(maxActive, active);
    batchesC.push(items);
    if (batchesC.length === 1) await firstPending;
    active -= 1;
  }, 60_000);
  batcherC.enqueue(message('m1', '첫 요청'));
  const draining = batcherC.flushNow();
  await Promise.resolve();
  batcherC.enqueue(message('m2', '대기 1'));
  batcherC.enqueue(message('m3', '대기 2'));
  releaseFirst();
  await draining;
  assert.equal(maxActive, 1);
  assert.deepEqual(batchesC.map(items => Array.from(items, item => item.messageId)), [['m1'], ['m2', 'm3']]);

  // D: 다른 Case/requester는 같은 요청에 섞이지 않는다.
  const batchesD = [];
  const batcherD = new ConsecutiveAiBatcher(async items => { batchesD.push(items); }, 60_000);
  batcherD.enqueue(message('m1', 'case 1'));
  batcherD.enqueue(message('m2', 'case 2', 'case-2'));
  batcherD.enqueue(message('m3', 'staff 2', 'case-1', 'staff-2'));
  await batcherD.flushNow();
  assert.equal(batchesD.length, 3);
  assert.ok(batchesD.every(items => new Set(items.map(item => `${item.caseId}:${item.requesterUserId}`)).size === 1));

  // E: 새 coordinator는 과거 처리 메시지를 복원하거나 재호출하지 않는다.
  batcherD.dispose();
  let reconnectCalls = 0;
  const reconnected = new ConsecutiveAiBatcher(async () => { reconnectCalls += 1; }, 60_000);
  await reconnected.flushNow();
  assert.equal(reconnectCalls, 0);

  // 저장에 실패한 원본 MESSAGE는 AI 입력으로 전달하지 않는다.
  const batchesFailed = [];
  const failed = new ConsecutiveAiBatcher(async items => { batchesFailed.push(items); }, 60_000);
  failed.enqueue(message('ok', '저장 성공'));
  failed.enqueue(message('failed', '저장 실패', 'case-1', 'staff-1', Promise.resolve(false)));
  await failed.flushNow();
  assert.deepEqual(Array.from(batchesFailed[0], item => item.messageId), ['ok']);

  const retriedBatches = [];
  const retried = new ConsecutiveAiBatcher(async items => { retriedBatches.push(items); }, 60_000);
  retried.enqueue(message('retry', '재시도', 'case-1', 'staff-1', Promise.resolve(false)));
  retried.enqueue(message('retry', '재시도', 'case-1', 'staff-1', Promise.resolve(true)));
  await retried.flushNow();
  assert.deepEqual(Array.from(retriedBatches[0], item => item.messageId), ['retry']);

  // 실제 page는 각 MESSAGE 저장 Promise를 batch entry에 연결하고 즉시 AI를 호출하지 않는다.
  assert.match(pageSource, /const saved = deliverMessage\(item\)/);
  assert.match(pageSource, /const queueBatchedAi[\s\S]*aiBatcherRef\.current\?\.enqueue\([\s\S]*saved,/);
  const deliverySection = pageSource.slice(pageSource.indexOf('const deliverMessage'), pageSource.indexOf('const send ='));
  assert.doesNotMatch(deliverySection, /enqueueAiReply\(/);
  assert.match(pageSource, /const retryMessage[\s\S]*queueBatchedAi\(item, saved\)/);
  assert.match(composerSource, /const sendBlocked = busy && target !== 'TEAM'/);

  console.log('Consecutive Bank AI message batching scenarios A-E passed');
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
