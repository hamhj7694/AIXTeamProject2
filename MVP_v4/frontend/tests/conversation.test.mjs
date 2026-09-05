import assert from 'node:assert/strict';
import { test } from 'node:test';
import { projectEvent, conversationPlacement, composerKey } from '../src/shared/conversation.ts';

const event={id:'stable-event',created_at:'2026-09-06T00:00:00Z',event_type:'ENTITY_CREATED',entity_type:'CONTEXT_FEATURE',visibility:'BANK_INTERNAL',payload:{risk_score:97.3,classification:'PHISHING',source_event_id:'browser-risk-text'}};
test('events become allowlisted human notices without leaking internal payload',()=>{
 const item=projectEvent(event);
 assert.equal(item.id,event.id);assert.equal(item.title,'통화 분석 업데이트');assert.equal(item.kind,'notice');
 for(const token of ['97.3','PHISHING','CONTEXT_FEATURE','BANK_INTERNAL','browser-risk-text']) assert.ok(!JSON.stringify(item).includes(token));
 assert.equal(projectEvent({...event,visibility:'AI_PRIVATE'}),null);
 assert.equal(projectEvent({...event,event_type:'CASE_CREATED'}).body,'사건이 생성되었습니다.');
});
test('functional results center; only current bank actor dialogue goes right',()=>{
 const notice=projectEvent(event);assert.equal(conversationPlacement(notice,'me'),'center');
 const message={id:'message',kind:'message',senderId:'me',senderRole:'BANK_STAFF',channel:'BANK_INTERNAL',body:'actual content',createdAt:'2026-09-06',title:'staff'};
 assert.equal(conversationPlacement(message,'me'),'right');
 assert.equal(conversationPlacement(message,'other'),'left');
 assert.equal(conversationPlacement(message,null),'left');
 assert.equal(conversationPlacement({...message,senderRole:'CUSTOMER'},'me'),'left');
 assert.equal(conversationPlacement({...message,senderRole:'AI'},'me'),'left');
 for(const kind of ['CASE_BRIEF','VERIFICATION','AI_SUGGESTION','TASK','QUESTION']) assert.equal(conversationPlacement(projectEvent({...event,entity_type:kind}),'me'),'center');
});
test('composer draft keys separate cases and customer/internal channels',()=>{
 assert.notEqual(composerKey('a','CUSTOMER'),composerKey('a','BANK_INTERNAL'));
 assert.notEqual(composerKey('a','CUSTOMER'),composerKey('b','CUSTOMER'));
});
