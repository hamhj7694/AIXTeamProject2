import React, { useEffect, useRef } from 'react';
import { Activity } from 'lucide-react';
import type { MvpEvent } from '../../services/mvpChatApi';

const labels: Record<string, string> = {
  CASE_CREATED: '사건 접수', MESSAGE_ADDED: '주요 대화·업무 알림', CUSTOMER_QUESTIONS_QUEUED: '고객 질문 구성',
  CUSTOMER_QUESTION_DISPATCHED: '고객 질문 전달', CUSTOMER_QUESTION_ANSWERED: '고객 답변 접수',
  CASE_FACT_PROPOSED: '확인 정보 후보', CASE_FACT_CONFIRMED: '확인 정보 확정', CASE_FIELD_UPDATED: 'Case 정보 변경',
  VERIFICATION_CREATED: '기관 확인 요청', VERIFICATION_UPDATED: '기관 확인 상태 변경', BANK_ACTION_ADDED: '은행 조치 기록',
  CASE_REPORT_FINALIZED: '보고서 확정',
};
const descriptions: Record<string, string> = {
  CASE_CREATED: '분석 결과를 바탕으로 사건이 접수되었습니다.', MESSAGE_ADDED: '업무와 연결된 대화 또는 알림이 추가되었습니다.',
  CUSTOMER_QUESTIONS_QUEUED: '은행에서 고객에게 확인할 질문 목록을 구성했습니다.', CUSTOMER_QUESTION_DISPATCHED: '다음 맞춤 질문이 고객 화면에 전달되었습니다.',
  CUSTOMER_QUESTION_ANSWERED: '고객 답변이 접수되어 확인 정보 후보로 전달됩니다.', CASE_FACT_PROPOSED: '고객 답변 또는 분석에서 확인할 정보 후보가 생성되었습니다.',
  CASE_FACT_CONFIRMED: '은행 담당자가 Case 확인 정보를 확정했습니다.', CASE_FIELD_UPDATED: 'Case의 업무 정보가 변경되었습니다.',
  VERIFICATION_CREATED: '확인 대상에 대한 사실 확인 업무가 등록되었습니다.', VERIFICATION_UPDATED: '기관 확인 상태 또는 결과가 변경되었습니다.',
  BANK_ACTION_ADDED: '은행 대응 조치가 기록되었습니다.', CASE_REPORT_FINALIZED: '사건 정보를 기준으로 보고서가 확정되었습니다.',
};
const colors: Record<string, string> = {
  CASE_CREATED: 'border-blue-400 bg-blue-50', MESSAGE_ADDED: 'border-violet-400 bg-violet-50',
  CUSTOMER_QUESTIONS_QUEUED: 'border-sky-400 bg-sky-50', CUSTOMER_QUESTION_DISPATCHED: 'border-sky-400 bg-sky-50',
  CUSTOMER_QUESTION_ANSWERED: 'border-cyan-400 bg-cyan-50', CASE_FACT_PROPOSED: 'border-amber-400 bg-amber-50',
  CASE_FACT_CONFIRMED: 'border-emerald-400 bg-emerald-50', CASE_FIELD_UPDATED: 'border-blue-500 bg-blue-50',
  VERIFICATION_CREATED: 'border-purple-400 bg-purple-50', VERIFICATION_UPDATED: 'border-purple-400 bg-purple-50',
  BANK_ACTION_ADDED: 'border-slate-400 bg-slate-50', CASE_REPORT_FINALIZED: 'border-emerald-400 bg-emerald-50',
};

const isCustomerDamageAlert = (event: MvpEvent) => event.event_type === 'CASE_FIELD_UPDATED'
  && event.payload.victim_transfer_status === 'YES';

export const CaseLiveLog: React.FC<{
  events: MvpEvent[];
  heightClassName?: string;
  onMessageEvent?: (messageId: string, channel?: string) => void;
  onWorkflowEvent?: (event: MvpEvent) => void;
  emergencyMessageId?: string;
}> = ({ events, heightClassName = 'min-h-[620px]', onMessageEvent, onWorkflowEvent, emergencyMessageId }) => {
  const filtered = events.filter((event) => event.event_type in labels);
  const scrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => { const node = scrollRef.current; if (node) node.scrollTop = node.scrollHeight; }, [filtered.length]);

  return <aside className={`flex ${heightClassName} min-h-0 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm`}>
    <header className="flex items-center gap-2 border-b border-slate-100 px-4 py-4"><Activity size={17} className="text-blue-600"/><h2 className="text-sm font-black">사건 진행 현황</h2></header>
    <div ref={scrollRef} className="flex-1 space-y-2 overflow-y-auto p-4">
      {filtered.length === 0 && <p className="rounded-xl bg-slate-50 p-4 text-xs text-slate-500">주요 진행 사항이 아직 없습니다.</p>}
      {filtered.map((event) => {
        const damageAlert = isCustomerDamageAlert(event);
        const messageId = typeof event.payload.message_id === 'string'
          ? event.payload.message_id
          : damageAlert ? emergencyMessageId ?? null : null;
        const channel = typeof event.payload.channel === 'string'
          ? event.payload.channel
          : damageAlert && emergencyMessageId ? 'AI_INTERNAL' : undefined;
        const title = damageAlert ? '고객 피해 발생 신고' : labels[event.event_type];
        const description = damageAlert ? '고객이 직접 사기 피해 발생을 알렸습니다. 즉시 보호 조치와 피해 금액 확인이 필요합니다.' : descriptions[event.event_type];
        const content = <><div className="flex items-center justify-between gap-2"><p className={`text-xs font-extrabold ${damageAlert ? 'text-rose-800' : 'text-slate-800'}`}>{title}</p><time className="text-[10px] text-slate-400">{new Date(event.occurred_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}</time></div><p className={`mt-1 text-[11px] leading-5 ${damageAlert ? 'text-rose-700' : 'text-slate-600'}`}>{description}</p></>;
        const className = `w-full rounded-r-lg border-l-2 p-2 pl-3 text-left ${damageAlert ? 'border-rose-500 bg-rose-50' : colors[event.event_type] ?? 'border-slate-200 bg-white'}`;
        const workflowLinked = event.event_type === 'VERIFICATION_CREATED' || event.event_type === 'VERIFICATION_UPDATED';
        return messageId
          ? <button key={event.event_id} onClick={() => onMessageEvent?.(messageId, channel)} className={`${className} hover:brightness-95`}>{content}</button>
          : workflowLinked
            ? <button key={event.event_id} onClick={() => onWorkflowEvent?.(event)} className={`${className} hover:brightness-95`}>{content}</button>
          : <article key={event.event_id} className={className}>{content}</article>;
      })}
    </div>
  </aside>;
};
