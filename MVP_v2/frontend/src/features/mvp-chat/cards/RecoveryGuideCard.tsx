import React from 'react';
import { CheckCircle2, ShieldAlert } from 'lucide-react';
import { recoverySteps } from '../customer-cards/recoverySteps';

interface Props { selectedStepId?: string | null; onSelectStep: (stepId: string) => void; }

/** Persistent compact recovery menu. Detailed procedures render as a card in the customer chat. */
export const RecoveryGuideCard: React.FC<Props> = ({ selectedStepId, onSelectStep }) => (
  <section className="rounded-2xl border border-rose-200 bg-gradient-to-br from-rose-50 to-white p-4 shadow-sm">
    <div className="flex items-center gap-2 text-rose-700"><ShieldAlert size={19}/><h2 className="text-sm font-black">보이스피싱 피해 구제 안내</h2></div>
    <p className="mt-2 text-[11px] leading-5 text-slate-600">필요한 단계를 선택하면 채팅창에 상세 절차 카드가 열립니다.</p>
    <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
      {recoverySteps.map(({ id, icon: Icon, title, summary }) => <button type="button" key={id} onClick={() => onSelectStep(id)} className={`rounded-xl border p-3 text-left transition ${selectedStepId === id ? 'border-slate-900 bg-white ring-2 ring-slate-900' : 'border-rose-100 bg-white hover:border-rose-300'}`}>
        <div className="flex items-center gap-2 text-xs font-black text-slate-800"><Icon size={15} className="text-rose-600"/>{title}</div>
        <p className="mt-1.5 text-[11px] leading-5 text-slate-600">{summary}</p>
      </button>)}
    </div>
    <p className="mt-3 flex items-center gap-1 rounded-xl bg-rose-100/70 px-3 py-2.5 text-xs font-bold leading-5 text-rose-800"><CheckCircle2 size={14}/> 빠른 신고와 증빙 확보가 피해 구제에 중요합니다.</p>
  </section>
);
