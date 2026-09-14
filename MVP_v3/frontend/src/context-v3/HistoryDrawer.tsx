import React, { useEffect, useRef } from 'react';
import { Clock3, X } from 'lucide-react';
import type { CaseEvent } from '../api/types';

const eventLabels: Record<string, string> = {
  CASE_CREATED: '사건 생성', CASE_FIELD_UPDATED: '사건 정보 변경', MESSAGE_ADDED: '메시지 등록',
  CASE_MEMBER_UPDATED: '참여자 변경', CASE_ASSIGNEE_UPDATED: '주 담당자 변경', VERIFICATION_CREATED: '기관 확인 요청',
  VERIFICATION_UPDATED: '기관 확인 변경', BANK_ACTION_ADDED: '조치 기록', CASE_CHECKLIST_UPDATED: '체크리스트 변경',
  VOICE_SESSION_REQUESTED: '통화 분석 요청', VOICE_SESSION_PROCESSING: '통화 분석 중', VOICE_SESSION_COMPLETED: '통화 분석 완료',
  VOICE_SESSION_FAILED: '통화 분석 실패', TRANSCRIPT_SEGMENT_ADDED: '통화 내용 반영', CASE_REPORT_FINALIZED: '사건 종결',
  CASE_REOPENED: '사건 재개', CUSTOMER_QUESTIONS_QUEUED: '고객 질문 준비', CUSTOMER_QUESTION_DISPATCHED: '고객 질문 전달',
  CUSTOMER_QUESTION_ANSWERED: '고객 답변 등록', CASE_FACT_PROPOSED: '사실 제안', CASE_FACT_CONFIRMED: '사실 확정',
};
const actorLabels: Record<string, string> = { BANK_STAFF: '은행 직원', CUSTOMER: '고객', SYSTEM: '시스템', BANK_AGENT: '직원 지원 AI', CUSTOMER_AGENT: '고객 응대 AI', VERIFICATION: '기관 확인' };
const eventLabel = (value: string) => eventLabels[value] ?? '기타 사건 기록';
const actorLabel = (value: string) => actorLabels[value] ?? '알 수 없는 수행자';
export const HistoryDrawer: React.FC<{ open: boolean; events: CaseEvent[]; onClose: () => void }> = ({ open, events, onClose }) => {
  const closeRef = useRef<HTMLButtonElement>(null);
  const drawerRef = useRef<HTMLElement>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  useEffect(() => {
    if (!open) return;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    closeRef.current?.focus();
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); onCloseRef.current(); return; }
      if (event.key !== 'Tab') return;
      const focusable = [...(drawerRef.current?.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])') ?? [])];
      if (focusable.length === 0) { event.preventDefault(); return; }
      const first = focusable[0]; const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    window.addEventListener('keydown', handleKey);
    return () => { window.removeEventListener('keydown', handleKey); previousFocus?.focus(); };
  }, [open]);
  if (!open) return null;
  return <div className="context-history-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><aside ref={drawerRef} className="context-history-drawer" role="dialog" aria-modal="true" aria-labelledby="context-history-title" aria-describedby="context-history-description"><header><Clock3 size={18}/><div><h2 id="context-history-title">최근 사건 기록</h2><p id="context-history-description">사건의 주요 최근 활동을 확인할 수 있습니다.</p></div><button ref={closeRef} onClick={onClose} aria-label="최근 사건 기록 닫기"><X size={17}/></button></header><div>{events.length === 0 ? <p className="context-history-empty">표시할 최근 이벤트가 없습니다.</p> : events.map((event) => <article key={event.event_id}><header><strong title={eventLabels[event.event_type] ? undefined : event.event_type}>{eventLabel(event.event_type)}</strong><time>{new Date(event.occurred_at).toLocaleString('ko-KR')}</time></header><p title={actorLabels[event.actor_type] ? undefined : event.actor_type}>{actorLabel(event.actor_type)}</p></article>)}</div></aside></div>;
};
