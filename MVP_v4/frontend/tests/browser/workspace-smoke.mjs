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
  `--user-data-dir=${cache}/profile`, 'about:blank',
], { stdio: 'ignore', windowsHide: true });
let ws;
const checks=[];
try {
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
  const input=async (selector,value)=>run(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e)throw Error('Missing input');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event('input',{bubbles:true}));})()`);
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
  const shot=await call('Page.captureScreenshot',{format:'png'});
  await writeFile(resolve(cache,'list.png'),Buffer.from(shot.data,'base64'));
  await writeFile(resolve(cache,'result.json'),JSON.stringify({passed:true,checks},null,2));
  console.log(JSON.stringify({passed:true,checks}));
  await call('Browser.close');
} finally { ws?.close(); chrome.kill(); }
