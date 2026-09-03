import React from 'react';
import { CheckCircle2, ExternalLink, ShieldCheck } from 'lucide-react';
import type { VerificationTaskSummary } from '../../../services/mvpChatApi';

const safeEvidenceUrl = (value?: string | null) => {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === 'https:' || url.protocol === 'http:' ? url.toString() : null;
  } catch {
    return null;
  }
};

export const VerificationResultsCard: React.FC<{ tasks: VerificationTaskSummary[] }> = ({ tasks }) => {
  if (!tasks.length) return null;
  return <section className="rounded-2xl border border-emerald-500/40 bg-slate-950 p-4 text-slate-100 shadow-lg">
    <div className="flex items-center gap-2">
      <ShieldCheck size={17} className="text-emerald-300"/>
      <div>
        <p className="text-[11px] font-black tracking-wide text-emerald-300">CASE VERIFICATION</p>
        <h2 className="mt-0.5 text-sm font-black">완료된 기관 검증 결과</h2>
      </div>
      <span className="ml-auto rounded-full bg-emerald-400/15 px-2 py-1 text-[10px] font-black text-emerald-200">{tasks.length}건</span>
    </div>
    <div className="mt-3 space-y-2">
      {tasks.map((task) => {
        const evidenceUrl = safeEvidenceUrl(task.evidence_url);
        return <article key={task.verification_task_id} className="rounded-xl border border-slate-700 bg-slate-900 p-3">
          <div className="flex items-start gap-2">
            <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-emerald-400"/>
            <div className="min-w-0 flex-1">
              <p className="text-[11px] font-bold text-slate-400">{task.target}</p>
              <p className="mt-1 text-sm font-bold text-white">{task.result_summary || task.claim}</p>
              <div className="mt-2 flex flex-wrap gap-1.5 text-[10px] font-bold">
                <span className="rounded-full bg-slate-800 px-2 py-1 text-slate-300">확인자 {task.verified_by || '확인안됨'}</span>
                <span className="rounded-full bg-slate-800 px-2 py-1 text-slate-300">RAG {task.rag_source || '확인안됨'}</span>
                <span className={`rounded-full px-2 py-1 ${task.customer_visible ? 'bg-blue-500/20 text-blue-200' : 'bg-amber-500/15 text-amber-200'}`}>{task.customer_visible ? '고객 공개 가능' : '은행 내부 전용'}</span>
              </div>
              {evidenceUrl && <a href={evidenceUrl} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1 text-[11px] font-bold text-blue-300 hover:text-blue-200"><ExternalLink size={12}/>근거 열기</a>}
            </div>
          </div>
        </article>;
      })}
    </div>
  </section>;
};
