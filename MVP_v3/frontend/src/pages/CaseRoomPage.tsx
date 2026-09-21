import React, { useCallback, useEffect, useRef, useState } from 'react';
import { AlertCircle, Bookmark, CheckCircle2, FileSearch, Loader2, RefreshCw, RotateCcw, StickyNote, Trash2, Users, X } from 'lucide-react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { casesApi, CURRENT_BANK_USER } from '../api/cases';
import type { AnalyzeCaseResponse, CaseBundle, CaseFact, CaseMessage, CaseSupportSnapshot, StoredCase, VerificationTask } from '../api/types';
import { ActionDialog, QuestionDialog, VerificationDialog } from '../components/CaseActionDialogs';
import { AdminCaseDialog } from '../components/AdminCaseDialog';
import { ContextPanelFoundation } from '../context-v3/ContextPanelFoundation';
import { MoreMenu } from '../context-v3/components';
import { CaseContextLayout } from '../components/CaseContextLayout';
import { ConversationComposer, type ComposerTarget } from '../components/ConversationComposer';
import { SharedConversation } from '../components/SharedConversation';
import { BankBookmarks } from '../components/BankBookmarks';
import { BankPersonalNotes } from '../components/BankPersonalNotes';
import { CaseAssignmentDialog } from '../components/CaseAssignmentDialog';
import { readBankBookmarks, writeBankBookmarks, type BankBookmark } from '../bank/bookmarks';
import { stripBankAiMention } from '../bank/aiMention';
import { buildConsecutiveAiPrompt, ConsecutiveAiBatcher } from '../bank/consecutiveAiBatch';
import { generateUuid } from '../uuid';
import { mergePendingMessages, removeMessage, upsertMessage } from '../api/messageState';
import { caseState, caseStateTone, incidentTitle, statusLabel } from '../presentation';
import { BankCardKind } from '../components/cards/BankCardMenu';
import BankTransactionCard from '../components/cards/BankTransactionCard';
import FdsResultCard from '../components/cards/FdsResultCard';
import AdditionalLookupCard from '../components/cards/AdditionalLookupCard';
import { mockAdditionalLookup, mockBankTransaction, mockFdsResult } from '../mocks/cardMocks';
import { hasInitialAssignmentHandled, hasInitialAssignmentPending, markInitialAssignmentHandled, shouldOpenInitialAssignment } from '../assignmentPromptState';
import { AnalysisResult } from './HomePage';

type DialogState = { type: 'questions' } | { type: 'verification'; task?: VerificationTask } | { type: 'action' } | null;
type AdminAction = 'finalize' | 'reopen' | 'trash' | null;
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
  context_revision: bundle.case.context_revision,
});

type CaseRoomPageProps = {
  caseName?: string | null;
  onMutated: () => void;
  contextOpen: boolean;
  onContextOpenChange: (open: boolean) => void;
};

