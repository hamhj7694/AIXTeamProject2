import React, { useState } from 'react';
import { ArrowLeft, Check, ShieldAlert } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import { getCase } from '../data/mock/caseData';

export const BankPage: React.FC = () => {
  const { caseId = 'VP-014' } = useParams();
  const item = getCase(caseId);
  const [takeover, setTakeover] = useState(() => window.localStorage.getItem('human-takeover') === 'true');
  const toggleTakeover = () => {
    const next = !takeover;
    setTakeover(next);
    window.localStorage.setItem('human-takeover', String(next));
    window.dispatchEvent(new Event('human-takeover-change'));
  };
  return <AppLayout><div className="mx-auto max-w-6xl py-8 lg:ml-64">
    <div className="mb-5 flex flex-wrap items-center justify-between gap-3"><Link to={`/cases/${caseId}`} className="inline-flex items-center gap-1 text-sm font-bold text-slate-500"><ArrowLeft size={16}/> Case로 돌아가기</Link><button onClick={toggleTakeover} className={`rounded-xl px-3 py-2 text-xs font-bold ${takeover ? 'bg-amber-100 text-amber-700' : 'bg-slate-900 text-white'}`}>{takeover ? '담당자 참여 중' : 'Human Takeover'}</button></div>
    <div className="mb-6"><p className="mb-2 text-xs font-bold text-blue-600">BANK FRAUD CASE WORKSPACE</p><div className="flex flex-wrap items-center gap-2"><h1 className="text-2xl font-black">#{item.id} · {item.risk}</h1><span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-bold text-blue-700">{item.status}</span></div><p className="mt-2 text-sm text-slate-500">{item.type} · 마지막 이벤트 {item.updatedAt}</p></div>
    <div className="grid gap-4 lg:grid-cols-2"><section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-sm font-extrabold">LIVE CASE BRIEF</h2><p className="mt-4 text-sm leading-7 text-slate-600">{item.summary}</p><div className="mt-4 rounded-xl bg-rose-50 p-4"><p className="text-xs font-bold text-rose-600">FDS 위험 신호</p><p className="mt-1 text-sm font-bold text-rose-800">추가 검증과 담당자 확인이 필요합니다.</p></div></section><section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-sm font-extrabold">담당자 참여 상태</h2><div className={`mt-4 flex items-center gap-3 rounded-xl p-4 ${takeover ? 'bg-amber-50 text-amber-800' : 'bg-slate-50 text-slate-600'}`}><ShieldAlert size={20}/><div><p className="text-sm font-bold">{takeover ? '담당자가 Case에 참여했습니다.' : 'AI가 Case를 확인하고 있습니다.'}</p><p className="mt-1 text-xs">소비자 화면에도 참여 상태가 반영됩니다.</p></div></div><p className="mt-4 inline-flex items-center gap-1 text-xs text-slate-500"><Check size={14}/> 최종 금융조치는 금융기관 담당자가 판단합니다.</p></section></div>
  </div></AppLayout>;
};
