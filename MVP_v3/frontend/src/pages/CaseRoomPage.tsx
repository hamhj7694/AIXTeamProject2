import React, { useCallback, useEffect, useRef, useState } from 'react';
import { AlertCircle, Loader2, PanelRightClose, PanelRightOpen, RefreshCw, Users } from 'lucide-react';
import { useParams } from 'react-router-dom';
import { casesApi, CURRENT_BANK_USER } from '../api/cases';
import type { CaseAction, CaseBundle, CaseFact, CaseMessage, CaseSupportSnapshot, StoredCase, VerificationTask } from '../api/types';
import { ActionDialog, QuestionDialog, VerificationDialog } from '../components/CaseActionDialogs';
import { CaseContextPanel } from '../components/CaseContextPanel';
import { CaseContextLayout } from '../components/CaseContextLayout';
import { ConversationComposer, type ComposerTarget } from '../components/ConversationComposer';
import { SharedConversation } from '../components/SharedConversation';
import { BankBookmarks } from '../components/BankBookmarks';
import { BankPersonalNotes } from '../components/BankPersonalNotes';
import { ParticipantManager } from '../components/ParticipantManager';
import { readBankBookmarks, writeBankBookmarks, type BankBookmark } from '../bank/bookmarks';
import { stripBankAiMention } from '../bank/aiMention';
import { mergePendingMessages, removeMessage, upsertMessage } from '../api/messageState';
import { caseState, caseStateTone, incidentTitle, statusLabel } from '../presentation';

type DialogState = { type: 'questions' } | { type: 'verification'; task?: VerificationTask } | { type: 'action' } | null;
type BankOutboxItem = {
  message: CaseMessage;
  content: string;
  files: File[];
  attachmentIds: string[];
  target: ComposerTarget;
  requestAi: boolean;
};

const caseContextRevision = (caseItem: StoredCase, bundle: CaseBundle, facts: CaseFact[]) => JSON.stringify({
  // AI support에 실제로 전달되는 의미 상태만 지문화한다. 일반 채팅이나
  // presence 갱신만으로 동일한 AI 사건 맥락을 다시 만들지 않는다.
  case: [caseItem.victim_transfer_status, caseItem.mode, caseItem.status, caseItem.diagnosis],
  questions: bundle.questions.map((item) => [item.question_id, item.status, item.answer_text, item.asked_at, item.answered_at]),
  facts: facts.map((item) => [item.fact_id, item.status, item.value, item.confirmed_at]),
  verifications: bundle.verification_tasks.map((item) => [item.verification_task_id, item.version, item.status, item.result_summary, item.updated_at]),
  actions: bundle.recent_actions.map((item) => [item.action_id, item.status, item.note, item.created_at]),
  customer_progress: bundle.customer_progress,
});

type CaseRoomPageProps = {
  onMutated: () => void;
  contextOpen: boolean;
  onContextOpenChange: (open: boolean) => void;
};