export const CaseRoomPage: React.FC<CaseRoomPageProps> = ({ caseName, onMutated, contextOpen, onContextOpenChange }) => {
  const { caseId = '' } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const initialAssignmentRecommendation = Boolean((location.state as { initialAssignmentRecommendation?: boolean } | null)?.initialAssignmentRecommendation);
  const [caseItem, setCaseItem] = useState<StoredCase | null>(null);
  const [bundle, setBundle] = useState<CaseBundle | null>(null);
  const [support, setSupport] = useState<CaseSupportSnapshot | null>(null);
  const [facts, setFacts] = useState<CaseFact[]>([]);
  const [selectedBankCard, setSelectedBankCard] = useState<BankCardKind | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [partialWarnings, setPartialWarnings] = useState<string[]>([]);
  const [composerWarnings, setComposerWarnings] = useState<Partial<Record<ComposerTarget, string>>>({});
  const [busy, setBusy] = useState(false);
  const [aiPendingCount, setAiPendingCount] = useState(0);
  const [dialog, setDialog] = useState<DialogState>(null);
  const [bookmarkOpen, setBookmarkOpen] = useState(false);
  const [noteOpen, setNoteOpen] = useState(false);
  const [participantOpen, setParticipantOpen] = useState(false);
  const [participantCount, setParticipantCount] = useState(0);
  const [assignmentRequired, setAssignmentRequired] = useState(false);
  const [analysisResultOpen, setAnalysisResultOpen] = useState(false);
  const [adminAction, setAdminAction] = useState<AdminAction>(null);
  const [accessRevision, setAccessRevision] = useState(0);
  const [bookmarks, setBookmarks] = useState<BankBookmark[]>([]);
  const [customerPaneCollapsed, setCustomerPaneCollapsed] = useState(false);
  const [teamPaneCollapsed, setTeamPaneCollapsed] = useState(false);
  const [customerPaneRatio, setCustomerPaneRatio] = useState(50);
  const [splitDragging, setSplitDragging] = useState(false);
  const lastSupportRevisionRef = useRef('');
  const aiQueueRef = useRef<Promise<void>>(Promise.resolve());
  const aiBatcherRef = useRef<ConsecutiveAiBatcher | null>(null);
  const enqueueAiReplyRef = useRef<(prompt?: string, responseStyle?: 'CONVERSATIONAL' | 'BRIEF') => Promise<void>>(async () => undefined);
  const aiGenerationRef = useRef(0);
  const activeCaseIdRef = useRef(caseId);
  activeCaseIdRef.current = caseId;
  const loadRequestRef = useRef(0);
  const pendingMessagesRef = useRef(new Map<string, CaseMessage>());
  const outboxRef = useRef(new Map<string, BankOutboxItem>());
  const splitRef = useRef<HTMLDivElement>(null);
  const handleComposerError = useCallback((target: ComposerTarget, message: string) => {
    setComposerWarnings((current) => {
      if (!message) {
        const next = { ...current };
        delete next[target];
        return next;
      }
      return { ...current, [target]: message };
    });
  }, []);
  useEffect(() => {
    if (!splitDragging) return undefined;
    const handlePointerMove = (event: PointerEvent) => {
      const node = splitRef.current;
      if (!node || customerPaneCollapsed || teamPaneCollapsed) return;
      const bounds = node.getBoundingClientRect();
      const ratio = ((event.clientX - bounds.left) / bounds.width) * 100;
      setCustomerPaneRatio(Math.min(75, Math.max(25, ratio)));
    };
    const stopDragging = () => setSplitDragging(false);
    window.addEventListener('pointermove', handlePointerMove);
    window.addEventListener('pointerup', stopDragging);
    document.body.classList.add('is-resizing-conversations');
    return () => {
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', stopDragging);
      document.body.classList.remove('is-resizing-conversations');
    };
  }, [splitDragging, customerPaneCollapsed, teamPaneCollapsed]);

  useEffect(() => {
    if (caseName === undefined) return;
    setCaseItem((current) => current && current.case_id === caseId ? { ...current, case_name: caseName } : current);
  }, [caseId, caseName]);

  const load = useCallback(async (quiet = false, refreshSupport = !quiet) => {
    if (!caseId) return;
    const requestId = ++loadRequestRef.current;
    const generation = aiGenerationRef.current;
    if (quiet) setRefreshing(true); else setLoading(true);
    const [caseResult, bundleResult, factsResult, membersResult] = await Promise.allSettled([
      casesApi.get(caseId), casesApi.bundle(caseId), casesApi.facts(caseId), casesApi.members(caseId),
    ]);
    if (requestId !== loadRequestRef.current || generation !== aiGenerationRef.current) return;
    if (caseResult.status === 'rejected') {
      setError(caseResult.reason instanceof Error ? caseResult.reason.message : 'Case를 불러오지 못했습니다.');
      setLoading(false); setRefreshing(false); return;
    }
    setCaseItem(caseResult.value); if (!quiet) setError('');
    if (membersResult.status === 'fulfilled') setParticipantCount(membersResult.value.length);
    const assignmentPending = hasInitialAssignmentPending(caseId);
    const assignmentHandled = hasInitialAssignmentHandled(caseId);
    if (caseResult.value.primary_assignee) {
      // A save may have happened in another tab before this Case finished loading.
      markInitialAssignmentHandled(caseId);
      if (!quiet) setAssignmentRequired(false);
    } else if (!quiet && shouldOpenInitialAssignment({ hasPending: assignmentPending, hasHandled: assignmentHandled, hasPrimaryAssignee: false, routeHint: initialAssignmentRecommendation })) {
      // Do not mark the prompt as handled here. A failed load or failed save must
      // leave the one-time prompt available for the next retry.
      setAssignmentRequired(true);
    }
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
  }, [caseId, initialAssignmentRecommendation]);

  const showMessage = (message: CaseMessage) => {
    setBundle((current) => current && current.case.case_id === message.case_id ? {
      ...current,
      recent_messages: upsertMessage(current.recent_messages, message),
    } : current);
  };

  const enqueueAiReply = useCallback((prompt?: string, responseStyle: 'CONVERSATIONAL' | 'BRIEF' = 'CONVERSATIONAL') => {
    const generation = aiGenerationRef.current;
    const targetCaseId = caseId;
    setAiPendingCount((count) => count + 1);
    let pendingReleased = false;
    const releasePending = () => {
      if (pendingReleased) return;
      pendingReleased = true;
      setAiPendingCount((count) => Math.max(0, count - 1));
    };
    const run = async () => {
      if (aiGenerationRef.current !== generation || activeCaseIdRef.current !== targetCaseId) return;
      try {
        // TEAM은 고객에게 공개되지 않는 은행 내부 채널이며, 응답도 같은
        // 타임라인에 표시된다. AI는 호출 시점에 DB의 최신 Case를 다시 읽는다.
        const reply = await casesApi.invokeAi(targetCaseId, prompt, 'TEAM', responseStyle);
        if (aiGenerationRef.current === generation) {
          // Remove the thinking bubble before adding the completed answer so
          // the two states are never rendered together.
          releasePending();
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
        if (aiGenerationRef.current === generation) releasePending();
      }
    };
    // 연속 입력은 병렬 호출하지 않고 저장 순서대로 분석해 응답 순서를 지킨다.
    const queued = aiQueueRef.current.then(run, run);
    aiQueueRef.current = queued;
    return queued;
  }, [caseId, load]);
  enqueueAiReplyRef.current = enqueueAiReply;

  useEffect(() => {
    aiBatcherRef.current?.dispose();
    aiBatcherRef.current = new ConsecutiveAiBatcher(async (messages) => {
      await enqueueAiReplyRef.current(buildConsecutiveAiPrompt(messages));
    });
    aiGenerationRef.current += 1;
    aiQueueRef.current = Promise.resolve();
    loadRequestRef.current += 1;
    pendingMessagesRef.current.clear();
    outboxRef.current.clear();
    setAiPendingCount(0); setBusy(false);
    lastSupportRevisionRef.current = '';
    setCaseItem(null); setBundle(null); setSupport(null); setFacts([]); setDialog(null); setBookmarkOpen(false); setNoteOpen(false); setParticipantOpen(false); setParticipantCount(0); setAssignmentRequired(false); setAnalysisResultOpen(false); setAdminAction(null); setBookmarks(readBankBookmarks(caseId)); setError(''); setComposerWarnings({}); setCustomerPaneCollapsed(false); setTeamPaneCollapsed(false); setCustomerPaneRatio(50);
    // Register the existing demo identity before mounting editors that require membership.
    let active = true;
    void (async () => {
      try {
        const items = await casesApi.members(caseId);
        if (active) setParticipantCount(items.length);
        if (!items.some((item) => item.user_id === CURRENT_BANK_USER.user_id)) {
          await casesApi.upsertMember(caseId, { user_id: CURRENT_BANK_USER.user_id, display_name: CURRENT_BANK_USER.display_name, assignment_role: 'HANDOVER_PENDING' });
          const updatedItems = await casesApi.members(caseId);
          if (active) setParticipantCount(updatedItems.length);
        }
      } catch {
        if (active) setError('사건 참여 정보를 확인하지 못했습니다. 참여자 관리에서 다시 확인해 주세요.');
      }
      if (active) { setAccessRevision((value) => value + 1); await load(); }
    })();
    const heartbeat = () => { void casesApi.heartbeat(caseId, CURRENT_BANK_USER, 'VIEWING', 'TEAM').catch(() => undefined); };
    heartbeat();
    const timer = window.setInterval(() => { void load(true); }, 5000);
    const presenceTimer = window.setInterval(heartbeat, 30000);
    return () => { active = false; aiBatcherRef.current?.dispose(); aiBatcherRef.current = null; aiGenerationRef.current += 1; loadRequestRef.current += 1; window.clearInterval(timer); window.clearInterval(presenceTimer); };
  }, [load]);

  const refreshAfterMutation = async () => { await load(true, false); onMutated(); };
  const deliverMessage = async (item: BankOutboxItem) => {
    const generation = aiGenerationRef.current;
    const isCurrent = () => generation === aiGenerationRef.current && activeCaseIdRef.current === item.message.case_id;
    if (!isCurrent()) return false;
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
      if (!isCurrent()) return false;
      loadRequestRef.current += 1;
      pendingMessagesRef.current.delete(item.message.client_request_id!);
      outboxRef.current.delete(item.message.client_request_id!);
      showMessage(message);
      onMutated();
      if (!(item.target === 'TEAM' && item.requestAi && item.content)) {
        window.requestAnimationFrame(() => { if (isCurrent()) void load(true, false); });
      }
      return true;
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
      return false;
    } finally { if (isCurrent()) setBusy(false); }
  };
  const queueBatchedAi = (item: BankOutboxItem, saved: Promise<boolean>) => {
    if (item.target !== 'TEAM' || !item.requestAi || !item.content) return;
    aiBatcherRef.current?.enqueue({
      caseId: item.message.case_id,
      requesterUserId: CURRENT_BANK_USER.user_id,
      messageId: item.message.client_request_id!,
      content: stripBankAiMention(item.content) || '현재 사건에서 가장 시급하게 확인하거나 조치할 사항을 알려주세요.',
      saved,
    });
  };
  const send = (content: string, files: File[], target: ComposerTarget, requestAi: boolean): Promise<void> => {
    const clientRequestId = generateUuid();
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
    const saved = deliverMessage(item);
    queueBatchedAi(item, saved);
    void saved;
    return Promise.resolve();
  };
  const retryMessage = (message: CaseMessage) => {
    if (busy || !message.client_request_id) return;
    const item = outboxRef.current.get(message.client_request_id);
    if (item) {
      const saved = deliverMessage(item);
      queueBatchedAi(item, saved);
      void saved;
    }
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
  const updateBookmark = (bookmark: BankBookmark) => { const next = bookmarks.map((item) => item.entryId === bookmark.entryId ? bookmark : item); setBookmarks(next); writeBankBookmarks(caseId, next); };
  const deleteBookmark = (entryId: string) => { const next = bookmarks.filter((item) => item.entryId !== entryId); setBookmarks(next); writeBankBookmarks(caseId, next); };
  const finalizeCase = async (password: string, note: string) => {
    if (!caseItem) return;
    await casesApi.finalize(caseId, caseItem.version, password, note);
    await load(true, false);
    onMutated();
  };
  const reopenCase = async (password: string) => {
    if (!caseItem) return;
    await casesApi.reopen(caseId, caseItem.version, password);
    await load(true, false);
    onMutated();
  };
  const trashCase = async (password: string) => {
    await casesApi.trash(caseId, password);
    onMutated();
    navigate('/', { replace: true });
  };
  const composerWarningMessages = Object.values(composerWarnings).filter(Boolean);
  const toggleCustomerPane = () => {
    if (teamPaneCollapsed) {
      setTeamPaneCollapsed(false);
      setCustomerPaneRatio(50);
      return;
    }
    setCustomerPaneCollapsed((current) => !current);
  };
  const toggleTeamPane = () => {
    if (customerPaneCollapsed) {
      setCustomerPaneCollapsed(false);
      setCustomerPaneRatio(50);
      return;
    }
    setTeamPaneCollapsed((current) => !current);
  };
  const conversationGridStyle = customerPaneCollapsed
    ? { gridTemplateColumns: 'var(--conversation-collapsed-width) 4px minmax(0, 1fr)' }
    : teamPaneCollapsed
      ? { gridTemplateColumns: 'minmax(0, 1fr) 4px var(--conversation-collapsed-width)' }
      : { gridTemplateColumns: `minmax(0, ${customerPaneRatio}fr) 4px minmax(0, ${100 - customerPaneRatio}fr)` };
  const analysisResult: AnalyzeCaseResponse = caseItem ? {
    schema_version: 'analysis.v1',
    disposition: 'CASE_CREATED',
    case_id: caseItem.case_id,
    risk: caseItem.risk,
    mode: caseItem.mode === 'RECOVERY' ? 'RECOVERY' : 'PREVENT',
    status: caseItem.status,
    initial_brief: caseItem.initial_brief,
    initial_report: caseItem.initial_report ? {
      report_id: caseItem.initial_report.report_id,
      case_id: caseItem.initial_report.case_id,
      report_version: caseItem.initial_report.report_version,
    } : null,
  } : {
    schema_version: 'analysis.v1', disposition: 'CASE_CREATED', case_id: caseId,
  };
  if (loading && !caseItem) return <section className="room-state"><Loader2 className="spin" size={24}/><strong>Shared Case를 불러오고 있습니다.</strong><span>대화와 현재 맥락을 함께 준비합니다.</span></section>;
  if (error && !caseItem) return <section className="room-state error"><AlertCircle size={24}/><strong>정보를 불러오지 못했습니다.</strong><span>{error}</span><button onClick={() => void load()}>다시 시도</button></section>;
  if (!caseItem || !bundle) return <section className="room-state error"><AlertCircle size={24}/><strong>Case 기록을 열 수 없습니다.</strong><span>General API의 Bundle 응답을 확인해 주세요.</span><button onClick={() => void load()}>다시 시도</button></section>;

  const transferStatus = caseItem.victim_transfer_status === 'YES'
    ? '이체 완료'
    : caseItem.victim_transfer_status === 'NO'
      ? '미이체'
      : caseItem.victim_transfer_status === 'UNKNOWN'
        ? '확인 필요'
        : '정보 없음';
  const transactionCardData = {
    ...mockBankTransaction,
    transferAmount: typeof caseItem.actual_loss_amount_krw === 'number' ? caseItem.actual_loss_amount_krw : null,
    transactionStatus: transferStatus,
    updatedAt: caseItem.updated_at || '',
  };
  const supportBrief = support?.case_brief;
  const fdsReasons = support?.case_context?.key_signals?.filter((item) => item.trim()) ?? [];
  const fdsCardData = {
    ...mockFdsResult,
    riskScore: typeof supportBrief?.risk_score === 'number' ? supportBrief.risk_score : mockFdsResult.riskScore,
    riskLevel: supportBrief?.risk_level || mockFdsResult.riskLevel,
    updatedAt: caseItem.updated_at || mockFdsResult.updatedAt,
    ...(fdsReasons.length > 0 ? { reasons: fdsReasons } : {}),
  };
  const additionalLookupData = { ...mockAdditionalLookup, updatedAt: caseItem.updated_at || mockAdditionalLookup.updatedAt };
  const bankCard = selectedBankCard === 'transaction' ? <BankTransactionCard {...transactionCardData} /> : selectedBankCard === 'fds' ? <FdsResultCard {...fdsCardData} /> : selectedBankCard === 'additionalLookup' ? <AdditionalLookupCard {...additionalLookupData} onViewAll={() => undefined} /> : undefined;

  return <section className="case-room">
    <header className="case-room-header case-command-header">
      <div className="case-heading"><span className={`risk-dot ${caseStateTone(caseState(caseItem))}`}/><div><div className="case-title-line"><span>{caseItem.case_id}</span><h1>{incidentTitle(caseItem)}</h1></div><div className="case-header-meta"><span>{statusLabel(caseItem.status, caseItem.mode)}</span><span>주 담당자 {caseItem.primary_assignee || '미배정'}</span></div></div></div>
      <div className="room-header-actions"><button className="participant-open" type="button" onClick={() => setParticipantOpen(true)}><Users size={16}/>참여자 <b>{participantCount}</b></button><button type="button" className="header-tool-action header-tool-analysis" onClick={() => setAnalysisResultOpen(true)}><FileSearch size={15}/>초기 분석 결과 보기</button><button type="button" className="header-tool-action header-tool-note" onClick={() => setNoteOpen(true)}><StickyNote size={15}/>개인 메모</button><button type="button" className="header-tool-action header-tool-bookmark" onClick={() => setBookmarkOpen(true)}><Bookmark size={15}/>북마크{bookmarks.length > 0 && <b>{bookmarks.length}</b>}</button><button className="icon-button" onClick={() => void load(true, true)} aria-label="Case와 AI 사건 맥락 새로고침"><RefreshCw size={17} className={refreshing ? 'spin' : ''}/></button><MoreMenu label="Case 관리 메뉴"><>{caseItem.mode === 'CLOSED' ? <button onClick={() => setAdminAction('reopen')}><RotateCcw size={14}/>사건 다시 진행</button> : <button onClick={() => setAdminAction('finalize')}><CheckCircle2 size={14}/>해결 및 종료</button>}<button className="danger" onClick={() => setAdminAction('trash')}><Trash2 size={14}/>휴지통으로 이동</button></></MoreMenu></div>
    </header>
    <CaseContextLayout contextOpen={contextOpen}>
      <main className="conversation-column">
        {(partialWarnings.length > 0 || Boolean(error) || composerWarningMessages.length > 0) && <div className="conversation-top-warnings">
          {partialWarnings.map((message) => <div className="partial-warning" key={message}><AlertCircle size={15}/><span>{message}</span></div>)}
          {error && <div className="partial-warning danger"><AlertCircle size={15}/><span>{error}</span></div>}
          {composerWarningMessages.map((message) => <div className="partial-warning danger" key={message}><AlertCircle size={15}/><span>{message}</span></div>)}
        </div>}
        <div ref={splitRef} className={`conversation-channel-grid ${splitDragging ? 'is-resizing' : ''}`} style={conversationGridStyle}>
          <SharedConversation bundle={bundle} view="conversation" channel="CUSTOMER" aiBusy={false} inlineCard={dialog?.type === 'questions' ? <QuestionDialog inline caseId={caseId} initial={support?.recommended_questions ?? []} onDone={refreshAfterMutation} onClose={() => setDialog(null)}/> : undefined} collapsed={customerPaneCollapsed} collapseDisabled={false} onToggleCollapse={toggleCustomerPane} onOpenQuestions={() => setDialog({ type: 'questions' })} composer={<ConversationComposer foundationMode fixedTarget="CUSTOMER" showAi={false} showUtilities={false} showQuestionAction onOpenQuestions={() => setDialog({ type: 'questions' })} showInlineError={false} onErrorChange={(message) => handleComposerError('CUSTOMER', message)} busy={busy} aiBusy={false} onSend={send} onOpenVerification={() => undefined} onOpenAction={() => undefined} onInvokeAi={() => undefined} onOpenNotes={() => undefined} onOpenBookmarks={() => undefined} bookmarkCount={0}/>} bookmarkedIds={new Set(bookmarks.map((item) => item.entryId))} onToggleBookmark={toggleBookmark} onRetryMessage={retryMessage} onDismissMessage={dismissMessage}/>
          <button type="button" className="conversation-split-handle" onPointerDown={(event) => { if (customerPaneCollapsed || teamPaneCollapsed) return; event.preventDefault(); setSplitDragging(true); }} onDoubleClick={() => { if (!customerPaneCollapsed && !teamPaneCollapsed) setCustomerPaneRatio(50); }} onKeyDown={(event) => { if (event.key === 'Home') { event.preventDefault(); setCustomerPaneRatio(50); return; } if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return; event.preventDefault(); setCustomerPaneRatio((value) => Math.min(75, Math.max(25, value + (event.key === 'ArrowLeft' ? -5 : 5)))); }} aria-label="고객 소통과 은행 내부 소통 채팅창 너비 조절, 더블클릭하면 1대1로 맞춤" title="드래그하여 폭 조절 · 더블클릭하여 1:1 맞춤" aria-valuemin={25} aria-valuemax={75} aria-valuenow={Math.round(customerPaneRatio)} role="separator"><span/></button>
          <SharedConversation bundle={bundle} view="conversation" channel="TEAM" aiBusy={aiPendingCount > 0} inlineCard={bankCard} collapsed={teamPaneCollapsed} collapseDisabled={false} onToggleCollapse={toggleTeamPane} composer={<ConversationComposer foundationMode fixedTarget="TEAM" showAi showUtilities={false} showInlineError={false} selectedBankCard={selectedBankCard} onSelectBankCard={setSelectedBankCard} onErrorChange={(message) => handleComposerError('TEAM', message)} busy={busy} aiBusy={aiPendingCount > 0} onSend={send} onOpenQuestions={() => undefined} onOpenVerification={() => undefined} onOpenAction={() => undefined} onInvokeAi={() => void invokeAi()} onOpenNotes={() => setNoteOpen(true)} onOpenBookmarks={() => setBookmarkOpen(true)} bookmarkCount={bookmarks.length}/>} bookmarkedIds={new Set(bookmarks.map((item) => item.entryId))} onToggleBookmark={toggleBookmark} onRetryMessage={retryMessage} onDismissMessage={dismissMessage}/>
        </div>
      </main>
      <ContextPanelFoundation open={contextOpen} onToggle={() => onContextOpenChange(!contextOpen)}/>
    </CaseContextLayout>
    {dialog?.type === 'verification' && <VerificationDialog caseId={caseId} task={dialog.task} onDone={refreshAfterMutation} onClose={() => setDialog(null)}/>} 
    {dialog?.type === 'action' && <ActionDialog caseId={caseId} recovery={caseItem.mode === 'RECOVERY'} onDone={refreshAfterMutation} onClose={() => setDialog(null)}/>} 
    <BankBookmarks open={bookmarkOpen} items={bookmarks} onClose={() => setBookmarkOpen(false)} onUpdate={updateBookmark} onDelete={deleteBookmark}/>
    <BankPersonalNotes caseId={caseId} open={noteOpen} onClose={() => setNoteOpen(false)}/>
    {participantOpen && <CaseAssignmentDialog caseId={caseId} mode="edit" onClose={() => setParticipantOpen(false)} onSaved={async () => { setParticipantOpen(false); setAccessRevision((value) => value + 1); const members = await casesApi.members(caseId); setParticipantCount(members.length); await refreshAfterMutation(); }}/>}
    {analysisResultOpen && <div className="case-analysis-result-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setAnalysisResultOpen(false); }}><section className="case-analysis-result-dialog" role="dialog" aria-modal="true" aria-labelledby="case-analysis-result-title"><header><div><p className="eyebrow">ANALYSIS RESULT</p><h2 id="case-analysis-result-title">초기 분석 결과</h2><small>Case 생성 당시의 구조화 분석 결과를 다시 확인합니다.</small></div><button type="button" className="icon-button" onClick={() => setAnalysisResultOpen(false)} aria-label="초기 분석 결과 닫기"><X size={18}/></button></header><AnalysisResult result={analysisResult} caseItem={caseItem} sourceText="" onOpenCase={() => setAnalysisResultOpen(false)} onRestart={() => setAnalysisResultOpen(false)} showActions={false}/></section></div>}
    {adminAction === 'finalize' && <AdminCaseDialog title="해결 및 종료 처리" description="사건을 해결 상태로 종결합니다. 관리자 암호를 입력해 주세요." confirmLabel="해결 및 종료" noteLabel="종결 메모 (선택)" notePlaceholder="처리 결과나 인계 사항을 기록하세요." onConfirm={finalizeCase} onClose={() => setAdminAction(null)}/>}
    {adminAction === 'reopen' && <AdminCaseDialog title="사건 다시 진행하기" description="종결 직전의 사건 상태로 복구합니다. 관리자 암호를 입력해 주세요." confirmLabel="진행 상태로 복구" onConfirm={(password) => reopenCase(password)} onClose={() => setAdminAction(null)}/>}
    {adminAction === 'trash' && <AdminCaseDialog title="휴지통으로 보내기" description="사건은 휴지통에서 30일 동안 보관되며 그 안에는 복구할 수 있습니다." confirmLabel="휴지통으로 보내기" onConfirm={(password) => trashCase(password)} onClose={() => setAdminAction(null)}/>}
    {assignmentRequired && <CaseAssignmentDialog caseId={caseId} initialRecommendation={true} onAssigned={async () => { markInitialAssignmentHandled(caseId); setAssignmentRequired(false); await load(true, false); onMutated(); }}/>} 
  </section>;
};
