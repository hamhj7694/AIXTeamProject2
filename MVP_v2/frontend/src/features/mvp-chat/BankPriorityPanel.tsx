import React from 'react';
import { AlertTriangle, CheckCircle2, CircleDot, ListChecks } from 'lucide-react';

interface RiskItem { risk_id: string; claim: string; sourceLabel?: string; }
interface Props { tasks: string[]; risks: RiskItem[]; customerOnline: boolean; pendingQuestions: number; }

/** One-glance operational hierarchy for a bank operator. */
export const BankPriorityPanel: React.FC<Props> = ({ tasks, risks, customerOnline, pendingQuestions }) => (
  <section className="min-h-0 overflow-y-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
    <header className="border-b border-slate-100 p-4">
      <div className="flex items-center justify-between gap-2"><div className="flex items-center gap-2"><ListChecks size={17} className="text-blue-600"/><h2 className="text-sm font-black">우선 조치 및 위험요소</h2></div><span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-[10px] font-black ${customerOnline ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}><CircleDot size={11}/>고객 {customerOnline ? '상담 중' : '부재중'}</span></div>
      <p className="mt-1 text-[11px] text-slate-500">가장 중요한 행동부터 확인하고 완료하세요.</p>
    </header>
    <div className="space-y-4 p-4">
      {pendingQuestions > 0 && <div className="rounded-xl border border-blue-200 bg-blue-50 p-3"><p className="text-[10px] font-black text-blue-600">고객 응답 대기</p><p className="mt-1 text-sm font-black text-blue-950">질문 {pendingQuestions}건의 답변을 기다리고 있습니다.</p></div>}
      <div className="space-y-2">
        {tasks.length ? tasks.map((task, index) => <article key={task} className={`rounded-xl border p-3 ${index === 0 ? 'border-slate-900 bg-slate-900 text-white shadow-md' : 'border-blue-100 bg-blue-50 text-blue-950'}`}><p className={`text-[10px] font-black ${index === 0 ? 'text-blue-200' : 'text-blue-600'}`}>{index === 0 ? '가장 먼저' : `다음 업무 ${index + 1}`}</p><p className={`mt-1 font-bold leading-5 ${index === 0 ? 'text-sm' : 'text-xs'}`}>{task}</p></article>) : <p className="flex items-center gap-2 rounded-xl bg-emerald-50 p-3 text-xs font-bold text-emerald-800"><CheckCircle2 size={15}/>현재 확인이 필요한 우선 업무가 없습니다.</p>}
      </div>
      <div className="border-t border-slate-100 pt-4"><div className="flex items-center gap-2"><AlertTriangle size={15} className="text-amber-600"/><p className="text-xs font-black text-slate-800">확인된 위험요소</p></div><div className="mt-2 space-y-2">{risks.length ? risks.map((item) => <div key={item.risk_id} className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs font-semibold leading-5 text-amber-950">{item.sourceLabel && <span className="mb-1 block text-[10px] font-black text-amber-700">{item.sourceLabel}</span>}{item.claim}</div>) : <p className="rounded-xl bg-slate-50 p-3 text-xs text-slate-500">현재 등록된 위험요소가 없습니다.</p>}</div></div>
    </div>
  </section>
);
