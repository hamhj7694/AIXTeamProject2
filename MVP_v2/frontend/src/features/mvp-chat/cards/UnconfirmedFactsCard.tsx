import React, { useEffect, useMemo, useState } from 'react';
import { AlertCircle, Check, Loader2, X } from 'lucide-react';
import { mvpChatApi, type CaseFact, type VerificationTaskSummary } from '../../../services/mvpChatApi';
import { VerificationResultsCard } from './VerificationResultsCard';

interface Props {
  caseId: string;
  facts: CaseFact[];
  confirmedBy: string;
  onChanged: () => Promise<void> | void;
  onOpenQuestions: () => void;
  onClose: () => void;
}

const sourceLabel: Record<CaseFact['source'], string> = {
  AI_EXTRACTED: 'AI 추출 후보',
  HUMAN_CONFIRMED: '담당자 입력',
  VERIFIED: '기관 검증',
  UNRESOLVED: '출처 확인 필요',
};

export const UnconfirmedFactsCard: React.FC<Props> = ({ caseId, facts, confirmedBy, onChanged, onOpenQuestions, onClose }) => {
  const [savingId, setSavingId] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [verificationResults, setVerificationResults] = useState<VerificationTaskSummary[]>([]);
  const ordered = useMemo(() => [...facts].sort((a, b) => Number(a.status === 'CONFIRMED') - Number(b.status === 'CONFIRMED')), [facts]);
  useEffect(() => {
    mvpChatApi.getBundle(caseId, 'bank')
      .then((bundle) => setVerificationResults(bundle.verification_tasks.filter((task) => task.status === 'COMPLETED' || task.status === 'FAILED')))
      .catch(() => setVerificationResults([]));
  }, [caseId]);

  const confirm = async (fact: CaseFact) => {
    setSavingId(fact.fact_id);
    setError('');
    try {
      await mvpChatApi.confirmCaseFact(caseId, fact.fact_id, confirmedBy);
      await onChanged();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '확인 정보를 확정하지 못했습니다.');
    } finally {
      setSavingId(null);
    }
  };

  return <section className="rounded-2xl border border-amber-400/50 bg-slate-950 p-4 text-slate-100 shadow-lg">
    <div className="flex items-start justify-between gap-3">
      <div>
        <p className="text-[11px] font-black tracking-wide text-amber-300">AI 개인 작업 · 미확인 정보</p>
        <h2 className="mt-1 font-black">CaseFact 후보 검토</h2>
        <p className="mt-1 text-xs leading-5 text-slate-400">고객 답변·AI 추출 결과는 담당자가 확정하기 전까지 공식 사실이 아닙니다.</p>
      </div>
      <button type="button" onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-800" aria-label="미확인 정보 카드 닫기"><X size={17}/></button>
    </div>

    {error && <p className="mt-3 rounded-xl bg-rose-950/60 p-3 text-xs text-rose-200">{error}</p>}
    {verificationResults.length > 0 && <div className="mt-4"><VerificationResultsCard tasks={verificationResults}/></div>}
    <div className="mt-4 space-y-2">
      {ordered.length ? ordered.map((fact) => {
        const confirmed = fact.status === 'CONFIRMED';
        return <article key={fact.fact_id} className={`rounded-xl border p-3 ${confirmed ? 'border-emerald-700/50 bg-emerald-950/30' : 'border-amber-500/40 bg-slate-900'}`}>
          <div className="flex items-start gap-3">
            <AlertCircle size={16} className={confirmed ? 'mt-0.5 text-emerald-400' : 'mt-0.5 text-amber-300'}/>
            <div className="min-w-0 flex-1">
              <p className="text-[11px] font-bold text-slate-400">{fact.field} · {sourceLabel[fact.source]}</p>
              <p className="mt-1 break-words text-sm font-bold text-white">{fact.value}</p>
              <p className="mt-1 text-[10px] text-slate-500">신뢰도 {Math.round(fact.confidence * 100)}% · {confirmed ? `확정자 ${fact.confirmed_by ?? '담당자'}` : '확인 필요'}</p>
            </div>
            {confirmed ? <span className="rounded-full bg-emerald-400/15 px-2 py-1 text-[10px] font-black text-emerald-300">확정</span> : <button type="button" disabled={savingId === fact.fact_id} onClick={() => void confirm(fact)} className="inline-flex items-center gap-1 rounded-lg bg-amber-300 px-2.5 py-1.5 text-[11px] font-black text-slate-950 disabled:opacity-50">{savingId === fact.fact_id ? <Loader2 size={13} className="animate-spin"/> : <Check size={13}/>}확정</button>}
          </div>
        </article>;
      }) : <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900 p-4 text-center">
        <p className="text-xs font-bold text-slate-300">아직 검토할 CaseFact 후보가 없습니다.</p>
        <p className="mt-1 text-[11px] leading-5 text-slate-500">고객 확인 질문과 답변이 누적되면 이곳에서 후보를 검토할 수 있습니다.</p>
        <button type="button" onClick={onOpenQuestions} className="mt-3 rounded-lg border border-violet-400/50 px-3 py-2 text-xs font-bold text-violet-200">질문 추천 카드 열기</button>
      </div>}
    </div>
    <p className="mt-3 text-[10px] leading-4 text-slate-500">확정 액션만 Case의 공식 정보에 반영됩니다. AI가 제안한 내용은 자동 확정되지 않습니다.</p>
  </section>;
};
