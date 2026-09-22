import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AlertCircle, AlertTriangle, ArrowLeft, Bookmark, CheckCircle2, ChevronDown, Loader2, PanelRightClose, PanelRightOpen, RefreshCw, ShieldCheck, Wifi, X } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { casesApi, CURRENT_CUSTOMER_USER } from '../api/cases';
import { isApiErrorCode } from '../api/client';
import type { CaseBundle, CaseMessage, CustomerQuestion, ProgressStep } from '../api/types';
import { readCustomerBookmarks, writeCustomerBookmarks, type CustomerBookmark } from '../customer/bookmarks';
import { CustomerBookmarks } from '../customer/CustomerBookmarks';
import { CustomerComposer } from '../customer/CustomerComposer';
import { CustomerConversation } from '../customer/CustomerConversation';
import { CustomerProgressPanel, CustomerSafetyGuide } from '../customer/CustomerProgressPanel';
import { RecoveryNavigator } from '../customer/RecoveryCards';
import { RECOVERY_MESSAGE_PREFIX, recoveryStepFromMessage, type RecoveryStep, type RecoveryStepId } from '../customer/recovery';
import { buildCustomerTimeline } from '../customer/timeline';
import { mergePendingMessages, removeMessage, upsertMessage } from '../api/messageState';
import { generateUuid } from '../uuid';
import { buildConsecutiveCustomerAiPrompt, ConsecutiveAiBatcher, type AiBatchControl } from '../bank/consecutiveAiBatch';

type CustomerOutboxItem = {
  message: CaseMessage;
  content: string;
  requestAi: boolean;
};

