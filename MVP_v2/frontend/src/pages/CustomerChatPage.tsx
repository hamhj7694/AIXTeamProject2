import React, { useCallback, useEffect, useState } from 'react';

import { AlertTriangle, ArrowLeft, ShieldCheck } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import { CaseContextBar } from '../components/case/CaseContextBar';
import { ChatWorkspace } from '../features/mvp-chat/ChatWorkspace';

import { useParams } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import { CustomerSafetyRoom } from '../features/mvp-chat/CustomerSafetyRoom';

import { mvpChatApi, type CaseBundleV2, type MvpMessage } from '../services/mvpChatApi';
import { caseApi, type CaseDetail } from '../services/caseApi';

export const CustomerChatPage: React.FC = () => {
  const { caseId = '' } = useParams();
  const [bundle, setBundle] = useState<CaseBundleV2 | null>(null);
  const [messages, setMessages] = useState<MvpMessage[]>([]);
  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);

  const load = useCallback(async () => {
    const [nextBundle, nextMessages, nextCaseData] = await Promise.all([mvpChatApi.getBundle(caseId, 'customer'), mvpChatApi.listMessages(caseId, 'CUSTOMER', 'customer'), caseApi.get(caseId)]);
    setBundle(nextBundle); setMessages(nextMessages); setCaseData(nextCaseData);
  }, [caseId]);
  useEffect(() => { load().catch((reason) => setError(reason instanceof Error ? reason.message : 'Case를 불러오지 못했습니다.')); }, [load]);
  useEffect(() => { const timer = window.setInterval(() => { load().catch(() => undefined); }, 3000); return () => window.clearInterval(timer); }, [load]);

  useEffect(() => {
    const beat = () => mvpChatApi.heartbeat(caseId, { user_id: 'mvp-v2-customer', display_name: '고객', presence: 'VIEWING', channel: 'CUSTOMER' }).catch(() => undefined);
    void beat();
    const timer = window.setInterval(beat, 10_000);
    return () => window.clearInterval(timer);
  }, [caseId]);
  const send = async (content: string) => { setSending(true); try { const message = await mvpChatApi.createMessage(caseId, { actor_type: 'CUSTOMER', actor_user_id: 'mvp-v2-customer', actor_display_name: '고객', actor_role: 'CUSTOMER', content, channel: 'CUSTOMER', audience: 'CUSTOMER', visibility: 'CUSTOMER', message_kind: 'CHAT' }); setMessages((items) => [...items, message]); } finally { setSending(false); } };
  const currentCase = bundle?.case ?? {};
  const status = String(currentCase.status ?? '확인 중');
  const brief = String(currentCase.initial_brief ?? '현재 상황을 확인하고 있습니다.');

  return <AppLayout><main className="mx-auto max-w-6xl py-6 lg:ml-64"><div className="mb-4 flex items-center justify-between"><Link to={`/cases/${caseId}`} className="inline-flex items-center gap-1 text-sm font-bold text-slate-500"><ArrowLeft size={16}/> Case로 돌아가기</Link><span className="text-[11px] font-bold text-slate-400">CUSTOMER SAFETY CHAT</span></div>
    <section className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3"><div className="flex items-center gap-3"><AlertTriangle className="text-rose-600" size={20}/><div><p className="text-sm font-black text-rose-800">지금은 송금·인증정보 제공을 멈춰주세요.</p><p className="mt-0.5 text-xs text-rose-700">은행과 함께 사실관계를 확인하고 있습니다.</p></div></div><span className="rounded-full bg-white px-3 py-1 text-xs font-bold text-rose-700">{status}</span></section>
    {caseData && <div className="mb-4"><CaseContextBar item={caseData} compact/></div>}
    {error && <p className="mb-4 rounded-xl bg-rose-50 p-3 text-sm font-semibold text-rose-700">{error}</p>}
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px]"><ChatWorkspace title="안전 상담" description="현재 상황을 알려주시면 필요한 내용을 차례로 확인합니다." channelLabel="Customer Agent" messages={messages} placeholder="상대방이 요구한 내용이나 현재 상황을 입력하세요." currentUserId="mvp-v2-customer" sending={sending} onSend={send}/>
      <aside className="space-y-4"><section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><p className="text-xs font-extrabold text-slate-500">현재 진행</p><p className="mt-2 text-sm font-black text-slate-900">{status}</p><p className="mt-3 text-xs leading-5 text-slate-600">{brief}</p></section><section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><div className="flex items-center gap-2"><ShieldCheck size={16} className="text-blue-600"/><p className="text-sm font-black">다음 행동</p></div><p className="mt-2 text-xs leading-5 text-slate-600">상대방이 알려준 번호가 아닌 공식 채널을 통해 확인해 주세요.</p></section></aside>
    </div></main></AppLayout>;

  const send = async (content: string) => { setSending(true); try { const message = await mvpChatApi.createMessage(caseId, { actor_type: 'CUSTOMER', content, channel: 'CUSTOMER', audience: 'CUSTOMER' }); setMessages((items) => [...items, message]); } finally { setSending(false); } };
  return <AppLayout>
    {error && <p className="mx-auto mt-6 max-w-[1640px] rounded-xl bg-rose-50 p-3 text-sm font-semibold text-rose-700 lg:ml-[calc(16rem+1.5rem)]">{error}</p>}
    <CustomerSafetyRoom caseId={caseId} bundle={bundle} messages={messages} sending={sending} onSend={send} />
  </AppLayout>;
};
