// Real Chromium + running V4 HTTP services. No mocked fetch or fabricated UI items.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { setTimeout as pause } from 'node:timers/promises';
import { createUuid } from '../../src/shared/uuid.ts';

const root = resolve(import.meta.dirname, '../../..');
const cache = resolve(root, '.cache/browser-ux');
await mkdir(cache, { recursive: true });
const chrome = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', [
  '--headless=new', '--disable-gpu', '--no-first-run', '--remote-debugging-port=19222',
  '--window-size=1440,960',
  `--user-data-dir=${cache}/profile`, 'about:blank',
], { stdio: 'ignore', windowsHide: true });
let ws;
const checks=[];
try {
  let healthy=false;
  for(let i=0;i<100;i++) {
    try { healthy=(await fetch('http://127.0.0.1:15173/api/v4/health')).ok; if(healthy) break; } catch { }
    await pause(100);
  }
  assert.ok(healthy,'V4 General and proxy ready');
  let page;
  for(let i=0;i<100;i++) {
    try { page=await (await fetch('http://127.0.0.1:19222/json/new?http://127.0.0.1:15173/',{method:'PUT'})).json(); break; } catch { await pause(100); }
  }
  assert.ok(page,'Browser debugger started');
  ws=new WebSocket(page.webSocketDebuggerUrl);
  await new Promise(resolve=>ws.addEventListener('open',resolve,{once:true}));
  let sequence=0; const pending=new Map();
  ws.addEventListener('message',event=>{const msg=JSON.parse(event.data); const p=pending.get(msg.id); if(p){pending.delete(msg.id);msg.error?p.reject(new Error(msg.error.message)):p.resolve(msg.result);}});
  const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++sequence;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
  const run=async expression=>{const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true}); if(r.exceptionDetails) throw new Error(r.exceptionDetails.text+JSON.stringify(r.exceptionDetails.exception)); return r.result.value;};
  const wait=async expression=>{for(let i=0;i<100;i++){if(await run(`Boolean(${expression})`)) return;await pause(100);}throw new Error(`Browser wait: ${expression}`);};
  const click=async (selector,text)=>run(`(()=>{const e=[...document.querySelectorAll(${JSON.stringify(selector)})].find(e=>e.textContent.trim()===${JSON.stringify(text)});if(!e)throw Error('Missing button');e.click();})()`);
  const input=async (selector,value)=>run(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e)throw Error('Missing input');Object.getOwnPropertyDescriptor(e.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype,'value').set.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event('input',{bubbles:true}));})()`);
  await wait(`document.querySelector('.case-search') && !document.querySelector('.case-list [role="status"]')`);
  const base='http://127.0.0.1:15173/api/v4';
  const request=async(path,body)=>{const r=await fetch(base+path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});assert.ok(r.ok,await r.clone().text());return r.json();};
  const cid=createUuid();
  const title=`목록 UX 검증 ${cid.slice(0,8)}`;
  await request('/cases',{client_request_id:cid,customer_participant_id:'ux-smoke-customer',title,summary:'송금 여부를 확인하는 상담'});
  await click('.panel-heading button','새로고침');
  await wait(`document.querySelector('.case-list').textContent.includes(${JSON.stringify(title)})`);
  await input('.case-search',title);
  await wait(`document.querySelectorAll('.compact-row').length===1`);
  checks.push('natural-language search');
  await click('.case-filters button','피해 발생');
  await wait(`document.querySelectorAll('.compact-row').length===0`);
  await click('.case-filters button','의심');
  await wait(`document.querySelectorAll('.compact-row').length===1`);
  await click('.case-filters button','해결');
  await wait(`document.querySelectorAll('.compact-row').length===0`);
  await click('.case-filters button','전체');
  checks.push('status filters');
  await run(`document.querySelector('[aria-label="정렬 기준"]').value='id';document.querySelector('[aria-label="정렬 기준"]').dispatchEvent(new Event('change',{bubbles:true}));`);
  await click('[aria-label="정렬 방향"]','↓ 내림차순');
  await wait(`document.querySelector('[aria-label="정렬 방향"]').textContent.includes('오름차순')`);
  checks.push('sort controls');
  await run(`document.querySelector('.case-item').click()`);
  await wait(`document.querySelector('.case-item.selected') && document.querySelector('.timeline li')`);
  checks.push('Case selection');
  await click('.trash-action','삭제');
  await input('input[type=password]','wrong-admin');
  await click('.dialog-actions button','삭제');
  await wait(`document.querySelector('[role=dialog]').textContent.includes('올바르지 않습니다')`);
  assert.ok(process.env.ADMIN_CASE_PASSWORD,'Explicit browser smoke administrator credential required');
  await input('input[type=password]',process.env.ADMIN_CASE_PASSWORD);
  await click('.dialog-actions button','삭제');
  await wait(`!document.querySelector('[role=dialog]') && document.querySelectorAll('.compact-row').length===0`);
  await click('.trash-entry','휴지통');
  await wait(`document.querySelectorAll('.compact-row').length===1`);
  await click('.trash-action','복구');
  await input('input[type=password]',process.env.ADMIN_CASE_PASSWORD);
  await click('.dialog-actions button','복구');
  await wait(`!document.querySelector('[role=dialog]') && document.querySelectorAll('.compact-row').length===0`);
  await click('.trash-entry','사건 목록으로');
  await wait(`document.querySelectorAll('.compact-row').length===1`);
  checks.push('wrong/correct admin credential, soft delete, trash and restore');
  const events=(await request(`/cases/${cid}`)).events;
  assert.deepEqual(events.slice(-2).map(e=>e.payload.change),['CASE_DELETED','CASE_RESTORED']);
  checks.push('real persisted delete/restore audit');
  if (process.argv.includes('--conversation')) {
    await run(`document.querySelector('.case-item').click()`);
    await wait(`document.querySelector('#message-draft') && document.querySelectorAll('.conversation-notice').length===3`);
    const visibleText = await run(`document.querySelector('.case-list').textContent + document.querySelector('.timeline-panel').textContent`);
    for(const token of ['PHISHING','NORMAL','ENTITY_CREATED','CONTEXT_FEATURE','BANK_INTERNAL','revision']) assert.ok(!visibleText.includes(token), token);
    await wait(`document.querySelector('[role=switch]').getAttribute('aria-checked')==='true'`);
    await click('[role=switch]','AI 참여 ON');
    await wait(`document.querySelector('[role=switch]').getAttribute('aria-checked')==='false'`);
    await input('#message-draft','내부 초안 보존');
    await click('[aria-label="메시지 채널"] button','고객에게');
    assert.equal(await run(`document.querySelector('#message-draft').value`),'');
    await input('#message-draft','고객용 초안');
    await click('[aria-label="메시지 채널"] button','은행 내부');
    assert.equal(await run(`document.querySelector('#message-draft').value`),'내부 초안 보존');
    await run(`globalThis.savedEditor=document.querySelector('#message-draft');savedEditor.focus();savedEditor.setSelectionRange(2,5);savedEditor.dispatchEvent(new CompositionEvent('compositionstart',{bubbles:true,data:'입력'}));`);
    const current=(await request(`/cases/${cid}`)).case;
    await request(`/cases/${cid}/intake/test-text`,{client_request_id:createUuid(),expected_version:current.version,source_event_id:`conversation-${cid}`,text:'prosecutor urgent transfer password'});
    await wait(`document.querySelector('.timeline-panel').textContent.includes('통화 분석 업데이트')`);
    assert.equal(await run(`savedEditor===document.querySelector('#message-draft') && document.activeElement===savedEditor && savedEditor.value==='내부 초안 보존' && savedEditor.selectionStart===2 && savedEditor.selectionEnd===5`),true);
    await run(`savedEditor.dispatchEvent(new CompositionEvent('compositionend',{bubbles:true,data:'입력'}));`);
    checks.push('natural-language updates, AI OFF preserves real ML intake/polling, channel drafts/focus/selection/IME DOM preservation');
    await click('.function-toolbar button','고객에게 확인 질문');
    await wait(`document.querySelector('[role=dialog]')`);
    await input('[aria-label="직접 질문 추가"]','실제로 송금하셨나요?');
    await click('[role=dialog] button','추가');
    assert.equal(await run(`document.querySelector('.question-drafts').textContent.includes('실제로 송금하셨나요?')`),true);
    assert.equal(await run(`[...document.querySelectorAll('[role=dialog] button')].find(e=>e.textContent.includes('고객에게 전달')).disabled`),true);
    await click('[role=dialog] button','닫기');
    assert.equal(await run(`[...document.querySelectorAll('.composer-input button')].find(e=>e.textContent==='전송').disabled`),true);
    checks.push('question draft shell, no fake sending/provider');
    if (process.argv.includes('--personal')) {
      const before=(await request(`/cases/${cid}`)).case;
      const target=(await request(`/cases/${cid}`)).events[0].id;
      await wait(`document.querySelector('[data-item-id="${target}"] button') && !document.querySelector('[data-item-id="${target}"] button').disabled`);
      await run(`document.querySelector('[data-item-id="${target}"] button').click()`);
      await wait(`document.querySelector('[data-item-id="${target}"] button').getAttribute('aria-pressed')==='true'`);
      await run(`document.querySelector('[data-item-id="${target}"] button').click()`);
      await wait(`document.querySelector('[data-item-id="${target}"] button').getAttribute('aria-pressed')==='false'`);
      await run(`document.querySelector('[data-item-id="${target}"] button').click()`);
      await wait(`document.querySelector('[data-item-id="${target}"] button').getAttribute('aria-pressed')==='true'`);
      await click('.function-toolbar button','개인 메모');
      await input('[aria-label="개인 메모 내용"]','개인 업무 메모 보존');
      await click('[role=dialog] button','닫기');
      await click('.function-toolbar button','개인 메모');
      assert.equal(await run(`document.querySelector('[aria-label="개인 메모 내용"]').value`),'개인 업무 메모 보존');
      await click('[role=dialog] button','메모 추가');
      await wait(`document.querySelector('.personal-notes').textContent.includes('개인 업무 메모 보존')`);
      await click('[role=dialog] button','닫기');
      const after=(await request(`/cases/${cid}`)).case;
      assert.equal(before.revision,after.revision);
      const personal=await request(`/cases/${cid}/personal`);
      assert.equal(personal.notes.length,1);
      assert.equal(personal.bookmarks.filter(b=>b.active).length,1);
      const projection=await request(`/cases/${cid}/workspace`);
      assert.ok(!JSON.stringify(projection).includes('개인 업무 메모 보존'));
      await request(`/cases/${cid}/events`,{client_request_id:createUuid(),expected_version:after.version,event_type:'CASE_UPDATED',entity_type:'CASE',visibility:'CUSTOMER',payload:{change:'BROWSER_POLL_CHECK'}});
      await wait(`document.querySelectorAll('.conversation-notice').length===5`);
      await click('.function-toolbar button','내 북마크 (1)');
      await wait(`document.querySelector('.personal-bookmarks')`);
      await click('.personal-bookmarks button','사건 접수');
      await wait(`document.getElementById('conversation-${target}').classList.contains('bookmark-highlight')`);
      assert.equal(await run(`document.activeElement.id`),`conversation-${target}`);
      // Reload proves persistence independently of local React state.
      await call('Page.reload');
      await wait(`document.querySelector('.case-search')`);
      await input('.case-search',title);
      await wait(`document.querySelectorAll('.compact-row').length===1`);
      await run(`document.querySelector('.case-item').click()`);
      await wait(`document.querySelector('[data-item-id="${target}"] button')?.getAttribute('aria-pressed')==='true'`);
      await click('.function-toolbar button','개인 메모');
      await wait(`document.querySelector('.personal-notes').textContent.includes('개인 업무 메모 보존')`);
      await click('[role=dialog] button','닫기');
      checks.push('persistent private notes, bookmark add/cancel/persistence, unchanged shared revision, delta-stable target scroll/focus/highlight');
    }
  }
  if (process.argv.includes('--tasks')) {
    await wait(`document.querySelector('[aria-label="대응 업무"]')`);
    await click('.task-workspace button','업무 추가');
    await input('[aria-label="업무 제목"]','실제 업무 흐름 검증');
    await click('[role=dialog] button','저장');
    await wait(`!document.querySelector('[role=dialog]') && document.querySelector('.task-block')`);
    const taskId=await run(`document.querySelector('.task-block').dataset.taskId`);
    await click('.task-block button','업무 수정');
    await run(`const status=document.querySelector('[aria-label="업무 상태"]');status.value='COMPLETED';status.dispatchEvent(new Event('change',{bubbles:true}));`);
    await click('[role=dialog] button','저장');
    assert.equal(await run(`!!document.querySelector('[role=dialog]')`),true);
    await input('[aria-label="처리 결과"]','거래 내역 확인을 기록했습니다.');
    await click('[role=dialog] button','저장');
    await wait(`!document.querySelector('[role=dialog]') && document.querySelector('.task-block').textContent.includes('완료')`);
    await click('.task-block button','업무 수정');
    await run(`(()=>{const status=document.querySelector('[aria-label="업무 상태"]');status.value='IN_PROGRESS';status.dispatchEvent(new Event('change',{bubbles:true}));})()`);
    await click('[role=dialog] button','저장');
    await wait(`!document.querySelector('[role=dialog]') && document.querySelector('.task-block').textContent.includes('진행 중')`);
    assert.equal(await run(`document.querySelector('.task-block').dataset.taskId`),taskId);
    await click('.task-block button','업무 수정');
    await run(`(()=>{const status=document.querySelector('[aria-label="업무 상태"]');status.value='CANCELLED';status.dispatchEvent(new Event('change',{bubbles:true}));})()`);
    await input('[aria-label="취소 사유"]','중복 업무로 확인되어 취소합니다.');
    await click('[role=dialog] button','저장');
    await wait(`!document.querySelector('[role=dialog]') && document.querySelector('.task-block').textContent.includes('중복 업무')`);
    const updated=await request(`/cases/${cid}/workspace`);
    assert.equal(updated.tasks[0].id,taskId);
    assert.equal(updated.tasks[0].status,'CANCELLED');
    checks.push('actual task create/required completion result/reopen same ID/cancel reason/Entity-ID delta persistence');
  }
  const shot=await call('Page.captureScreenshot',{format:'png'});
  await writeFile(resolve(cache,'list.png'),Buffer.from(shot.data,'base64'));
  await writeFile(resolve(cache,'result.json'),JSON.stringify({passed:true,checks},null,2));
  console.log(JSON.stringify({passed:true,checks}));
  await call('Browser.close');
} finally { ws?.close(); chrome.kill(); }
