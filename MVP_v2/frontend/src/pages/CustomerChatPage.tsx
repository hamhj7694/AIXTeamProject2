import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AlertTriangle, CheckCircle2, HelpCircle } from 'lucide-react';
import { useParams } from 'react-router-dom';
import { CustomerLayout } from '../components/layout/CustomerLayout';
import { ChatWorkspace } from '../features/mvp-chat/ChatWorkspace';
import { RecoveryGuideCard } from '../features/mvp-chat/cards/RecoveryGuideCard';
import { CustomerCardRenderer } from '../features/mvp-chat/customer-cards/CustomerCardRenderer';
import { CustomerProgressCard } from '../features/mvp-chat/customer-cards/CustomerProgressCard';
import { RecoveryStepDetailCard } from '../features/mvp-chat/customer-cards/RecoveryStepDetailCard';
import type { CustomerCardDescriptor } from '../features/mvp-chat/customer-cards/types';
import { useCaseSyncRefresh } from '../features/case-sync/useCaseSyncRefresh';
import { mvpChatApi, type CaseBundleV2, type CustomerQuestion, type MvpMessage } from '../services/mvpChatApi';
import { workflowStatusLabel } from '../utils/casePresentation';

const customer = { user_id: 'mvp-v2-customer', display_name: '고객', role: 'CUSTOMER' };

