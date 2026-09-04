import React, { useCallback, useEffect, useState } from 'react';
import { ArrowLeft, Building2, ChevronRight, ShieldCheck, UserRound } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import { CaseContextBar } from '../components/case/CaseContextBar';
import { caseApi, type CaseDetail } from '../services/caseApi';
import { mvpChatApi } from '../services/mvpChatApi';
import { workflowStatusLabel } from '../utils/casePresentation';
import { CaseFactsPanel } from '../features/mvp-chat/cards/CaseFactsPanel';
import { useCaseSyncRefresh } from '../features/case-sync/useCaseSyncRefresh';
import { CaseWorkflowSummaryPanel } from '../features/mvp-chat/cards/CaseWorkflowSummaryPanel';

export const CaseEntryPageV2: React.FC = () => {
  const { caseId = '' } = useParams();
  const [item, setItem] = useState<CaseDetail | null>(null);
  const [customerStatus, setCustomerStatus] = useState('대기중');
  const [error, setError] = useState('');
  const load = useCallback(async () => {
    const [caseDetail, presence] = await Promise.all([caseApi.get(caseId), mvpChatApi.listPresence(caseId)]);
    setItem(caseDetail);
    const connectedCustomer = presence.find((entry) => entry.channel === 'CUSTOMER' && (entry.presence === 'VIEWING' || entry.presence === 'TYPING'));
    setCustomerStatus(connectedCustomer ? '상담 중' : caseDetail.transferred === null ? '대기중' : '부재중');
  }, [caseId]);
  useCaseSyncRefresh(caseId, load);
  useEffect(() => { void load().catch((reason) => setError(reason instanceof Error ? reason.message : 'Case를 불러오지 못했습니다.')); }, [load]);
  useEffect(() => {
    const refreshCustomerStatus = () => mvpChatApi.listPresence(caseId).then((presence) => {
      const customer = presence.find((entry) => entry.channel === 'CUSTOMER' && (entry.presence === 'VIEWING' || entry.presence === 'TYPING'));
      setCustomerStatus(customer ? '상담 중' : item?.transferred === null ? '대기중' : '부재중');
    }).catch(() => undefined);
    void refreshCustomerStatus();
    const timer = window.setInterval(refreshCustomerStatus, 10_000);
    return () => window.clearInterval(timer);
  }, [caseId, item?.transferred]);
  if (error) return <AppLayout><div className="mx-auto max-w-6xl py-8 lg:ml-64"><p className="rounded-xl bg-rose-50 p-4 text-rose-700">{error}</p><Link to="/cases" className="mt-4 inline-block text-sm font-bold text-blue-700">목록으로 돌아가기</Link></div></AppLayout>;
  if (!item) return <AppLayout><div className="mx-auto max-w-6xl py-8 lg:ml-64"><p className="rounded-xl bg-white p-8 text-center text-slate-500">Case를 불러오는 중입니다.</p></div></AppLayout>;
  const bankPath = '/cases/' + item.id + '/bank';
  const customerPath = '/cases/' + item.id + '/customer';
  const verifyPath = '/cases/' + item.id + '/verify';

  return <AppLayout><main className="mx-auto max-w-6xl py-8 lg:ml-64"><Link to="/cases" className="mb-5 inline-flex items-center gap-1 text-sm font-bold text-slate-500"><ArrowLeft size={16}/> 보이스피싱 Case 목록</Link>
    <header className="mb-4 rounded-2xl bg-slate-900 p-6 text-white"><p className="text-xs font-bold text-blue-200">CASE OVERVIEW</p><div className="mt-2 flex flex-wrap items-center gap-3"><h1 className="text-2xl font-black">{item.type || '사기 유형 확인안됨'}</h1><span className="rounded-full bg-white/15 px-3 py-1 text-xs font-bold">{workflowStatusLabel(item.status)}</span><span className="rounded-full bg-white/15 px-3 py-1 text-xs font-bold">고객 상태 · {customerStatus}</span></div><p className="mt-3 max-w-3xl text-sm leading-6 text-slate-200">사건 요약 · {item.summary}</p></header>
    <CaseContextBar item={item} />
    <CaseWorkflowSummaryPanel caseId={item.id} />
    <CaseFactsPanel caseId={item.id} />
    <section className="mt-4 grid gap-4 md:grid-cols-3"><Link to={bankPath} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-blue-300"><Building2 size={21} className="text-blue-600"/><h2 className="mt-4 font-extrabold">은행 대응 화면 체험하기</h2><p className="mt-2 min-h-10 text-sm text-slate-500">은행 담당자가 Case를 함께 확인하고 대응하는 화면입니다.</p><span className="mt-4 inline-flex items-center gap-1 text-xs font-bold text-blue-600">체험하기 <ChevronRight size={14}/></span></Link><Link to={customerPath} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-blue-300"><UserRound size={21} className="text-blue-600"/><h2 className="mt-4 font-extrabold">고객 상담 화면 체험하기</h2><p className="mt-2 min-h-10 text-sm text-slate-500">고객이 안전 안내를 받고 현재 상황을 입력하는 화면입니다.</p><span className="mt-4 inline-flex items-center gap-1 text-xs font-bold text-blue-600">체험하기 <ChevronRight size={14}/></span></Link><Link to={verifyPath} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-blue-300"><ShieldCheck size={21} className="text-blue-600"/><h2 className="mt-4 font-extrabold">기관 검증 화면 체험하기</h2><p className="mt-2 min-h-10 text-sm text-slate-500">사칭된 기관의 주장과 확인 결과를 기록하는 화면입니다.</p><span className="mt-4 inline-flex items-center gap-1 text-xs font-bold text-blue-600">체험하기 <ChevronRight size={14}/></span></Link></section>
  </main></AppLayout>;
};
