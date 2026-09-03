import React, { useState } from 'react';
import { Bot, CheckCircle2, Headphones, ShieldAlert } from 'lucide-react';
import { recoverySteps } from './recoverySteps';

interface Props {
  stepId: string;
  onRequest: (kind: 'AI_ADVICE' | 'HUMAN_HANDOFF', step: string) => Promise<void> | void;
}

export const RecoveryStepDetailCard: React.FC<Props> = ({ stepId, onRequest }) => {
  const [requesting, setRequesting] = useState(false);
  const [requested, setRequested] = useState<string | null>(null);
  const step = recoverySteps.find((item) => item.id === stepId);
  if (!step) return null;
  const Icon = step.icon;
  const request = async (kind: 'AI_ADVICE' | 'HUMAN_HANDOFF') => {
    if (requesting) return;
    setRequesting(true);
    try { await onRequest(kind, step.title); setRequested(kind); } finally { setRequesting(false); }
  };

  return <section className="rounded-3xl border border-rose-300 bg-white p-5 shadow-lg ring-4 ring-rose-50 sm:p-6">
    <div className="flex items-start gap-3"><div className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-rose-100 text-rose-700"><Icon size={22}/></div><div><p className="text-[11px] font-black tracking-wide text-rose-600">보이스피싱 피해 구제 · 단계별 안내</p><h2 className="mt-1 text-lg font-black text-slate-950">{step.title}</h2><p className="mt-1 text-sm leading-6 text-slate-600">{step.purpose}</p></div></div>
    <div className="mt-5 rounded-2xl bg-slate-50 p-4"><p className="text-xs font-black text-slate-800">지금 해야 할 순서</p><ol className="mt-3 space-y-2.5">{step.actions.map((action, index) => <li key={action} className="flex gap-3 text-sm leading-6 text-slate-700"><span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-rose-600 text-[11px] font-black text-white">{index + 1}</span><span>{action}</span></li>)}</ol></div>
    <div className="mt-4 grid gap-3 sm:grid-cols-2"><div className="rounded-2xl border border-amber-200 bg-amber-50 p-4"><div className="flex items-center gap-2 text-xs font-black text-amber-800"><ShieldAlert size={15}/>주의사항</div><p className="mt-2 text-xs leading-5 text-amber-900">{step.caution}</p></div><div className="rounded-2xl border border-blue-200 bg-blue-50 p-4"><p className="text-xs font-black text-blue-800">공식 확인·연락처</p><p className="mt-2 text-xs leading-5 text-blue-900">{step.contact}</p></div></div>
    <div className="mt-5 flex flex-wrap gap-2 border-t border-slate-100 pt-4"><button type="button" disabled={requesting} onClick={() => void request('AI_ADVICE')} className="inline-flex items-center gap-1.5 rounded-xl border border-blue-200 bg-blue-50 px-4 py-2.5 text-xs font-black text-blue-800 disabled:opacity-50"><Bot size={15}/>내 상황에 맞는 AI 조언</button><button type="button" disabled={requesting} onClick={() => void request('HUMAN_HANDOFF')} className="inline-flex items-center gap-1.5 rounded-xl bg-slate-900 px-4 py-2.5 text-xs font-black text-white disabled:opacity-50"><Headphones size={15}/>은행 담당자에게 지원 요청</button></div>
    {requested && <p className="mt-3 flex items-center gap-2 rounded-xl bg-emerald-50 px-3 py-2.5 text-xs font-bold text-emerald-700"><CheckCircle2 size={15}/>{requested === 'AI_ADVICE' ? 'AI 맞춤 조언 요청이 Case에 기록되었습니다.' : '은행 담당자 지원 요청이 Case에 기록되었습니다.'}</p>}
    <p className="mt-3 text-[10px] leading-5 text-slate-400">버튼은 Case에 지원 요청을 기록합니다. 외부 기관이나 은행 업무를 자동으로 실행하지 않습니다.</p>
  </section>;
};