export const CustomerChatPage: React.FC = () => {
  const { caseId = '' } = useParams();
  const [bundle, setBundle] = useState<CaseBundleV2 | null>(null);
  const [messages, setMessages] = useState<MvpMessage[]>([]);
  const [customerQuestions, setCustomerQuestions] = useState<CustomerQuestion[]>([]);
  const [recoveryActive, setRecoveryActive] = useState(() => localStorage.getItem(`mvp-v2:recovery:${caseId}`) === 'true');
  const [selectedRecoveryStep, setSelectedRecoveryStep] = useState<string | null>(() => localStorage.getItem(`mvp-v2:recovery-step:${caseId}`));
  const [answerReceipt, setAnswerReceipt] = useState<{ question: CustomerQuestion; answer: string; createdAt: string } | null>(null);
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const ensuredQuestionsRef = useRef(false);

  useEffect(() => { ensuredQuestionsRef.current = false; }, [caseId]);

  const load = useCallback(async () => {
    const nextBundle = await mvpChatApi.getBundle(caseId, 'customer');
    setBundle(nextBundle);
    setMessages(nextBundle.recent_messages);
    setCustomerQuestions(nextBundle.questions as CustomerQuestion[]);
    const recoveryFromServer = nextBundle.case.mode === 'RECOVERY' || nextBundle.case.victim_transfer_status === 'YES';
    const recoveryFromThisBrowser = localStorage.getItem(`mvp-v2:recovery:${caseId}`) === 'true';
    setRecoveryActive(recoveryFromServer || recoveryFromThisBrowser);
    setSelectedRecoveryStep(localStorage.getItem(`mvp-v2:recovery-step:${caseId}`));
    setLoading(false);
  }, [caseId]);
  useCaseSyncRefresh(caseId, load);

  useEffect(() => { load().catch((reason) => setError(reason instanceof Error ? reason.message : 'Case를 불러오지 못했습니다.')); }, [load]);
  useEffect(() => {
    if (loading || ensuredQuestionsRef.current || String(bundle?.case.status ?? '') === 'CLOSED') return;
    const hasOpenQuestion = customerQuestions.some((question) => question.status === 'ASKED' || question.status === 'PENDING');
    if (hasOpenQuestion) return;
    ensuredQuestionsRef.current = true;
    let active = true;
    mvpChatApi.ensureAiCustomerQuestions(caseId)
      .then(() => { if (active) { setError(''); return load(); } })
      .catch((reason) => active && setError(reason instanceof Error ? reason.message : '안전 확인 질문을 준비하지 못했습니다. 잠시 후 다시 시도해 주세요.'));
    return () => { active = false; };
  }, [bundle?.case.status, caseId, customerQuestions, load, loading]);
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
    setError('');
    try {
      const message = await mvpChatApi.createMessage(caseId, {
        actor_type: 'CUSTOMER', actor_user_id: customer.user_id, actor_display_name: customer.display_name,
        actor_role: customer.role, content, channel: 'CUSTOMER', audience: 'CUSTOMER', visibility: 'CUSTOMER',
        message_kind: 'CHAT', attachment_ids: attachmentIds,
      });
      setMessages((items) => [...items, message]);
      if (content.trim()) {
        try {
          const reply = await mvpChatApi.invokeCustomerAgent(caseId, content, message.message_id, customer);
          setMessages((items) => [...items, reply]);
        } catch (reason) {
          setError(reason instanceof Error
            ? `메시지는 전달됐지만 AI 답변을 만들지 못했습니다. ${reason.message}`
            : '메시지는 전달됐지만 AI 답변을 만들지 못했습니다.');
        }
      }
    } finally { setSending(false); }
  };

  const currentCase = bundle?.case ?? {};
  const status = String(currentCase.status ?? '확인 중');
  const visibleMessages = useMemo(() => {
    const cardQuestionTexts = new Set(customerQuestions.map((question) => question.question_text.trim()));
    const answeredMessageIds = new Set(customerQuestions.map((question) => question.answer_message_id).filter(Boolean));
    return messages.filter((message) => message.visibility === 'CUSTOMER'
      && !(message.actor_type === 'CUSTOMER_AGENT' && cardQuestionTexts.has(message.content.trim()))
      && !answeredMessageIds.has(message.message_id));
  }, [customerQuestions, messages]);
  const activeQuestion = customerQuestions.find((question) => question.status === 'ASKED') ?? null;

  const answerQuestion = async (answer: string) => {
    if (!activeQuestion) return;
    setSending(true);
    setError('');
    try {
      await mvpChatApi.answerCustomerQuestion(caseId, activeQuestion.question_id, answer, customer);
      setAnswerReceipt({ question: activeQuestion, answer, createdAt: new Date().toISOString() });
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
    setSending(true);
    setError('');
    try {
      await mvpChatApi.startCustomerEmergency(caseId, customer);
      setRecoveryActive(true);
      await load();
    } catch (reason) {
      setRecoveryActive(false);
      setError(reason instanceof Error ? reason.message : '피해구제 요청을 접수하지 못했습니다. 잠시 후 다시 시도해 주세요.');
    }
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
      created_at: question.answered_at ?? question.asked_at ?? new Date(0).toISOString(),
      payload: { question, answer: question.answer_text! },
    });
    if (answerReceipt && !answeredQuestions.some((question) => question.question_id === answerReceipt.question.question_id)) {
      cards.push({ card_id: `receipt-${answerReceipt.question.question_id}`, card_type: 'ANSWER_RECEIPT', created_at: answerReceipt.createdAt, payload: answerReceipt });
    }
    if (activeQuestion) cards.push({ card_id: `question-${activeQuestion.question_id}`, card_type: 'QUESTION', created_at: activeQuestion.asked_at ?? new Date().toISOString(), payload: { question: activeQuestion } });
    for (const result of bundle?.customer_verification_results ?? []) cards.push({
      card_id: `verification-${result.verification_task_id}`, card_type: 'VERIFICATION_RESULT', created_at: result.published_at ?? String(currentCase.updated_at ?? new Date().toISOString()), payload: { result },
    });
    return cards;
  }, [activeQuestion, answerReceipt, bundle?.customer_verification_results, customerQuestions, recoveryActive, selectedRecoveryStep]);
  const customerTimelineCards = useMemo(() => customerCards.map((card) => ({
    id: card.card_id,
    createdAt: card.created_at,
    content: <CustomerCardRenderer cards={[card]} submitting={sending} onAnswer={answerQuestion} onRecoveryRequest={requestRecoveryHelp}/>,
  })), [customerCards, sending]);

  const closed = status === 'CLOSED';
  const safetyCopy = closed
    ? { title: '상담이 마무리되었습니다.', detail: '추가 피해가 의심되면 공식 은행 고객센터로 다시 상담을 요청해 주세요.', tone: 'border-emerald-200 bg-emerald-50 text-emerald-800' }
    : recoveryActive
      ? { title: '피해구제 절차를 함께 진행하고 있습니다.', detail: '아래 진행 단계와 공식 연락처를 확인하고, 추가 송금과 상대방 접촉은 중단해 주세요.', tone: 'border-rose-200 bg-rose-50 text-rose-800' }
      : { title: '지금은 송금·인증정보 제공을 멈춰주세요.', detail: '상대방이 알려준 연락처가 아닌 공식 채널로만 확인해 주세요.', tone: 'border-rose-200 bg-rose-50 text-rose-800' };

  return <CustomerLayout>
    <main className="min-w-0 py-6">
      <div className="mb-4 flex items-center justify-between"><p className="text-sm font-black text-slate-800">안전 상담 세션</p><span className="text-[11px] font-bold text-slate-400">CUSTOMER SAFETY CHAT</span></div>
      <section className={`mb-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border px-4 py-3 ${safetyCopy.tone}`}><div className="flex items-center gap-3">{closed ? <CheckCircle2 size={20}/> : <AlertTriangle size={20}/>}<div><p className="text-sm font-black">{safetyCopy.title}</p><p className="mt-0.5 text-xs opacity-90">{safetyCopy.detail}</p></div></div><span className="rounded-full bg-white px-3 py-1 text-xs font-bold">{workflowStatusLabel(status)}</span></section>
      {!closed && <section className="mb-4 flex items-center justify-between gap-3 rounded-2xl border border-rose-200 bg-white px-4 py-3 shadow-sm"><div><p className="text-sm font-black text-rose-800">이미 사기 피해가 발생했나요?</p><p className="mt-1 text-xs text-slate-500">송금·정보 노출 피해가 있다면 즉시 대응 절차를 확인하세요.</p></div><button type="button" onClick={() => void startRecovery()} disabled={recoveryActive || sending} className="rounded-xl bg-rose-600 px-4 py-2.5 text-xs font-black text-white disabled:opacity-50">{recoveryActive ? '피해구제 안내 진행 중' : '이미 사기 당했어요'}</button></section>}
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
            timelineCards={customerTimelineCards}
            heightClassName="h-[814px]"
            draftStorageKey={`mvp-v2:draft:${caseId}:customer`}
            disabled={loading || closed}
            loading={loading}
          />
        </div>
        <aside className="order-2 min-w-0 self-start space-y-4 lg:col-start-2 lg:row-start-1">
          <CustomerProgressCard currentCase={currentCase} questions={customerQuestions} verificationCount={bundle?.customer_verification_results?.length ?? 0} recoveryActive={recoveryActive}/>
          {recoveryActive
            ? <RecoveryGuideCard selectedStepId={selectedRecoveryStep} onSelectStep={setSelectedRecoveryStep}/>
            : <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><div className="flex items-center gap-2"><HelpCircle size={16} className="text-blue-600"/><p className="text-sm font-black">안전 상담 안내</p></div><p className="mt-2 text-xs leading-5 text-slate-600">은행원 또는 AI 챗봇의 질문에는 기억나는 범위에서 답변해 주세요. 확실하지 않은 경우 “잘 모르겠어요”라고 답해도 됩니다.</p></section>}
        </aside>
      </div>
      {recoveryActive && <section id="customer-recovery-detail" className="mt-4 space-y-4">
        {selectedRecoveryStep && (
          <RecoveryStepDetailCard stepId={selectedRecoveryStep} onRequest={requestRecoveryHelp}/>
        )}
      </section>}
    </main>
  </CustomerLayout>;
};
