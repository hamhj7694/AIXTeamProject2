import React from 'react';
import { CheckCircle2, Loader2, X } from 'lucide-react';
import type { WorkCardStage } from './types';

const stageLabel: Record<WorkCardStage, string> = {
  DRAFT: '초안', READY: '검토 대기', SUBMITTING: '처리 중', REGISTERED: '업무 등록', DELIVERED: '전달 완료', FAILED: '처리 실패',
};

interface Props {
  eyebrow: string;
  title: string;
  description: string;
  stage: WorkCardStage;
  onClose: () => void;
  children: React.ReactNode;
}

export const WorkCardFrame: React.FC<Props> = ({ eyebrow, title, description, stage, onClose, children }) => (
  <section className="rounded-2xl border border-violet-400/50 bg-slate-950 p-4 text-slate-100 shadow-lg">
    <div className="flex items-start justify-between gap-3">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-[11px] font-black tracking-wide text-violet-300">{eyebrow}</p>
          <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-black ${stage === 'FAILED' ? 'bg-rose-500/20 text-rose-200' : stage === 'SUBMITTING' ? 'bg-blue-500/20 text-blue-200' : stage === 'REGISTERED' || stage === 'DELIVERED' ? 'bg-emerald-500/20 text-emerald-200' : 'bg-slate-800 text-slate-300'}`}>
            {stage === 'SUBMITTING' ? <Loader2 size={11} className="animate-spin"/> : stage === 'REGISTERED' || stage === 'DELIVERED' ? <CheckCircle2 size={11}/> : null}
            {stageLabel[stage]}
          </span>
        </div>
        <h2 className="mt-1 font-black">{title}</h2>
        <p className="mt-1 text-xs leading-5 text-slate-400">{description}</p>
      </div>
      <button type="button" onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-800" aria-label={`${title} 카드 닫기`}><X size={17}/></button>
    </div>
    {children}
  </section>
);
