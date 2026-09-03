import React, { useEffect, useState } from 'react';
import { AlertCircle, Check, Loader2 } from 'lucide-react';
import { mvpChatApi, type CaseFact } from '../../../services/mvpChatApi';

export const CaseFactsPanel: React.FC<{ caseId: string; compact?: boolean }> = ({ caseId, compact = false }) => {
  const [facts, setFacts] = useState<CaseFact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const load = () => mvpChatApi.listCaseFacts(caseId).then(setFacts).catch((reason) => setError(reason instanceof Error ? reason.message : '확인 정보를 불러오지 못했습니다.')).finally(() => setLoading(false));
  useEffect(() => { void load(); }, [caseId]);
  const confirm = async (fact: CaseFact) => { try { await mvpChatApi.confirmCaseFact(caseId, fact.fact_id, '현재 사용자'); await load(); } catch (reason) { setError(reason instanceof Error ? reason.message : '확인 정보를 확정하지 못했습니다.'); } };
  return <section className={`rounded-2xl border border-slate-200 bg-white p-4 shadow-sm ${compact ? '' : 'mt-4'}`}><div className="flex items-center gap-2"><AlertCircle size={16} className="text-amber-500"/><h2 className="text-sm font-black">확인된 정보</h2><span className="ml-auto text-[11px] font-bold text-slate-400">AI 후보 · 담당자 확정</span></div>{loading ? <div className="mt-3 flex items-center gap-2 text-xs text-slate-500"><Loader2 size={14} className="animate-spin"/> 불러오는 중</div> : error ? <p className="mt-3 rounded-xl bg-rose-50 p-3 text-xs text-rose-700">{error}</p> : facts.length ? <div className="mt-3 space-y-2">{facts.map((fact) => <div key={fact.fact_id} className="flex items-center gap-3 rounded-xl border border-slate-100 p-3"><div className="min-w-0 flex-1"><p className="text-xs font-bold text-slate-500">{fact.field}</p><p className="mt-1 text-sm font-semibold">{fact.value}</p></div><span className={`rounded-full px-2 py-1 text-[10px] font-black ${fact.status === 'CONFIRMED' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>{fact.status === 'CONFIRMED' ? '확정' : '확인 필요'}</span>{fact.status !== 'CONFIRMED' && <button type="button" onClick={() => void confirm(fact)} className="inline-flex items-center gap-1 rounded-lg bg-slate-900 px-2.5 py-1.5 text-[11px] font-bold text-white"><Check size={13}/>확정</button>}</div>)}</div> : <p className="mt-3 rounded-xl bg-slate-50 p-3 text-xs text-slate-500">고객 답변에서 생성된 확인 정보가 없습니다.</p>}</section>;
};