export const CustomerCaseRoomPage: React.FC = () => {
  const { caseId = '' } = useParams();
  const [bundle, setBundle] = useState<CaseBundle | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [aiPendingCount, setAiPendingCount] = useState(0);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [confirmRecovery, setConfirmRecovery] = useState(false);
  const [bookmarkOpen, setBookmarkOpen] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [selectedRecoveryStep, setSelectedRecoveryStep] = useState<RecoveryStepId | null>(null);
  const [bookmarks, setBookmarks] = useState<CustomerBookmark[]>([]);
  const aiBatcherRef = useRef<ConsecutiveAiBatcher | null>(null);
  const enqueueCustomerAiReplyRef = useRef<(prompt: string, replyToMessageId: string, sourceMessageIds: string[], control: AiBatchControl) => Promise<void>>(async () => undefined);
  const aiGenerationRef = useRef(0);
  const activeCaseIdRef = useRef(caseId);
  activeCaseIdRef.current = caseId;
  const loadRequestRef = useRef(0);
  const pendingMessagesRef = useRef(new Map<string, CaseMessage>());
  const outboxRef = useRef(new Map<string, CustomerOutboxItem>());

  const load = useCallback(async (quiet = false) => {
    if (!caseId) return;
    const requestId = ++loadRequestRef.current;
    if (quiet) setRefreshing(true); else setLoading(true);
    try {
      const nextBundle = await casesApi.customerBundle(caseId);
      if (requestId !== loadRequestRef.current) return;
      setBundle({ ...nextBundle, recent_messages: mergePendingMessages(nextBundle.recent_messages, pendingMessagesRef.current.values()) });
      setError('');
    }
    catch (reason) { if (requestId === loadRequestRef.current && !quiet) setError(reason instanceof Error ? reason.message : '안전 상담 정보를 불러오지 못했습니다.'); }
    finally { if (requestId === loadRequestRef.current) { setLoading(false); setRefreshing(false); } }
  }, [caseId]);

  const showMessage = (message: CaseMessage) => {
    setBundle((current) => current && current.case.case_id === message.case_id ? {
      ...current,
      recent_messages: upsertMessage(current.recent_messages, message),
    } : current);
  };

  const enqueueCustomerAiReply = useCallback(async (prompt: string, replyToMessageId: string, sourceMessageIds: string[], control: AiBatchControl) => {
    const generation = aiGenerationRef.current;
    const targetCaseId = caseId;
    if (aiGenerationRef.current !== generation || activeCaseIdRef.current !== targetCaseId || control.isSuperseded()) return;
    setAiPendingCount((count) => count + 1);
    let pendingReleased = false;
    const releasePending = () => {
      if (pendingReleased) return;
      pendingReleased = true;
      setAiPendingCount((count) => Math.max(0, count - 1));
    };
    try {
      // 서버는 이 호출 시점의 고객 공개 대화와 누적 질문 답변을 다시 읽는다.
      const message = await casesApi.invokeCustomerAi(targetCaseId, prompt, replyToMessageId, sourceMessageIds, control.signal);
      if (aiGenerationRef.current === generation && !control.isSuperseded()) {
        // Remove the thinking bubble before adding the completed answer so
        // the two states are never rendered together.
        releasePending();
        loadRequestRef.current += 1;
        showMessage(message);
        await load(true);
      }
    } catch (reason) {
      if (isApiErrorCode(reason, 'AI_GENERATION_STALE')) { control.supersedeIfPending(); return; }
      if (control.isSuperseded()) return;
      if (aiGenerationRef.current === generation) {
        setNotice(`메시지는 전달됐지만 실제 AI 서버가 응답하지 않았습니다. 임의 안내는 생성하지 않았습니다. ${reason instanceof Error ? reason.message : '잠시 후 다시 요청해 주세요.'}`);
      }
    } finally {
      if (aiGenerationRef.current === generation) releasePending();
    }
  }, [caseId, load]);
  enqueueCustomerAiReplyRef.current = enqueueCustomerAiReply;

  useEffect(() => {
    aiBatcherRef.current?.dispose();
    aiBatcherRef.current = new ConsecutiveAiBatcher(async (messages, control) => {
      const lastMessage = messages[messages.length - 1];
      await enqueueCustomerAiReplyRef.current(
        buildConsecutiveCustomerAiPrompt(messages), lastMessage.messageId,
        messages.map((message) => message.messageId), control,
      );
    });
    aiGenerationRef.current += 1;
    loadRequestRef.current += 1;
    pendingMessagesRef.current.clear();
    outboxRef.current.clear();
    setAiPendingCount(0); setBusy(false);
    setBundle(null); setError(''); setNotice(''); setLoading(true); setConfirmRecovery(false); setDetailsOpen(false); setSelectedRecoveryStep(null);
    setBookmarks(readCustomerBookmarks(caseId));
    void load();
    const heartbeat = () => { void casesApi.heartbeat(caseId, CURRENT_CUSTOMER_USER, 'VIEWING', 'CUSTOMER').catch(() => undefined); };
    heartbeat();
    const timer = window.setInterval(() => void load(true), 4000);
    const presenceTimer = window.setInterval(heartbeat, 30000);
    return () => { aiBatcherRef.current?.dispose(); aiBatcherRef.current = null; aiGenerationRef.current += 1; loadRequestRef.current += 1; window.clearInterval(timer); window.clearInterval(presenceTimer); };
  }, [caseId, load]);

  useEffect(() => {
    if (!detailsOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === 'Escape') setDetailsOpen(false); };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [detailsOpen]);

  const refresh = async () => { await load(true); };
  const requestProgressConfirmation = async (step: ProgressStep) => {
    const items = await casesApi.requestProgressConfirmation(caseId, step);
    loadRequestRef.current += 1;
    setBundle((current) => current ? { ...current, customer_progress: items } : current);
  };
  const recovery = String(bundle?.case.mode ?? '') === 'RECOVERY' || String(bundle?.case.victim_transfer_status ?? '') === 'YES';
  useEffect(() => {
    if (recovery) setDetailsOpen(true);
  }, [recovery]);
  const timelineSelectedStep = useMemo<RecoveryStepId | null>(() => {
    if (!bundle) return null;
    const latestRecoveryEntry = [...buildCustomerTimeline(bundle)].reverse()
      .find((entry) => entry.kind === 'RECOVERY_STEP');
    const step = latestRecoveryEntry?.data as { step: RecoveryStep } | undefined;
    return step?.step.id ?? null;
  }, [bundle]);
  const selectedStep = selectedRecoveryStep ?? timelineSelectedStep;
  const closed = String(bundle?.case.status ?? '') === 'CLOSED' || String(bundle?.case.mode ?? '') === 'CLOSED';
  const recoveryUiActive = recovery || detailsOpen || confirmRecovery;

  const deliverMessage = async (item: CustomerOutboxItem) => {
    const generation = aiGenerationRef.current;
    const isCurrent = () => generation === aiGenerationRef.current && activeCaseIdRef.current === item.message.case_id;
    if (!isCurrent()) return false;
    setBusy(true); setError(''); setNotice('');
    const sendingMessage = { ...item.message, delivery_state: 'SENDING' as const, delivery_error: null };
    item.message = sendingMessage;
    pendingMessagesRef.current.set(sendingMessage.client_request_id!, sendingMessage);
    showMessage(sendingMessage);
    try {
      const message = await casesApi.sendCustomerMessage(caseId, item.content, item.message.client_request_id!);
      if (!isCurrent()) return false;
      loadRequestRef.current += 1;
      pendingMessagesRef.current.delete(item.message.client_request_id!);
      outboxRef.current.delete(item.message.client_request_id!);
      showMessage(message);
      if (!(item.requestAi && item.content)) {
        window.requestAnimationFrame(() => { if (isCurrent()) void refresh(); });
      }
      return message;
    } catch (reason) {
      const failed = {
        ...item.message,
        delivery_state: 'FAILED' as const,
        delivery_error: reason instanceof Error ? reason.message : '서버에 전송하지 못했습니다.',
      };
      if (!isCurrent()) return false;
      item.message = failed;
      pendingMessagesRef.current.set(failed.client_request_id!, failed);
      showMessage(failed);
      setError('메시지를 전송하지 못했습니다. 말풍선의 다시 전송을 눌러주세요.');
      return false;
    } finally { if (isCurrent()) setBusy(false); }
  };
  const queueCustomerAi = (item: CustomerOutboxItem, saved: Promise<CaseMessage | false>) => {
    if (!item.requestAi || !item.content) return;
    aiBatcherRef.current?.enqueue({
      caseId: item.message.case_id,
      requesterUserId: CURRENT_CUSTOMER_USER.user_id,
      channel: 'CUSTOMER',
      messageId: item.message.client_request_id!,
      content: item.content,
      saved: saved.then((message) => message ? { messageId: message.message_id, createdAt: message.created_at } : false),
    });
  };
  const send = (content: string, requestAi: boolean): Promise<void> => {
    const clientRequestId = generateUuid();
    const message: CaseMessage = {
      message_id: `pending-${clientRequestId}`,
      client_request_id: clientRequestId,
      case_id: caseId,
      actor_type: 'CUSTOMER',
      actor_user_id: CURRENT_CUSTOMER_USER.user_id,
      actor_display_name: CURRENT_CUSTOMER_USER.display_name,
      actor_role: CURRENT_CUSTOMER_USER.role,
      content,
      channel: 'CUSTOMER',
      audience: 'CUSTOMER',
      visibility: 'CUSTOMER',
      message_kind: 'CHAT',
      private_owner_user_id: null,
      mentions: [],
      reply_to_message_id: null,
      attachments: [],
      created_at: new Date().toISOString(),
      delivery_state: 'SENDING',
      delivery_error: null,
    };
    const item: CustomerOutboxItem = { message, content, requestAi };
    pendingMessagesRef.current.set(clientRequestId, message);
    outboxRef.current.set(clientRequestId, item);
    showMessage(message);
    const saved = deliverMessage(item);
    queueCustomerAi(item, saved);
    void saved;
    return Promise.resolve();
  };
  const retryMessage = (message: CaseMessage) => {
    if (busy || !message.client_request_id) return;
    const item = outboxRef.current.get(message.client_request_id);
    if (item) {
      const saved = deliverMessage(item);
      queueCustomerAi(item, saved);
      void saved;
    }
  };
  const dismissMessage = (message: CaseMessage) => {
    if (!message.client_request_id) return;
    pendingMessagesRef.current.delete(message.client_request_id);
    outboxRef.current.delete(message.client_request_id);
    setBundle((current) => current ? { ...current, recent_messages: removeMessage(current.recent_messages, message) } : current);
  };

  const answer = async (question: CustomerQuestion, structuredAnswer: import('../api/types').StructuredQuestionAnswer) => {
    setBusy(true); setError(''); setNotice('');
    try {
      await casesApi.answerCustomerQuestion(caseId, question.question_id, structuredAnswer);
      try { await refresh(); } catch { setNotice('답변은 접수됐지만 최신 화면을 갱신하지 못했습니다. 다시 요청하지 말고 새로고침해 주세요.'); }
    } finally { setBusy(false); }
  };

  const startRecovery = async () => {
    if (recovery || busy) return;
    setBusy(true); setError(''); setNotice('');
    try {
      const message = await casesApi.startCustomerEmergency(caseId);
      loadRequestRef.current += 1;
      showMessage(message); setConfirmRecovery(false); setDetailsOpen(true);
      window.requestAnimationFrame(() => { void refresh(); });
    }
    catch (reason) { setError(reason instanceof Error ? reason.message : '피해구제 요청을 접수하지 못했습니다.'); }
    finally { setBusy(false); }
  };

  const selectRecoveryStep = async (step: RecoveryStep) => {
    const existing = bundle?.recent_messages.find((message) => message.content === `${RECOVERY_MESSAGE_PREFIX} ${step.title}`);
    if (existing) { setSelectedRecoveryStep(step.id); document.getElementById(`recovery-${existing.message_id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }); return; }
    setBusy(true); setError('');
    try {
      const message = await casesApi.sendCustomerMessage(caseId, `${RECOVERY_MESSAGE_PREFIX} ${step.title}`);
      loadRequestRef.current += 1;
      showMessage(message);
      setSelectedRecoveryStep(step.id);
      window.requestAnimationFrame(() => { void refresh(); });
      window.setTimeout(() => document.getElementById(`recovery-${message.message_id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 60);
    } catch (reason) { setError(reason instanceof Error ? reason.message : '피해구제 절차를 열지 못했습니다.'); }
    finally { setBusy(false); }
  };

  const requestRecoveryHelp = async (kind: 'AI_ADVICE' | 'HUMAN_HANDOFF', step: RecoveryStep) => {
    setBusy(true); setError(''); setNotice('');
    try {
      const label = kind === 'AI_ADVICE' ? '내 상황에 맞는 AI 조언' : '은행 담당자 지원';
      const message = await casesApi.sendCustomerMessage(caseId, `${step.title} 단계에 대해 ${label}을 요청합니다.`);
      loadRequestRef.current += 1;
      showMessage(message);
      if (kind === 'AI_ADVICE') {
        aiBatcherRef.current?.enqueue({
          caseId, requesterUserId: CURRENT_CUSTOMER_USER.user_id, channel: 'CUSTOMER',
          messageId: message.message_id,
          content: `${step.title} 피해구제 단계에서 제가 지금 해야 할 일을 쉬운 순서로 알려주세요.`,
          saved: Promise.resolve({ messageId: message.message_id, createdAt: message.created_at }),
        });
      } else {
        window.requestAnimationFrame(() => { void refresh(); });
      }
    } finally { setBusy(false); }
  };

  const toggleBookmark = (bookmark: CustomerBookmark) => {
    const next = bookmarks.some((item) => item.entryId === bookmark.entryId) ? bookmarks.filter((item) => item.entryId !== bookmark.entryId) : [...bookmarks, bookmark];
    setBookmarks(next); writeCustomerBookmarks(caseId, next);
  };

  if (loading && !bundle) return <div className="customer-page"><section className="customer-room-state"><Loader2 className="spin" size={26}/><strong>안전 상담 정보를 불러오고 있습니다.</strong><span>현재 Case의 공개 정보를 준비합니다.</span></section></div>;
  if (!bundle) return <div className="customer-page"><section className="customer-room-state error"><AlertCircle size={25}/><strong>안전 상담을 열지 못했습니다.</strong><span>{error || '잠시 후 다시 시도해 주세요.'}</span><button onClick={() => void load()}>다시 시도</button></section></div>;

  return <div className={`customer-page ${recovery ? 'is-recovery' : ''}`}>
    <Link className="customer-demo-switch" to={`/cases/${encodeURIComponent(caseId)}`} aria-label="은행 화면으로"><ArrowLeft size={15}/>은행 화면으로</Link><header className="customer-header"><div className="customer-header-brand"><span><ShieldCheck size={18}/></span><b>CSR | Case Share Room</b><small>{caseId} · 고객 안전 상담</small></div><div className="customer-header-actions"><span><Wifi size={13}/>안전하게 연결됨</span><button type="button" onClick={() => setBookmarkOpen(true)}><Bookmark size={16}/>북마크{bookmarks.length > 0 && <b>{bookmarks.length}</b>}</button><button type="button" onClick={() => void load(true)} aria-label="상담 내용 새로고침"><RefreshCw size={16} className={refreshing ? 'spin' : ''}/></button></div></header>
    <main className="customer-main">
      {error && <div className="customer-global-message danger"><AlertCircle size={16}/><span>{error}</span><button type="button" onClick={() => setError('')} aria-label="오류 닫기"><X size={15}/></button></div>}
      {notice && <div className="customer-global-message"><AlertCircle size={16}/><span>{notice}</span><button type="button" onClick={() => setNotice('')} aria-label="안내 닫기"><X size={15}/></button></div>}
      <div className="customer-room-grid">

        {/* <section className="customer-chat-panel"><header><div><h1>보이스피싱 대응 AI 상담</h1><p>필요한 내용을 한 가지씩 확인하고 은행 담당자와 연결합니다.</p></div><span>고객 공개 채널</span></header><div className="customer-conversation-host"><CustomerConversation bundle={bundle} busy={busy} aiBusy={aiPendingCount > 0} bookmarkedIds={new Set(bookmarks.map((item) => item.entryId))} onAnswer={answer} onRecoveryRequest={requestRecoveryHelp} onToggleBookmark={toggleBookmark} onRetryMessage={retryMessage} onDismissMessage={dismissMessage}/><CustomerBookmarks open={bookmarkOpen} items={bookmarks} onClose={() => setBookmarkOpen(false)}/></div><section className={`customer-recovery-guide ${closed ? 'closed' : recovery ? 'recovery' : ''}`}>
          <div className="customer-recovery-guide-header"><div>{closed ? <CheckCircle2 size={20}/> : <AlertTriangle size={20}/>}<span><strong>{closed ? '상담이 마무리되었습니다.' : recovery ? '피해 대응 안내를 확인하고 있습니다.' : '피해 대응 안내를 확인해 주세요.'}</strong><small>{closed ? '추가 피해가 의심되면 공식 은행 고객센터로 다시 상담을 요청해 주세요.' : recovery ? '실제 신청·처리 여부는 현재 진행 상황에서 확인하세요.' : '필요한 피해구제 절차를 선택할 수 있습니다.'}</small></span></div>{recovery ? <span className="customer-recovery-active-status">피해 대응 안내 중</span> : !closed && <button type="button" className="customer-emergency-button" disabled={busy} onClick={() => { setDetailsOpen(true); setConfirmRecovery(true); }}>이미 사기 당했어요</button>}</div>
          <details className="customer-recovery-guide-details" open={detailsOpen} onToggle={(event) => setDetailsOpen(event.currentTarget.open)}><summary>피해 대응 안내 <span className="customer-recovery-open-label">열기</span><span className="customer-recovery-close-label">닫기</span><ChevronDown size={15}/></summary><div className="customer-recovery-guide-content"><RecoveryNavigator selected={selectedStep} busy={busy} onSelect={selectRecoveryStep}/></div></details>
        </section>{detailsOpen && <div className="customer-recovery-menu"><div className="customer-recovery-menu-intro"><strong><AlertTriangle size={15} aria-hidden="true"/>보이스피싱 피해 구제 안내</strong><span>피해 발생 시 필요한 대응 단계를 선택해주세요.</span><button type="button" className="customer-recovery-close-button" onClick={() => setDetailsOpen(false)} aria-label="구제 안내 닫기"><ChevronDown size={14}/></button></div><RecoveryNavigator selected={selectedStep} busy={busy} onSelect={selectRecoveryStep}/></div>}<CustomerComposer busy={busy} aiBusy={aiPendingCount > 0} disabled={closed} showEmergency={!closed} emergencyActive={recoveryUiActive} guideOpen={detailsOpen} onEmergency={() => { setDetailsOpen(true); setConfirmRecovery(true); }} onOpenRecoveryGuide={() => setDetailsOpen(true)} onSend={send}/></section> */}

        <section className="customer-chat-panel"><header><div><h1>보이스피싱 대응 AI 상담</h1><p>필요한 내용을 한 가지씩 확인하고 은행 담당자와 연결합니다.</p></div><span>고객 공개 채널</span></header><CustomerConversation bundle={bundle} busy={busy} aiBusy={aiPendingCount > 0} bookmarkedIds={new Set(bookmarks.map((item) => item.entryId))} onAnswer={answer} onRecoveryRequest={requestRecoveryHelp} onToggleBookmark={toggleBookmark} onRetryMessage={retryMessage} onDismissMessage={dismissMessage}/><CustomerComposer busy={busy} aiBusy={aiPendingCount > 0} disabled={closed} onSend={send} draftStorageKey={`csr:composer-draft:${caseId}:customer`}/></section>
        {detailsOpen && <button type="button" className="customer-side-scrim" aria-label="현재 진행 상황 닫기" onClick={() => setDetailsOpen(false)}/>}
        <aside id="customer-side-panel" className={`customer-side-panel ${detailsOpen ? 'is-open' : ''}`}><CustomerProgressPanel key={caseId} bundle={bundle} recovery={recovery} onRequestConfirmation={requestProgressConfirmation}/>{recovery ? <RecoveryNavigator selected={selectedStep} busy={busy} onSelect={selectRecoveryStep}/> : <CustomerSafetyGuide/>}</aside>

      </div>
    </main>
    {confirmRecovery && <div className="dialog-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setConfirmRecovery(false); }}><section className="customer-confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="recovery-confirm-title"><header><AlertTriangle size={21}/><div><h2 id="recovery-confirm-title">이미 사기 피해가 발생했나요?</h2><p>송금 또는 개인정보·인증정보 제공 피해가 있다면 피해구제 모드로 전환합니다.</p></div></header><p>전환 후에는 추가 송금 중단, 증빙 확보, 신고, 피해구제 신청 순서를 안내하며 은행 담당자에게 긴급 신호가 전달됩니다.</p><footer><button type="button" onClick={() => setConfirmRecovery(false)}>취소</button><button type="button" className="danger" disabled={busy} onClick={() => void startRecovery()}>{busy ? '접수 중' : '피해구제 시작'}</button></footer></section></div>}
  </div>;
};