export const CaseRoomPage: React.FC<CaseRoomPageProps> = ({ onMutated, contextOpen, onContextOpenChange }) => {
  const { caseId = '' } = useParams();
  const [caseItem, setCaseItem] = useState<StoredCase | null>(null);
  const [bundle, setBundle] = useState<CaseBundle | null>(null);
  const [support, setSupport] = useState<CaseSupportSnapshot | null>(null);
  const [facts, setFacts] = useState<CaseFact[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [partialWarnings, setPartialWarnings] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [aiPendingCount, setAiPendingCount] = useState(0);
  const [checklistBusy, setChecklistBusy] = useState(false);
  const [view, setView] = useState<'conversation' | 'timeline'>('conversation');
  const [dialog, setDialog] = useState<DialogState>(null);
  const [bookmarkOpen, setBookmarkOpen] = useState(false);
  const [noteOpen, setNoteOpen] = useState(false);
  const [participantOpen, setParticipantOpen] = useState(false);
  const [bookmarks, setBookmarks] = useState<BankBookmark[]>([]);
  const lastSupportRevisionRef = useRef('');
  const aiQueueRef = useRef<Promise<void>>(Promise.resolve());
  const aiGenerationRef = useRef(0);
  const loadRequestRef = useRef(0);
  const pendingMessagesRef = useRef(new Map<string, CaseMessage>());
  const outboxRef = useRef(new Map<string, BankOutboxItem>());

  const load = useCallback(async (quiet = false, refreshSupport = !quiet) => {
    if (!caseId) return;
    const requestId = ++loadRequestRef.current;
    const generation = aiGenerationRef.current;
    if (quiet) setRefreshing(true); else setLoading(true);
    const [caseResult, bundleResult, factsResult] = await Promise.allSettled([
      casesApi.get(caseId), casesApi.bundle(caseId), casesApi.facts(caseId),
    ]);
    if (requestId !== loadRequestRef.current || generation !== aiGenerationRef.current) return;
    if (caseResult.status === 'rejected') {
      setError(caseResult.reason instanceof Error ? caseResult.reason.message : 'Case를 불러오지 못했습니다.');
      setLoading(false); setRefreshing(false); return;
    }
    setCaseItem(caseResult.value); if (!quiet) setError('');
    const warnings: string[] = [];
    const nextBundle = bundleResult.status === 'fulfilled' ? {
      ...bundleResult.value,
      recent_messages: mergePendingMessages(bundleResult.value.recent_messages, pendingMessagesRef.current.values()),
    } : null;
    const nextFacts = factsResult.status === 'fulfilled' ? factsResult.value : null;
    if (nextBundle) setBundle(nextBundle); else warnings.push('대화와 업무 기록을 갱신하지 못했습니다.');
    if (nextFacts) setFacts(nextFacts); else warnings.push('확인된 사실을 갱신하지 못했습니다.');
    const nextRevision = nextBundle && nextFacts ? caseContextRevision(caseResult.value, nextBundle, nextFacts) : '';
    const caseContextChanged = Boolean(nextRevision && nextRevision !== lastSupportRevisionRef.current);
    if (refreshSupport || caseContextChanged) {
      try {
        const updatedSupport = await casesApi.support(caseId);
        if (requestId !== loadRequestRef.current || generation !== aiGenerationRef.current) return;
        if (updatedSupport.available) {
          setSupport(updatedSupport);
          if (nextRevision) lastSupportRevisionRef.current = nextRevision;
        } else {
          warnings.push('사건 맥락을 갱신하지 못했습니다. 마지막으로 확인한 내용을 표시합니다.');
        }
      } catch {
        if (requestId !== loadRequestRef.current || generation !== aiGenerationRef.current) return;
        warnings.push('사건 맥락 연결이 끊겼습니다. 마지막으로 확인한 내용을 표시합니다.');
      }
    }
    setPartialWarnings(warnings); setLoading(false); setRefreshing(false);
  }, [caseId]);

  const showMessage = (message: CaseMessage) => {
    setBundle((current) => current ? {
      ...current,
      recent_messages: upsertMessage(current.recent_messages, message),
    } : current);
  };

  const enqueueAiReply = useCallback((prompt?: string, responseStyle: 'CONVERSATIONAL' | 'BRIEF' = 'CONVERSATIONAL') => {
    const generation = aiGenerationRef.current;
    const targetCaseId = caseId;
    setAiPendingCount((count) => count + 1);
    const run = async () => {
      try {
        // TEAM은 고객에게 공개되지 않는 은행 내부 채널이며, 응답도 같은
        // 타임라인에 표시된다. AI는 호출 시점에 DB의 최신 Case를 다시 읽는다.
        const reply = await casesApi.invokeAi(targetCaseId, prompt, 'TEAM', responseStyle);
        if (aiGenerationRef.current === generation) {
          loadRequestRef.current += 1;
          showMessage({
            message_id: reply.message_id,
            case_id: targetCaseId,
            actor_type: 'BANK_AGENT',
            actor_user_id: 'case-copilot',
            actor_display_name: 'CaseCopilot',
            actor_role: 'BANK_AGENT',
            content: reply.content,
            channel: 'TEAM',
            audience: 'BANK_INTERNAL',
            visibility: 'BANK_INTERNAL',
            message_kind: 'AI_RESPONSE',
            private_owner_user_id: null,
            mentions: ['CaseCopilot'],
            reply_to_message_id: null,
            attachments: [],
            created_at: reply.created_at,
          });
          await load(true, false);
        }
      } catch (reason) {
        if (aiGenerationRef.current === generation) {
          setError(reason instanceof Error ? `메시지는 저장됐지만 실제 AI 서버가 응답하지 않았습니다. 임의 답변은 생성하지 않았습니다. ${reason.message}` : '메시지는 저장됐지만 실제 AI 서버가 응답하지 않았습니다. 임의 답변은 생성하지 않았습니다.');
        }
      } finally {
        if (aiGenerationRef.current === generation) setAiPendingCount((count) => Math.max(0, count - 1));
      }
    };
    // 연속 입력은 병렬 호출하지 않고 저장 순서대로 분석해 응답 순서를 지킨다.
    aiQueueRef.current = aiQueueRef.current.then(run, run);
  }, [caseId, load]);

  useEffect(() => {
    aiGenerationRef.current += 1;
    aiQueueRef.current = Promise.resolve();
    loadRequestRef.current += 1;
    pendingMessagesRef.current.clear();
    outboxRef.current.clear();
    setAiPendingCount(0);
    lastSupportRevisionRef.current = '';
    setCaseItem(null); setBundle(null); setSupport(null); setFacts([]); setDialog(null); setBookmarkOpen(false); setNoteOpen(false); setParticipantOpen(false); setBookmarks(readBankBookmarks(caseId)); setError('');
    void load();
    void casesApi.members(caseId).then((items) => items.some((item) => item.user_id === CURRENT_BANK_USER.user_id) ? undefined : casesApi.upsertMember(caseId, { ...CURRENT_BANK_USER, role: 'CHAT_OPERATOR' })).catch(() => undefined);
    const heartbeat = () => { void casesApi.heartbeat(caseId, CURRENT_BANK_USER, 'VIEWING', 'TEAM').catch(() => undefined); };
    heartbeat();
    const timer = window.setInterval(() => { void load(true); }, 5000);
    const presenceTimer = window.setInterval(heartbeat, 30000);
    return () => { window.clearInterval(timer); window.clearInterval(presenceTimer); };
  }, [load]);

  const refreshAfterMutation = async () => { await load(true, false); onMutated(); };
  const deliverMessage = async (item: BankOutboxItem) => {
    setBusy(true); setError('');
    const sendingMessage = { ...item.message, delivery_state: 'SENDING' as const, delivery_error: null };
    item.message = sendingMessage;
    pendingMessagesRef.current.set(sendingMessage.client_request_id!, sendingMessage);
    showMessage(sendingMessage);
    try {
      const visibility = item.target === 'CUSTOMER' ? 'CUSTOMER' : 'BANK_INTERNAL';
      for (const file of item.files.slice(item.attachmentIds.length)) {
        const attachment = await casesApi.uploadAttachment(caseId, file, visibility);
        item.attachmentIds.push(attachment.attachment_id);
      }
      const message = await casesApi.sendMessage(caseId, item.content, item.target, item.attachmentIds, item.message.client_request_id!);
      loadRequestRef.current += 1;
      pendingMessagesRef.current.delete(item.message.client_request_id!);
      outboxRef.current.delete(item.message.client_request_id!);
      showMessage(message);
      onMutated();
      if (item.target === 'TEAM' && item.requestAi && item.content) {
        const requestText = stripBankAiMention(item.content) || '현재 사건에서 가장 시급하게 확인하거나 조치할 사항을 알려주세요.';
        const copilotPrompt = `은행 담당자의 질문: ${requestText}\n\n현재 Shared Case 맥락만 바탕으로, 동료에게 답하듯 자연스럽게 업무를 지원해 주세요. 확인되지 않은 사실은 추정하지 말고, 고객에게 자동 전송하거나 지급정지·신고 등 외부 조치를 완료한 것처럼 표현하지 마세요.`;
        window.requestAnimationFrame(() => enqueueAiReply(copilotPrompt));
      } else {
        window.requestAnimationFrame(() => { void load(true, false); });
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
  const send = (content: string, files: File[], target: ComposerTarget, requestAi: boolean): Promise<void> => {
    const clientRequestId = crypto.randomUUID();
    const visibility = target === 'CUSTOMER' ? 'CUSTOMER' : 'BANK_INTERNAL';
    const message: CaseMessage = {
      message_id: `pending-${clientRequestId}`,
      client_request_id: clientRequestId,
      case_id: caseId,
      actor_type: 'BANK_STAFF',
      actor_user_id: CURRENT_BANK_USER.user_id,
      actor_display_name: CURRENT_BANK_USER.display_name,
      actor_role: CURRENT_BANK_USER.role,
      content,
      channel: target,
      audience: visibility,
      visibility,
      message_kind: 'CHAT',
      private_owner_user_id: null,
      mentions: [],
      reply_to_message_id: null,
      attachments: [],
      created_at: new Date().toISOString(),
      delivery_state: 'SENDING',
      delivery_error: null,
    };
    const item: BankOutboxItem = { message, content, files, attachmentIds: [], target, requestAi };
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
  const invokeAi = async () => {
    if (aiPendingCount > 0) return;
    setError('');
    enqueueAiReply(undefined, 'BRIEF');
  };
  const toggleBookmark = (bookmark: BankBookmark) => {
    const next = bookmarks.some((item) => item.entryId === bookmark.entryId) ? bookmarks.filter((item) => item.entryId !== bookmark.entryId) : [...bookmarks, bookmark];
    setBookmarks(next); writeBankBookmarks(caseId, next);
  };
  const createJudgment = async (note: string) => {
    setChecklistBusy(true); setError('');
    try {
      await casesApi.createAction(caseId, 'STAFF_JUDGMENT', note);
      await refreshAfterMutation();
      return true;
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '담당자 판단을 저장하지 못했습니다.');
      return false;
    } finally { setChecklistBusy(false); }
  };
  const toggleChecklist = async (action: CaseAction, status: 'REQUESTED' | 'COMPLETED') => {
    setChecklistBusy(true); setError('');
    try {
      await casesApi.updateAction(caseId, action.action_id, status);
      await refreshAfterMutation();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '체크리스트 상태를 변경하지 못했습니다.');
    } finally { setChecklistBusy(false); }
  };

  if (loading && !caseItem) return <section className="room-state"><Loader2 className="spin" size={24}/><strong>Shared Case를 불러오고 있습니다.</strong><span>대화와 현재 맥락을 함께 준비합니다.</span></section>;
  if (error && !caseItem) return <section className="room-state error"><AlertCircle size={24}/><strong>정보를 불러오지 못했습니다.</strong><span>{error}</span><button onClick={() => void load()}>다시 시도</button></section>;
  if (!caseItem || !bundle) return <section className="room-state error"><AlertCircle size={24}/><strong>Case 기록을 열 수 없습니다.</strong><span>General API의 Bundle 응답을 확인해 주세요.</span><button onClick={() => void load()}>다시 시도</button></section>;

  return <section className="case-room">
    <header className="case-room-header">
      <div className="case-heading"><span className={`risk-dot ${caseStateTone(caseState(caseItem))}`}/><div><div className="case-title-line"><span>{caseItem.case_id}</span><h1>{incidentTitle(caseItem)}</h1></div><p>{statusLabel(caseItem.status, caseItem.mode)} · 담당자 {caseItem.primary_assignee || '미배정'}</p></div></div>
      <div className="room-header-actions"><button className="participant-open" type="button" onClick={() => setParticipantOpen(true)}><Users size={16}/>참여자 관리</button><button type="button" className="app-context-toggle" onClick={() => onContextOpenChange(!contextOpen)} aria-label={contextOpen ? '사건 맥락 접기' : '사건 맥락 열기'} aria-expanded={contextOpen} aria-controls="case-context-content" title={contextOpen ? '사건 맥락 접기' : '사건 맥락 열기'}>{contextOpen ? <PanelRightClose size={16}/> : <PanelRightOpen size={16}/>}</button><button className="icon-button" onClick={() => void load(true, true)} aria-label="Case와 AI 사건 맥락 새로고침"><RefreshCw size={17} className={refreshing ? 'spin' : ''}/></button><button className="context-open" onClick={() => onContextOpenChange(true)}><PanelRightOpen size={17}/>사건 맥락</button></div>
    </header>
    <CaseContextLayout contextOpen={contextOpen}>
      <main className="conversation-column">
        {partialWarnings.length > 0 && <div className="partial-warning"><AlertCircle size={15}/><span>{partialWarnings.join(' ')}</span></div>}
        <div className="conversation-toolbar"><div><button className={view === 'conversation' ? 'active' : ''} onClick={() => setView('conversation')}>대화</button><button className={view === 'timeline' ? 'active' : ''} onClick={() => setView('timeline')}>전체 기록</button></div><span>{refreshing ? '업데이트 확인 중' : '변경 시 AI 사건 맥락 자동 반영'}</span></div>
        <SharedConversation caseItem={caseItem} bundle={bundle} view={view} bookmarkedIds={new Set(bookmarks.map((item) => item.entryId))} onToggleBookmark={toggleBookmark} onEditVerification={(task) => setDialog({ type: 'verification', task })} onRetryMessage={retryMessage} onDismissMessage={dismissMessage}/>
        {error && <div className="partial-warning danger composer-warning"><AlertCircle size={15}/><span>{error}</span></div>}
        <ConversationComposer busy={busy} aiBusy={aiPendingCount > 0} onSend={send} onOpenQuestions={() => setDialog({ type: 'questions' })} onOpenVerification={() => setDialog({ type: 'verification' })} onOpenAction={() => setDialog({ type: 'action' })} onInvokeAi={() => void invokeAi()} onOpenNotes={() => setNoteOpen(true)} onOpenBookmarks={() => setBookmarkOpen(true)} bookmarkCount={bookmarks.length}/>
      </main>
      <CaseContextPanel caseItem={caseItem} bundle={bundle} facts={facts} support={support} open={contextOpen} onToggle={() => onContextOpenChange(!contextOpen)} onEditVerification={(task) => setDialog({ type: 'verification', task })} onCreateJudgment={createJudgment} onToggleChecklist={toggleChecklist} checklistBusy={checklistBusy} onProgressSaved={(items) => { loadRequestRef.current += 1; setBundle((current) => current ? { ...current, customer_progress: items } : current); void load(true); }}/>
    </CaseContextLayout>
    {dialog?.type === 'questions' && <QuestionDialog caseId={caseId} initial={support?.recommended_questions ?? []} onDone={refreshAfterMutation} onClose={() => setDialog(null)}/>} 
    {dialog?.type === 'verification' && <VerificationDialog caseId={caseId} task={dialog.task} onDone={refreshAfterMutation} onClose={() => setDialog(null)}/>} 
    {dialog?.type === 'action' && <ActionDialog caseId={caseId} recovery={caseItem.mode === 'RECOVERY'} onDone={refreshAfterMutation} onClose={() => setDialog(null)}/>} 
    <BankBookmarks open={bookmarkOpen} items={bookmarks} onClose={() => setBookmarkOpen(false)}/>
    <BankPersonalNotes caseId={caseId} open={noteOpen} onClose={() => setNoteOpen(false)}/>
    <ParticipantManager caseId={caseId} open={participantOpen} onClose={() => setParticipantOpen(false)} onChanged={refreshAfterMutation}/>
  </section>;
};
