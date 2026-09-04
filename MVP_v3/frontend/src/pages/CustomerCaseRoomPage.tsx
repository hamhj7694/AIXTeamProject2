import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AlertCircle, AlertTriangle, ArrowLeft, Bookmark, CheckCircle2, Loader2, RefreshCw, ShieldCheck, Wifi, X } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { casesApi, CURRENT_CUSTOMER_USER } from '../api/cases';
import type { CaseBundle, CaseMessage, CustomerQuestion } from '../api/types';
import { readCustomerBookmarks, writeCustomerBookmarks, type CustomerBookmark } from '../customer/bookmarks';
import { CustomerBookmarks } from '../customer/CustomerBookmarks';
import { CustomerComposer } from '../customer/CustomerComposer';
import { CustomerConversation } from '../customer/CustomerConversation';
import { CustomerProgressPanel, CustomerSafetyGuide } from '../customer/CustomerProgressPanel';
import { RecoveryNavigator } from '../customer/RecoveryCards';
import { RECOVERY_MESSAGE_PREFIX, recoveryStepFromMessage, type RecoveryStep, type RecoveryStepId } from '../customer/recovery';
import { mergePendingMessages, removeMessage, upsertMessage } from '../api/messageState';

type CustomerOutboxItem = {
  message: CaseMessage;
  content: string;
  files: File[];
  attachmentIds: string[];
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
  const [bookmarks, setBookmarks] = useState<CustomerBookmark[]>([]);
  const aiQueueRef = useRef<Promise<void>>(Promise.resolve());
  const aiGenerationRef = useRef(0);
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
    setBundle((current) => current ? {
      ...current,
      recent_messages: upsertMessage(current.recent_messages, message),
    } : current);
  };

  const enqueueCustomerAiReply = useCallback((prompt: string, replyToMessageId: string) => {
    const generation = aiGenerationRef.current;
    const targetCaseId = caseId;
    setAiPendingCount((count) => count + 1);
    const run = async () => {
      try {
        // 서버는 이 호출 시점의 고객 공개 대화와 누적 질문 답변을 다시 읽는다.
        const message = await casesApi.invokeCustomerAi(targetCaseId, prompt, replyToMessageId);
        if (aiGenerationRef.current === generation) {
          loadRequestRef.current += 1;
          showMessage(message);
          await load(true);
        }
      } catch (reason) {
        if (aiGenerationRef.current === generation) {
          setNotice(`메시지는 전달됐지만 AI 안내를 만들지 못했습니다. ${reason instanceof Error ? reason.message : '잠시 후 다시 요청해 주세요.'}`);
        }
      } finally {
        if (aiGenerationRef.current === generation) setAiPendingCount((count) => Math.max(0, count - 1));
      }
    };
    // 빠르게 연속 입력해도 AI 응답은 고객 메시지 순서대로 생성한다.
    aiQueueRef.current = aiQueueRef.current.then(run, run);
  }, [caseId, load]);

  useEffect(() => {
    aiGenerationRef.current += 1;
    aiQueueRef.current = Promise.resolve();
    loadRequestRef.current += 1;
    pendingMessagesRef.current.clear();
    outboxRef.current.clear();
    setAiPendingCount(0);
    setBundle(null); setError(''); setNotice(''); setLoading(true); setConfirmRecovery(false);
    setBookmarks(readCustomerBookmarks(caseId));
    void load();
    const heartbeat = () => { void casesApi.heartbeat(caseId, CURRENT_CUSTOMER_USER, 'VIEWING', 'CUSTOMER').catch(() => undefined); };
    heartbeat();
    const timer = window.setInterval(() => void load(true), 4000);
    const presenceTimer = window.setInterval(heartbeat, 30000);
    return () => { window.clearInterval(timer); window.clearInterval(presenceTimer); };
  }, [caseId, load]);

  const refresh = async () => { await load(true); };
  const recovery = String(bundle?.case.mode ?? '') === 'RECOVERY' || String(bundle?.case.victim_transfer_status ?? '') === 'YES';
  const selectedStep = useMemo<RecoveryStepId | null>(() => {
    if (!bundle) return null;
    const messages = [...bundle.recent_messages].reverse();
    return recoveryStepFromMessage(messages.find((message) => recoveryStepFromMessage(message.content))?.content ?? '')?.id ?? null;
  }, [bundle]);
  const closed = String(bundle?.case.status ?? '') === 'CLOSED' || String(bundle?.case.mode ?? '') === 'CLOSED';

  const deliverMessage = async (item: CustomerOutboxItem) => {
    setBusy(true); setError(''); setNotice('');
    const sendingMessage = { ...item.message, delivery_state: 'SENDING' as const, delivery_error: null };
    item.message = sendingMessage;
    pendingMessagesRef.current.set(sendingMessage.client_request_id!, sendingMessage);
    showMessage(sendingMessage);
    try {
      for (const file of item.files.slice(item.attachmentIds.length)) {
        const attachment = await casesApi.uploadCustomerAttachment(caseId, file);
        item.attachmentIds.push(attachment.attachment_id);
      }
      const message = await casesApi.sendCustomerMessage(caseId, item.content, item.attachmentIds, item.message.client_request_id!);
      loadRequestRef.current += 1;
      pendingMessagesRef.current.delete(item.message.client_request_id!);
      outboxRef.current.delete(item.message.client_request_id!);
      showMessage(message);
      if (item.requestAi && item.content) {
        window.requestAnimationFrame(() => enqueueCustomerAiReply(item.content, message.message_id));
      } else {
        window.requestAnimationFrame(() => { void refresh(); });
      }
    } catch (reason) {
      const failed = {
        ...item.message,
        delivery_state: 'FAILED' as const,
        delivery_error: reason instanceof Error ? reason.message : '서버에 전송하지 못했습니다.',
      };
      item.message = failed;
      pendingMessagesRef.current.set(failed.client_request_id!, failed);
      showMessage(failed);
      setError('메시지를 전송하지 못했습니다. 말풍선의 다시 전송을 눌러주세요.');
    } finally { setBusy(false); }
  };
  const send = (content: string, files: File[], requestAi: boolean): Promise<void> => {
    const clientRequestId = crypto.randomUUID();
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
    const item: CustomerOutboxItem = { message, content, files, attachmentIds: [], requestAi };
    pendingMessagesRef.current.set(clientRequestId, message);
    outboxRef.current.set(clientRequestId, item);
    showMessage(message);
    void deliverMessage(item);
    return Promise.resolve();
  };
  const retryMessage = (message: CaseMessage) => {
    if (busy || !message.client_request_id) return;
    const item = outboxRef.current.get(message.client_request_id);
    if (item) void deliverMessage(item);
  };
  const dismissMessage = (message: CaseMessage) => {
    if (!message.client_request_id) return;
    pendingMessagesRef.current.delete(message.client_request_id);
    outboxRef.current.delete(message.client_request_id);
    setBundle((current) => current ? { ...current, recent_messages: removeMessage(current.recent_messages, message) } : current);
  };

  const answer = async (question: CustomerQuestion, rawAnswer: string) => {
    setBusy(true); setError(''); setNotice('');
    try {
      await casesApi.answerCustomerQuestion(caseId, question.question_id, rawAnswer);
      try { await refresh(); } catch { setNotice('답변은 접수됐지만 최신 화면을 갱신하지 못했습니다. 다시 요청하지 말고 새로고침해 주세요.'); }
    } finally { setBusy(false); }
  };

  const startRecovery = async () => {
    if (recovery || busy) return;
    setBusy(true); setError(''); setNotice('');
    try {
      const message = await casesApi.startCustomerEmergency(caseId);
      loadRequestRef.current += 1;
      showMessage(message); setConfirmRecovery(false);
      window.requestAnimationFrame(() => { void refresh(); });
    }
    catch (reason) { setError(reason instanceof Error ? reason.message : '피해구제 요청을 접수하지 못했습니다.'); }
    finally { setBusy(false); }
  };

  const selectRecoveryStep = async (step: RecoveryStep) => {
    const existing = bundle?.recent_messages.find((message) => message.content === `${RECOVERY_MESSAGE_PREFIX} ${step.title}`);
    if (existing) { document.getElementById(`recovery-${existing.message_id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }); return; }
    setBusy(true); setError('');
    try {
      const message = await casesApi.sendCustomerMessage(caseId, `${RECOVERY_MESSAGE_PREFIX} ${step.title}`);
      loadRequestRef.current += 1;
      showMessage(message);
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
        window.requestAnimationFrame(() => enqueueCustomerAiReply(`${step.title} 피해구제 단계에서 제가 지금 해야 할 일을 쉬운 순서로 알려주세요.`, message.message_id));
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
    <header className="customer-header"><Link to="/" aria-label="서비스 홈으로"><ArrowLeft size={17}/>서비스 홈</Link><div><span><ShieldCheck size={18}/></span><b>CSR | Case Share Room</b><small>{caseId} · 고객 안전 상담</small></div><div className="customer-header-actions"><span><Wifi size={13}/>안전하게 연결됨</span><button type="button" onClick={() => setBookmarkOpen(true)}><Bookmark size={16}/>북마크{bookmarks.length > 0 && <b>{bookmarks.length}</b>}</button><button type="button" onClick={() => void load(true)} aria-label="상담 내용 새로고침"><RefreshCw size={16} className={refreshing ? 'spin' : ''}/></button></div></header>
    <main className="customer-main">
      <section className={`customer-safety-banner ${closed ? 'closed' : recovery ? 'recovery' : ''}`}><div>{closed ? <CheckCircle2 size={20}/> : <AlertTriangle size={20}/>}<span><strong>{closed ? '상담이 마무리되었습니다.' : recovery ? '피해구제 절차를 함께 진행하고 있습니다.' : '지금은 송금·인증정보 제공을 멈춰주세요.'}</strong><small>{closed ? '추가 피해가 의심되면 공식 은행 고객센터로 다시 상담을 요청해 주세요.' : recovery ? '추가 송금과 상대방 접촉을 중단하고 아래 절차를 확인하세요.' : '상대방이 알려준 연락처가 아닌 공식 채널로만 확인해 주세요.'}</small></span></div>{!closed && <button type="button" disabled={recovery || busy} onClick={() => setConfirmRecovery(true)}>{recovery ? '피해구제 안내 진행 중' : '이미 사기 당했어요'}</button>}</section>
      {error && <div className="customer-global-message danger"><AlertCircle size={16}/><span>{error}</span><button type="button" onClick={() => setError('')} aria-label="오류 닫기"><X size={15}/></button></div>}
      {notice && <div className="customer-global-message"><AlertCircle size={16}/><span>{notice}</span><button type="button" onClick={() => setNotice('')} aria-label="안내 닫기"><X size={15}/></button></div>}
      <div className="customer-room-grid">
        <section className="customer-chat-panel"><header><div><h1>보이스피싱 대응 AI 상담</h1><p>필요한 내용을 한 가지씩 확인하고 은행 담당자와 연결합니다.</p></div><span>고객 공개 채널</span></header><CustomerConversation bundle={bundle} busy={busy} bookmarkedIds={new Set(bookmarks.map((item) => item.entryId))} onAnswer={answer} onRecoveryRequest={requestRecoveryHelp} onToggleBookmark={toggleBookmark} onRetryMessage={retryMessage} onDismissMessage={dismissMessage}/><CustomerComposer busy={busy} aiBusy={aiPendingCount > 0} disabled={closed} onSend={send}/></section>
        <aside className="customer-side-panel"><CustomerProgressPanel bundle={bundle} recovery={recovery} selectedStep={selectedStep}/>{recovery ? <RecoveryNavigator selected={selectedStep} busy={busy} onSelect={selectRecoveryStep}/> : <CustomerSafetyGuide/>}</aside>
      </div>
    </main>
    <CustomerBookmarks open={bookmarkOpen} items={bookmarks} onClose={() => setBookmarkOpen(false)}/>
    {confirmRecovery && <div className="dialog-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setConfirmRecovery(false); }}><section className="customer-confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="recovery-confirm-title"><header><AlertTriangle size={21}/><div><h2 id="recovery-confirm-title">이미 사기 피해가 발생했나요?</h2><p>송금 또는 개인정보·인증정보 제공 피해가 있다면 피해구제 모드로 전환합니다.</p></div></header><p>전환 후에는 추가 송금 중단, 증빙 확보, 신고, 피해구제 신청 순서를 안내하며 은행 담당자에게 긴급 신호가 전달됩니다.</p><footer><button type="button" onClick={() => setConfirmRecovery(false)}>취소</button><button type="button" className="danger" disabled={busy} onClick={() => void startRecovery()}>{busy ? '접수 중' : '피해구제 시작'}</button></footer></section></div>}
  </div>;
};
