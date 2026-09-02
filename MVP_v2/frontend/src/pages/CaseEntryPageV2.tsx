import React, { useEffect, useState } from 'react';
import { ArrowLeft, Building2, ChevronRight, ShieldCheck, UserRound } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import { caseApi, type CaseDetail } from '../services/caseApi';

export const CaseEntryPageV2: React.FC = () => {
  const { caseId = '' } = useParams();
  const [item, setItem] = useState<CaseDetail | null>(null);
  const [error, setError] = useState('');
  useEffect(() => { caseApi.get(caseId).then(setItem).catch((reason) => setError(reason instanceof Error ? reason.message : 'Case를 불러오지 못했습니다.')); }, [caseId]);
  if (error) return <AppLayout><div className="mx-auto max-w-5xl py-8 lg:ml-64"><p className="rounded-xl bg-rose-50 p-4 text-rose-700">{error}</p></div></AppLayout>;
  if (!item) return <AppLayout><div className="mx-auto max-w-5xl py-8 lg:ml-64"><p className="rounded-xl bg-white p-8 text-center text-slate-500">Case를 불러오는 중입니다.</p></div></AppLayout>;
  const links = [
    ['은행 협업 화면', '담당자·채널·Case Live Log를 확인합니다.', `/cases/${item.id}/bank`, Building2],
    ['고객 상담 화면', '고객 안전 안내 및 상담 메시지를 확인합니다.', `/cases/${item.id}/customer`, UserRound],
    ['기관 검증', '사칭 기관에 대한 사실 확인 요청을 기록합니다.', `/cases/${item.id}/verify`, ShieldCheck],
  ] as const;
  return <AppLayout><div className="mx-auto max-w-5xl py-8 lg:ml-64"><Link to="/cases" className="mb-5 inline-flex items-center gap-1 text-sm font-bold text-slate-500"><ArrowLeft size={16}/> 보이스피싱 Case 목록</Link>
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-xs font-bold text-blue-600">CASE {item.id.replace(/^VP-/, '#')}</p><h1 className="mt-2 text-2xl font-black">{item.type}</h1></div><div className="flex gap-2"><span className={`rounded-full px-3 py-1.5 text-xs font-bold ${item.risk === 'HIGH' ? 'bg-rose-50 text-rose-700' : 'bg-slate-100 text-slate-700'}`}>{item.risk}</span><span className="rounded-full bg-blue-50 px-3 py-1.5 text-xs font-bold text-blue-700">{item.status}</span></div></div><p className="mt-5 text-sm leading-7 text-slate-700">{item.aiInitialBrief}</p><div className="mt-5 border-t border-slate-100 pt-4 text-xs text-slate-500">생성 {item.createdAt} · 최근 업데이트 {item.updatedAt} · 담당자 {item.assignee || '미배정'}</div></section>
    <div className="mt-5 grid gap-4 md:grid-cols-3">{links.map(([title, description, path, Icon]) => <Link key={title} to={path} className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-blue-300"><Icon size={21} className="text-blue-600"/><h2 className="mt-4 font-extrabold">{title}</h2><p className="mt-2 min-h-10 text-sm text-slate-500">{description}</p><span className="mt-4 inline-flex items-center gap-1 text-xs font-bold text-blue-600">열기 <ChevronRight size={14}/></span></Link>)}</div>
  </div></AppLayout>;
};
