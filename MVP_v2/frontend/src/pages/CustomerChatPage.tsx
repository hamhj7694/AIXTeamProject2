import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, ArrowLeft, HelpCircle, ShieldCheck } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import { CaseContextBar } from '../components/case/CaseContextBar';
import { ChatWorkspace } from '../features/mvp-chat/ChatWorkspace';
import { CustomerQuestionCard } from '../features/mvp-chat/cards/CustomerQuestionCard';
import { RecoveryGuideCard } from '../features/mvp-chat/cards/RecoveryGuideCard';
import { mvpChatApi, type CaseBundleV2, type CustomerQuestion, type MvpMessage } from '../services/mvpChatApi';
import { caseApi, type CaseDetail } from '../services/caseApi';

const customer = { user_id: 'mvp-v2-customer', display_name: '고객', role: 'CUSTOMER' };

export const CustomerChatPage: React.FC = () => {
  const { caseId = '' } = useParams();
  const [bundle, setBundle] = useState<CaseBundleV2 | null>(null);
  const [messages, setMessages] = useState<MvpMessage[]>([]);
  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [customerQuestions, setCustomerQuestions] = useState<CustomerQuestion[]>([]);
  const [recoveryActive, setRecoveryActive] = useState(false);
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);
  const load = useCallback(async () => {
    const [nextBundle, nextMessages, nextCase, nextQuestions] = await Promise.all([mvpChatApi.getBundle(caseId, 'customer'), mvpChatApi.listMessages(caseId, 'CUSTOMER', 'customer'), caseApi.get(caseId), mvpChatApi.listCustomerQuestions(caseId, 'customer')]);
    setBundle(nextBundle); setMessages(nextMessages); setCaseData(nextCase); setCustomerQuestions(nextQuestions);
  }, [caseId]);
  useEffect(() => { load().catch((reason) => setError(reason instanceof Error ? reason.message : 'Case를 불러오지 못했습니다.')); }, [load]);
  useEffect(() => { const timer = window.setInterval(() => { load().catch(() => undefined); }, 3000); return () => window.clearInterval(timer); }, [load]);
  useEffect(() => { const beat = () => mvpChatApi.heartbeat(caseId, { ...customer, presence: 'VIEWING', channel: 'CUSTOMER' }).catch(() => undefined); void beat(); const timer = window.setInterval(beat, 10_000); return () => window.clearInterval(timer); }, [caseId]);
  const send = async (content: string) => { setSending(true); try { const message = await mvpChatApi.createMessage(caseId, { actor_type: 'CUSTOMER', actor_user_id: customer.user_id, actor_display_name: customer.display_name, actor_role: customer.role, content, channel: 'CUSTOMER', audience: 'CUSTOMER', visibility: 'CUSTOMER', message_kind: 'CHAT' }); setMessages((items) => [...items, message]); } finally { setSending(false); } };
  const currentCase = bundle?.case ?? {};
  const status = String(currentCase.status ?? '확인 중');
  const brief = String(currentCase.initial_brief ?? '현재 상황을 확인하고 있습니다.');
  const visibleMessages = useMemo(() => messages.filter((message) => message.visibility === 'CUSTOMER'), [messages]);
  const activeQuestion = customerQuestions.find((question) => question.status === 'ASKED') ?? null;
  const hasLoss = caseData?.transferred === true;
  const answerQuestion = async (answer: string) => {
    if (!activeQuestion) return;
    setSending(true);
    try {
      await mvpChatApi.answerCustomerQuestion(caseId, activeQuestion.question_id, answer, customer);
      await mvpChatApi.createMessage(caseId, {
        actor_type: 'CUSTOMER_AGENT', actor_user_id: 'customer-agent', actor_display_name: 'Customer Agent', actor_role: null,
        content: `고객이 확인 질문에 답변했습니다.\n질문: ${activeQuestion.question_text}\n답변: ${answer}`,
        channel: 'TEAM', audience: 'BANK_INTERNAL', visibility: 'BANK_INTERNAL', message_kind: 'SYSTEM_EVENT',
      });
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '답변을 저장하지 못했습니다.');
    } finally { setSending(false); }
  };
  const startRecovery = async () => {
    if (recoveryActive || sending) return;
    setRecoveryActive(true); setSending(true);
    try {
      await mvpChatApi.createMessage(caseId, { actor_type: 'CUSTOMER', actor_user_id: customer.user_id, actor_display_name: customer.display_name, actor_role: customer.role, content: '긴급 대응을 시작합니다. 피해구제 안내를 확인하고 싶습니다.', channel: 'CUSTOMER', audience: 'CUSTOMER', visibility: 'CUSTOMER', message_kind: 'CHAT' });
      await mvpChatApi.createMessage(caseId, {
        actor_type: 'CUSTOMER_AGENT', actor_user_id: 'customer-agent', actor_display_name: 'Customer Agent', actor_role: null,
        content: '고객이 긴급 대응을 요청했습니다. 피해 발생 여부와 즉시 보호 조치를 확인해 주세요.',
        channel: 'TEAM', audience: 'BANK_INTERNAL', visibility: 'BANK_INTERNAL', message_kind: 'SYSTEM_EVENT',
      });
      await load();
    } catch (reason) {
      setRecoveryActive(false);
      setError(reason instanceof Error ? reason.message : '긴급 대응을 시작하지 못했습니다.');
    } finally { setSending(false); }
  };
  return <AppLayout><main className="mx-auto max-w-6xl py-6 lg:ml-64"><div className="mb-4 flex items-center justify-between"><Link to={`/cases/${caseId}`} className="inline-flex items-center gap-1 text-sm font-bold text-slate-500"><ArrowLeft size={16}/> Case로 돌아가기</Link><span className="text-[11px] font-bold text-slate-400">CUSTOMER SAFETY CHAT</span></div><section className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3"><div className="flex items-center gap-3"><AlertTriangle className="text-rose-600" size={20}/><div><p className="text-sm font-black text-rose-800">지금은 송금·인증정보 제공을 멈춰주세요.</p><p className="mt-0.5 text-xs text-rose-700">상대방이 알려준 연락처가 아닌 공식 채널로만 확인해 주세요.</p></div></div><span className="rounded-full bg-white px-3 py-1 text-xs font-bold text-rose-700">{status}</span></section><section className="mb-4 flex items-center justify-between gap-3 rounded-2xl border border-rose-200 bg-white px-4 py-3 shadow-sm"><div><p className="text-sm font-black text-rose-800">이미 피해를 받았어요?</p><p className="mt-1 text-xs text-slate-500">송금·정보 노출 피해가 있다면 즉시 대응 절차를 확인하세요.</p></div><button type="button" onClick={() => void startRecovery()} disabled={recoveryActive || sending} className="rounded-xl bg-rose-600 px-4 py-2.5 text-xs font-black text-white disabled:opacity-50">{recoveryActive ? '긴급 대응 진행 중' : '긴급 대응 시작'}</button></section>{caseData && <div className="mb-4"><CaseContextBar item={caseData} compact/></div>}{error && <p className="mb-4 rounded-xl bg-rose-50 p-3 text-sm font-semibold text-rose-700">{error}</p>}<div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px]"><ChatWorkspace title="안전 상담" description="현재 상황을 알려주시면 필요한 내용을 차례로 확인합니다." channelLabel="고객 공개 채널" messages={visibleMessages} placeholder="상대방이 요구한 내용이나 현재 상황을 입력하세요." currentUserId={customer.user_id} sending={sending} onSend={send} toolCards={<>{recoveryActive && <RecoveryGuideCard onClose={() => setRecoveryActive(false)}/>} {activeQuestion && <CustomerQuestionCard question={activeQuestion} submitting={sending} onSubmit={answerQuestion}/>}</>}/><aside className="space-y-4"><section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><p className="text-xs font-extrabold text-slate-500">현재 확인 중</p><p className="mt-2 text-sm font-black text-slate-900">{status}</p><p className="mt-3 text-xs leading-5 text-slate-600">{brief}</p></section><section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><div className="flex items-center gap-2"><HelpCircle size={16} className="text-blue-600"/><p className="text-sm font-black">안전 상담 안내</p></div><p className="mt-2 text-xs leading-5 text-slate-600">은행 또는 안전 상담 AI의 질문에는 기억나는 범위에서 답변해 주세요. 확실하지 않은 경우 “잘 모르겠어요”라고 답해도 됩니다.</p></section><section className={`rounded-2xl border p-4 shadow-sm ${hasLoss ? 'border-rose-200 bg-rose-50' : 'border-slate-200 bg-white'}`}><div className="flex items-center gap-2"><ShieldCheck size={16} className={hasLoss ? 'text-rose-600' : 'text-slate-500'}/><p className={`text-sm font-black ${hasLoss ? 'text-rose-800' : 'text-slate-800'}`}>피해구제 안내</p></div><p className={`mt-2 text-xs leading-5 ${hasLoss ? 'text-rose-700' : 'text-slate-600'}`}>{hasLoss ? '추가 송금을 멈추고 거래 내역과 대화 기록을 보관해 주세요. 은행 담당자가 필요한 절차를 안내합니다.' : '피해 여부가 확인되면 필요한 보호·피해구제 안내가 이곳에 표시됩니다.'}</p></section></aside></div></main></AppLayout>;
};
