import React, { useEffect, useState } from 'react';
import { ArrowLeft, ChevronRight, ShieldCheck, UserRound, WalletCards } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import { CaseDetail } from '../data/mock/caseData';
import { caseApi } from '../services/caseApi';

const badgeClass = (risk: string) => risk === 'HIGH' ? 'bg-rose-50 text-rose-700' : risk === 'LOW' ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700';
const statusClass = (status: string) => status === '확인중' ? 'bg-blue-50 text-blue-700' : status === '후속조치' ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700';

export const CaseEntryPageV2: React.FC = () => {
  const { caseId = 'VP-014' } = useParams();
  const [item, setItem] = useState<CaseDetail | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    setItem(null); setError('');
    caseApi.get(caseId)
      .then((result) => { if (active) setItem(result); })
      .catch((reason) => { if (active) setError(reason instanceof Error ? reason.message : 'Case를 불러오지 못했습니다.'); });
    return () => { active = false; };
  }, [caseId]);

  if (error) return <AppLayout><div className="mx-auto max-w-6xl py-8 lg:ml-64"><Link to="/" className="mb-6 inline-flex items-center gap-1 text-sm font-bold text-slate-500"><ArrowLeft size={16}/> 진단 화면으로 돌아가기</Link><div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm font-bold text-rose-700">{error}</div></div></AppLayout>;
  if (!item) return <AppLayout><div className="mx-auto max-w-6xl py-8 lg:ml-64"><div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm font-bold text-slate-500">분석된 Case를 불러오는 중...</div></div></AppLayout>;
  const cards = [
    ['은행 화면', '담당자용 AI Workspace, 진행 흐름, 원본 Evidence를 확인합니다.', `/cases/${item.id}/bank`, WalletCards],
    ['소비자 화면', '현재 행동과 Customer Agent를 확인합니다.', `/cases/${item.id}/customer`, UserRound],
    ['기타 / 검증', '이 Case의 사실 확인 질문을 진행합니다.', `/cases/${item.id}/verify`, ShieldCheck],
  ] as const;

  return <AppLayout><div className="mx-auto max-w-6xl py-8 lg:ml-64"><Link to="/cases" className="mb-6 inline-flex items-center gap-1 text-sm font-bold text-slate-500"><ArrowLeft size={16}/> Case 목록</Link><div className="mb-6"><div className="mb-2 flex flex-wrap items-center gap-2"><span className="text-xs font-bold text-slate-400">CASE #{item.id}</span><span className={`rounded-full px-2.5 py-1 text-[11px] font-extrabold ${badgeClass(item.risk)}`}>{item.risk}</span><span className={`rounded-full px-2.5 py-1 text-[11px] font-extrabold ${statusClass(item.status)}`}>{item.status}</span></div><h1 className="text-2xl font-black">{item.type} 의심 Case</h1><p className="mt-2 text-sm text-slate-500">생성 {item.createdAt} · 최근 업데이트 {item.updatedAt}</p></div><section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-sm font-extrabold">AI Initial Brief</h2><p className="mt-4 text-sm leading-7 text-slate-600">{item.aiInitialBrief}</p></section><div className="mt-5 grid gap-4 md:grid-cols-3">{cards.map(([title, description, path, Icon]) => <Link key={title} to={path} className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-blue-300"><Icon size={22} className="text-blue-600"/><h2 className="mt-5 font-extrabold">{title}</h2><p className="mt-2 min-h-10 text-sm text-slate-500">{description}</p><span className="mt-5 inline-flex items-center gap-1 text-xs font-bold text-blue-600">들어가기 <ChevronRight size={14}/></span></Link>)}</div><section className="mt-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex flex-wrap items-center justify-between gap-3"><div className="flex items-center gap-2"><span className="text-sm font-black">#{item.id.replace(/^VP-/, '')}</span><span className={`rounded-md px-2 py-1 text-[11px] font-bold ${statusClass(item.status)}`}>{item.status === '확인중' ? 'PREVENT' : item.status === '해결 완료' ? 'CLOSED' : 'FOLLOW-UP'}</span></div><span className="text-xs text-slate-400">{item.createdAt}</span></div><p className="mt-4 text-sm font-bold">{item.type} · {item.transferred ? '송금 Y' : '송금 N'} · {item.amount || '-'}</p><p className="mt-2 text-sm leading-6 text-slate-600">{item.summary}</p><p className="mt-4 text-right text-xs text-slate-400">최근 업데이트 {item.updatedAt}</p></section></div></AppLayout>;
};
