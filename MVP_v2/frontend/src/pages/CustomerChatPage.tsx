import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, ArrowLeft, HelpCircle } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import { ChatWorkspace } from '../features/mvp-chat/ChatWorkspace';
import { RecoveryGuideCard } from '../features/mvp-chat/cards/RecoveryGuideCard';
import { CustomerCardRenderer } from '../features/mvp-chat/customer-cards/CustomerCardRenderer';
import { CustomerProgressCard } from '../features/mvp-chat/customer-cards/CustomerProgressCard';
import type { CustomerCardDescriptor } from '../features/mvp-chat/customer-cards/types';
import { useCaseSyncRefresh } from '../features/case-sync/useCaseSyncRefresh';
import { mvpChatApi, type CaseBundleV2, type CustomerQuestion, type MvpMessage } from '../services/mvpChatApi';

const customer = { user_id: 'mvp-v2-customer', display_name: '고객', role: 'CUSTOMER' };

export const CustomerChatPage: React.FC = () => {
  const { caseId = '' } = useParams();
  const [bundle, setBundle] = useState<CaseBundleV2 | null>(null);
  const [messages, setMessages] = useState<MvpMessage[]>([]);
  const [customerQuestions, setCustomerQuestions] = useState<CustomerQuestion[]>([]);
  const [recoveryActive, setRecoveryActive] = useState(() => localStorage.getItem(`mvp-v2:recovery:${caseId}`) === 'true');
  const [selectedRecoveryStep, setSelectedRecoveryStep] = useState<string | null>(() => localStorage.getItem(`mvp-v2:recovery-step:${caseId}`));
  const [answerReceipt, setAnswerReceipt] = useState<{ question: CustomerQuestion; answer: string } | null>(null);
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);

  const load = useCallback(async () => {
    const [nextBundle, nextMessages, nextQuestions] = await Promise.all([
      mvpChatApi.getBundle(caseId, 'customer'),
      mvpChatApi.listMessages(caseId, 'CUSTOMER', 'customer'),
      mvpChatApi.listCustomerQuestions(caseId, 'customer'),
    ]);
    setBundle(nextBundle);
    setMessages(nextMessages);
    setCustomerQuestions(nextQuestions);
    const recoveryFromServer = nextBundle.case.mode === 'RECOVERY' || nextBundle.case.victim_transfer_status === 'YES';
    const recoveryFromThisBrowser = localStorage.getItem(`mvp-v2:recovery:${caseId}`) === 'true';
    setRecoveryActive(recoveryFromServer || recoveryFromThisBrowser);
    setSelectedRecoveryStep(localStorage.getItem(`mvp-v2:recovery-step:${caseId}`));
  }, [caseId]);
  useCaseSyncRefresh(caseId, load);

  useEffect(() => { load().catch((reason) => setError(reason instanceof Error ? reason.message : 'Case를 불러오지 못했습니다.')); }, [load]);
  useEffect(() => { localStorage.setItem(`mvp-v2:recovery:${caseId}`, String(recoveryActive)); }, [caseId, recoveryActive]);
  useEffect(() => {
    if (selectedRecoveryStep) localStorage.setItem(`mvp-v2:recovery-step:${caseId}`, selectedRecoveryStep);
  }, [caseId, selectedRecoveryStep]);
  useEffect(() => { const timer = window.setInterval(() => { load().catch(() => undefined); }, 3000); return () => window.clearInterval(timer); }, [load]);
  useEffect(() => {
    const beat = () => mvpChatApi.heartbeat(caseId, { ...customer, presence: 'VIEWING', channel: 'CUSTOMER' }).catch(() => undefined);
    void beat();
    const timer = window.setInterval(beat, 10_000);
    return () => window.clearInterval(timer);
  }, [caseId]);

  const uploadFile = (file: File) => mvpChatApi.uploadAttachment(caseId, file, customer.display_name, 'CUSTOMER');
  const send = async (content: string, attachmentIds: string[] = []) => {
    setSending(true);
    try {
      const message = await mvpChatApi.createMessage(caseId, {
        actor_type: 'CUSTOMER', actor_user_id: customer.user_id, actor_display_name: customer.display_name,
        actor_role: customer.role, content, channel: 'CUSTOMER', audience: 'CUSTOMER', visibility: 'CUSTOMER',
        message_kind: 'CHAT', attachment_ids: attachmentIds,
      });
      setMessages((items) => [...items, message]);
    } finally { setSending(false); }
  };

  const currentCase = bundle?.case ?? {};
  const status = String(currentCase.status ?? '확인 중');
  const visibleMessages = useMemo(() => {
    const cardQuestionTexts = new Set(customerQuestions.map((question) => question.question_text.trim()));
    return messages.filter((message) => message.visibility === 'CUSTOMER'
      && !(message.actor_type === 'CUSTOMER_AGENT' && cardQuestionTexts.has(message.content.trim())));
  }, [customerQuestions, messages]);
  const activeQuestion = customerQuestions.find((question) => question.status === 'ASKED') ?? null;

  const answerQuestion = async (answer: string) => {
    if (!activeQuestion) return;
    setSending(true);
    setError('');
    try {
      await mvpChatApi.answerCustomerQuestion(caseId, activeQuestion.question_id, answer, customer);
      setAnswerReceipt({ question: activeQuestion, answer });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '답변을 저장하지 못했습니다.');
      setSending(false);
      return;
    }
    try { await load(); } catch { setError('답변은 접수됐지만 최신 화면을 불러오지 못했습니다. 새로고침해 주세요.'); }
    finally { setSending(false); }
  };

  const startRecovery = async () => {
    if (recoveryActive || sending) return;
    setRecoveryActive(true);
    setSending(true);
    try { await mvpChatApi.startCustomerEmergency(caseId, customer); }
    catch { setError('피해구제 안내는 시작됐지만 AI 개인 작업공간과 사건 진행 현황 알림을 생성하지 못했습니다. 다시 누르지 말고 담당자에게 알려 주세요.'); }
    try { await load(); } catch { setError('피해구제 안내는 시작됐지만 최신 화면을 불러오지 못했습니다. 새로고침해 주세요.'); }
    finally { setSending(false); }
  };

  const requestRecoveryHelp = async (kind: 'AI_ADVICE' | 'HUMAN_HANDOFF', step: string) => {
    setSending(true);
    setError('');
    const label = kind === 'AI_ADVICE' ? 'AI 맞춤 조언' : '은행 담당자 지원';
    try {
      await mvpChatApi.createMessage(caseId, {
        actor_type: 'CUSTOMER', actor_user_id: customer.user_id, actor_display_name: customer.display_name,
        actor_role: customer.role, content: `${step} 단계에 대해 ${label}을 요청합니다.`,
        channel: 'CUSTOMER', audience: 'CUSTOMER', visibility: 'CUSTOMER', message_kind: 'CHAT',
      });
      try {
        await mvpChatApi.createMessage(caseId, {
          actor_type: 'CUSTOMER_AGENT', actor_user_id: 'customer-agent', actor_display_name: 'Customer Agent', actor_role: null,
          content: `고객이 피해구제 ‘${step}’ 단계의 ${label}을 요청했습니다.`,
          channel: 'TEAM', audience: 'BANK_INTERNAL', visibility: 'BANK_INTERNAL', message_kind: 'SYSTEM_EVENT',
        });
      } catch {
        setError('요청은 접수됐지만 은행 협업 알림을 동기화하지 못했습니다. 다시 요청하지 말고 담당자에게 확인해 주세요.');
      }
      await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : '피해구제 지원을 요청하지 못했습니다.'); }
    finally { setSending(false); }
  };

  const customerCards = useMemo<CustomerCardDescriptor[]>(() => {
    const cards: CustomerCardDescriptor[] = [];
    const answeredQuestions = customerQuestions.filter((question) => question.status === 'ANSWERED' && question.answer_text);
    for (const question of answeredQuestions) cards.push({
      card_id: `receipt-${question.question_id}`, card_type: 'ANSWER_RECEIPT',
      payload: { question, answer: question.answer_text! },
    });
    if (answerReceipt && !answeredQuestions.some((question) => question.question_id === answerReceipt.question.question_id)) {
      cards.push({ card_id: `receipt-${answerReceipt.question.question_id}`, card_type: 'ANSWER_RECEIPT', payload: answerReceipt });
    }
    if (activeQuestion) cards.push({ card_id: `question-${activeQuestion.question_id}`, card_type: 'QUESTION', payload: { question: activeQuestion } });
    if (recoveryActive && selectedRecoveryStep) cards.push({ card_id: `recovery-${selectedRecoveryStep}`, card_type: 'RECOVERY_STEP', payload: { stepId: selectedRecoveryStep } });
    for (const result of bundle?.customer_verification_results ?? []) cards.push({
      card_id: `verification-${result.verification_task_id}`, card_type: 'VERIFICATION_RESULT', payload: { result },
    });
    return cards;
  }, [activeQuestion, answerReceipt, bundle?.customer_verification_results, customerQuestions, recoveryActive, selectedRecoveryStep]);

  return <AppLayout>
    <main className="min-w-0 py-6 lg:ml-64">
      <div className="mb-4 flex items-center justify-between"><Link to={`/cases/${caseId}`} className="inline-flex items-center gap-1 text-sm font-bold text-slate-500"><ArrowLeft size={16}/> Case로 돌아가기</Link><span className="text-[11px] font-bold text-slate-400">CUSTOMER SAFETY CHAT</span></div>
      <section className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3"><div className="flex items-center gap-3"><AlertTriangle className="text-rose-600" size={20}/><div><p className="text-sm font-black text-rose-800">지금은 송금·인증정보 제공을 멈춰주세요.</p><p className="mt-0.5 text-xs text-rose-700">상대방이 알려준 연락처가 아닌 공식 채널로만 확인해 주세요.</p></div></div><span className="rounded-full bg-white px-3 py-1 text-xs font-bold text-rose-700">{status}</span></section>
      <section className="mb-4 flex items-center justify-between gap-3 rounded-2xl border border-rose-200 bg-white px-4 py-3 shadow-sm"><div><p className="text-sm font-black text-rose-800">이미 사기 피해가 발생했나요?</p><p className="mt-1 text-xs text-slate-500">송금·정보 노출 피해가 있다면 즉시 대응 절차를 확인하세요.</p></div><button type="button" onClick={() => void startRecovery()} disabled={recoveryActive || sending} className="rounded-xl bg-rose-600 px-4 py-2.5 text-xs font-black text-white disabled:opacity-50">{recoveryActive ? '피해구제 안내 진행 중' : '이미 사기 당했어요'}</button></section>
      {error && <p className="mb-4 rounded-xl bg-rose-50 p-3 text-sm font-semibold text-rose-700">{error}</p>}
      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_280px]">
        <div className="order-1 min-w-0 self-start lg:col-start-1 lg:row-start-1">
          <ChatWorkspace
            title="보이스피싱 대응 AI 챗봇"
            description="현재 상황을 알려주시면 필요한 내용을 차례로 확인합니다."
            channelLabel="고객 공개 채널"
            messages={visibleMessages}
            placeholder="상대방이 요구한 내용이나 현재 상황을 입력하세요."
            currentUserId={customer.user_id}
            sending={sending}
            onSend={send}
            onUploadFile={uploadFile}
            attachmentView="customer"
            toolCardsActive={customerCards.length > 0}
            toolCards={<CustomerCardRenderer cards={customerCards} submitting={sending} onAnswer={answerQuestion} onRecoveryRequest={requestRecoveryHelp}/>}
            heightClassName="h-[814px]"
          />
        </div>
        <aside className="order-2 min-w-0 self-start space-y-4 lg:col-start-2 lg:row-start-1">
          <CustomerProgressCard currentCase={currentCase} questions={customerQuestions} verificationCount={bundle?.customer_verification_results?.length ?? 0} recoveryActive={recoveryActive}/>
          {recoveryActive
            ? <RecoveryGuideCard selectedStepId={selectedRecoveryStep} onSelectStep={setSelectedRecoveryStep}/>
            : <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><div className="flex items-center gap-2"><HelpCircle size={16} className="text-blue-600"/><p className="text-sm font-black">안전 상담 안내</p></div><p className="mt-2 text-xs leading-5 text-slate-600">은행원 또는 AI 챗봇의 질문에는 기억나는 범위에서 답변해 주세요. 확실하지 않은 경우 “잘 모르겠어요”라고 답해도 됩니다.</p></section>}
        </aside>
      </div>
    </main>
  </AppLayout>;
};
