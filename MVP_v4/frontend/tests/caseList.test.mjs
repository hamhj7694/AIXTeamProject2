import assert from 'node:assert/strict';
import { test } from 'node:test';
import { userStatus, selectCases } from '../src/shared/caseList.ts';
const rows = [
 {id:'b',case_number:'CSR-B',title:'사칭 전화',summary:'송금 전',status:'TRIAGE',loss_status:'UNKNOWN',risk_classification:'PHISHING',created_at:'2026-01-01',updated_at:'2026-03-01'},
 {id:'a',case_number:'CSR-A',title:'송금 상담',summary:'이체 확인',status:'ACTIVE',loss_status:'LOSS_CONFIRMED',risk_classification:'NORMAL',created_at:'2026-02-01',updated_at:'2026-02-01'},
 {id:'c',case_number:'CSR-C',title:'상담 종료',summary:'완료',status:'CLOSED',loss_status:'LOSS_CONFIRMED',created_at:'2026-03-01',updated_at:'2026-01-01'},
];
test('user taxonomy follows confirmed loss/closure, never ML classification',()=>{
 assert.deepEqual(rows.map(userStatus),['의심','피해 발생','해결 및 종결']);
 for(const status of ['의심','피해 발생','해결 및 종결']) assert.equal(selectCases(rows,'',status,'id',true).length,1);
 assert.equal(selectCases(rows,'','','id',true).length,3);
});
test('ID and natural-language search exclude internal classification',()=>{
 assert.equal(selectCases(rows,'CSR-A','','id',true)[0].id,'a');
 assert.equal(selectCases(rows,'사칭','','id',true)[0].id,'b');
 assert.equal(selectCases(rows,'이체','','id',true)[0].id,'a');
 assert.equal(selectCases(rows,'PHISHING','','id',true).length,0);
});
test('all sort keys/directions use actual Case data with stable tie breaker',()=>{
 for(const key of ['id','created_at','updated_at']) {
 const asc=selectCases(rows,'','',key,true); const desc=selectCases(rows,'','',key,false);
 assert.deepEqual(asc.map(x=>x.id),desc.map(x=>x.id).reverse());
 }
 assert.deepEqual(selectCases(rows,'','','updated_at',false).map(x=>x.id),['b','a','c']);
});
