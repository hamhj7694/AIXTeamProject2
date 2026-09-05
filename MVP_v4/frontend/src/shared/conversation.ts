import type { CaseEvent } from '../api/cases.ts';

// Message results enter here only after the future server message/visibility contract exists.
export type ConversationItem = {
  id: string; createdAt: string; title: string; body: string;
} & ({ kind: 'notice'; category: 'update' | 'brief' | 'verification' | 'suggestion' | 'action' | 'question' } |
     { kind: 'message'; senderId: string | null; senderRole: 'CUSTOMER' | 'BANK_STAFF' | 'AI'; channel: 'CUSTOMER' | 'BANK_INTERNAL' });

export function conversationPlacement(item: ConversationItem, actorId: string | null): 'left' | 'center' | 'right' {
  if (item.kind === 'notice') return 'center';
  return item.senderRole === 'BANK_STAFF' && actorId !== null && item.senderId === actorId ? 'right' : 'left';
}

export function projectEvent(event: CaseEvent): ConversationItem | null {
  if (event.visibility !== 'CUSTOMER' && event.visibility !== 'BANK_INTERNAL') return null;
  let title = '사건 업데이트';
  let body = '사건에 새로운 처리 내용이 반영되었습니다.';
  let category: 'update' | 'brief' | 'verification' | 'suggestion' | 'action' | 'question' = 'update';
  if (event.event_type === 'CASE_CREATED') { title = '사건 접수'; body = '사건이 생성되었습니다.'; }
  else if (event.payload.change === 'CASE_DELETED') { title = '휴지통 이동'; body = '관리자 확인을 거쳐 사건을 휴지통으로 이동했습니다.'; }
  else if (event.payload.change === 'CASE_RESTORED') { title = '사건 복구'; body = '관리자 확인을 거쳐 사건을 목록으로 복구했습니다.'; }
  else if (event.entity_type === 'CONTEXT_FEATURE') { title = '통화 분석 업데이트'; body = '새로운 통화 분석 정보가 사건에 반영되었습니다.'; }
  else if (event.entity_type === 'CASE_BRIEF') { title = '사건 정리'; body = '사건 정리 내용이 업데이트되었습니다.'; category = 'brief'; }
  else if (event.entity_type === 'VERIFICATION') { title = '확인 결과 업데이트'; body = '사건의 사실 확인 기록이 업데이트되었습니다.'; category = 'verification'; }
  else if (event.entity_type === 'AI_SUGGESTION') { title = '대응 제안'; body = '새로운 대응 제안이 등록되었습니다.'; category = 'suggestion'; }
  else if (event.entity_type === 'TASK') { title = '업무 처리'; body = '사건 대응 업무에 변경 사항이 있습니다.'; category = 'action'; }
  else if (event.entity_type === 'QUESTION') { title = '고객 확인 요청'; body = '고객 확인 질문의 처리 내용이 변경되었습니다.'; category = 'question'; }
  else if (event.entity_type === 'FACT') { title = '확인 내용 업데이트'; body = '사건의 확인 내용이 업데이트되었습니다.'; }
  return { id: event.id, createdAt: event.created_at, kind: 'notice', category, title, body };
}

export type Channel = 'BANK_INTERNAL' | 'CUSTOMER';
export function composerKey(caseId: string, channel: Channel): string { return `${caseId}:${channel}`; }
