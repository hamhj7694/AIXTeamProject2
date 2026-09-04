import React, { useCallback, useMemo, useState } from 'react';
import { Building2, CheckCircle2, MessageCircleQuestion, ShieldCheck } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useCaseSyncRefresh } from '../../case-sync/useCaseSyncRefresh';
import { mvpChatApi, type CaseBundleV2, type CaseFact, type CustomerQuestion } from '../../../services/mvpChatApi';

export const CaseWorkflowSummaryPanel: React.FC<{ caseId: string }> = ({ caseId }) => {
  const [bundle, setBundle] = useState<CaseBundleV2 | null>(null);
  const [questions, setQuestions] = useState<CustomerQuestion[]>([]);
  const [facts, setFacts] = useState<CaseFact[]>([]);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const [nextBundle, nextQuestions, nextFacts] = await Promise.all([
        mvpChatApi.getBundle(caseId, 'bank'),
        mvpChatApi.listCustomerQuestions(caseId, 'bank'),
        mvpChatApi.listCaseFacts(caseId),
      ]);
      setBundle(nextBundle); setQuestions(nextQuestions); setFacts(nextFacts); setError('');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Case 연결 현황을 불러오지 못했습니다.');
    }
  }, [caseId]);
  useCaseSyncRefresh(caseId, load);
  React.useEffect(() => { void load(); }, [load]);

  const answered = useMemo(() => questions.filter((item) => item.status === 'ANSWERED').length, [questions]);
  const confirmedFacts = useMemo(() => facts.filter((item) => item.status === 'CONFIRMED').length, [facts]);
  const completedVerifications = useMemo(() => (bundle?.verification_tasks ?? []).filter((item) => item.status === 'COMPLETED' || item.status === 'FAILED').length, [bundle]);
  const mode = String(bundle?.case.mode ?? 'PREVENT');
  const status = String(bundle?.case.status ?? 'TRIAGE');

  const items = [
    { icon: MessageCircleQuestion, label: '고객 확인', value: `${answered}/${questions.length}건 답변`, detail: questions.length - answered > 0 ? `${questions.length - answered}건 응답 대기` : '대기 질문 없음', to: `/cases/${caseId}/customer`, color: 'text-blue-700 bg-blue-50' },
    { icon: CheckCircle2, label: '확정 정보', value: `${confirmedFacts}/${facts.length}건 확정`, detail: facts.length - confirmedFacts > 0 ? `${facts.length - confirmedFacts}건 담당자 확인 필요` : '확인 대기 없음', to: `/cases/${caseId}/bank`, color: 'text-emerald-700 bg-emerald-50' },
    { icon: ShieldCheck, label: '기관 검증', value: `${completedVerifications}/${bundle?.verification_tasks.length ?? 0}건 완료`, detail: (bundle?.verification_tasks.length ?? 0) - completedVerifications > 0 ? '공식 채널 확인 진행 중' : '대기 검증 없음', to: `/cases/${caseId}/verify`, color: 'text-violet-700 bg-violet-50' },
    { icon: Building2, label: '대응 모드', value: status === 'CLOSED' ? '처리 완료' : mode === 'RECOVERY' ? '피해구제 진행' : '피해 예방 진행', detail: status === 'CLOSED' ? '최종 보고서와 처리 결과 확인' : '은행 대응 화면에서 다음 업무 확인', to: `/cases/${caseId}/bank`, color: mode === 'RECOVERY' ? 'text-rose-700 bg-rose-50' : 'text-slate-700 bg-slate-100' },
  ];

  return <section className="mt-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
    <div className="flex items-center justify-between gap-3"><div><h2 className="text-sm font-black">Case 연결 현황</h2><p className="mt-1 text-xs text-slate-500">고객·은행·기관 검증 화면이 같은 Case 원본을 사용합니다.</p></div><span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-bold text-emerald-700">변경 즉시 동기화</span></div>
    {error ? <p className="mt-4 rounded-xl bg-rose-50 p-3 text-xs font-bold text-rose-700">{error}</p> : <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{items.map((item) => <Link key={item.label} to={item.to} className="rounded-xl border border-slate-100 p-3 transition hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-sm"><div className={`grid h-8 w-8 place-items-center rounded-lg ${item.color}`}><item.icon size={16}/></div><p className="mt-3 text-[11px] font-bold text-slate-400">{item.label}</p><p className="mt-1 text-sm font-black text-slate-900">{item.value}</p><p className="mt-1 text-[11px] leading-5 text-slate-500">{item.detail}</p></Link>)}</div>}
  </section>;
};
