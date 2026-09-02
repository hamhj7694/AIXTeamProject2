import React from 'react';
import { Activity, ChevronDown } from 'lucide-react';
import type { MvpEvent } from '../../services/mvpChatApi';

const eventLabel: Record<string, string> = {
  CASE_CREATED: 'Case 생성', MESSAGE_ADDED: '메시지 추가', CASE_FIELD_UPDATED: 'Case 상태 변경',
  VERIFICATION_CREATED: '기관 검증 요청', VERIFICATION_UPDATED: '기관 검증 갱신', BANK_ACTION_ADDED: '은행 조치 기록',
  CASE_MEMBER_UPDATED: '참여자 역할 갱신', CASE_REPORT_FINALIZED: 'Case 종료 결과 생성',
};

export const CaseLiveLog: React.FC<{ events: MvpEvent[] }> = ({ events }) => <aside className="flex min-h-[620px] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
  <header className="flex items-center justify-between border-b border-slate-100 px-4 py-4"><div className="flex items-center gap-2"><Activity size={17} className="text-blue-600"/><h2 className="text-sm font-black">Case Live Log</h2></div><button className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100" aria-label="Log 필터는 준비 중"><ChevronDown size={16}/></button></header>
  <div className="flex-1 space-y-3 overflow-y-auto p-4">
    {events.length === 0 && <p className="rounded-xl bg-slate-50 p-4 text-xs leading-5 text-slate-500">저장된 Case Event가 없습니다.</p>}
    {[...events].reverse().map((event) => <article key={event.event_id} className="border-l-2 border-blue-200 pl-3"><div className="flex items-center justify-between gap-2"><p className="text-xs font-extrabold text-slate-800">{eventLabel[event.event_type] || event.event_type}</p><time className="shrink-0 text-[10px] text-slate-400">{new Date(event.occurred_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}</time></div><p className="mt-1 text-[11px] font-medium text-blue-600">{event.actor_type}</p><p className="mt-1 break-all text-[11px] leading-5 text-slate-500">{Object.keys(event.payload).length ? JSON.stringify(event.payload) : '상세 정보 없음'}</p></article>)}
  </div>
</aside>;
