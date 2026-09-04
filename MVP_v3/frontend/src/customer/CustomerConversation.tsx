import React, { useEffect, useMemo, useRef } from 'react';
import { BadgeCheck, Bookmark, Bot, CheckCircle2, FileText, ShieldCheck, UserRound } from 'lucide-react';
import { casesApi, CURRENT_CUSTOMER_USER } from '../api/cases';
import type { CaseBundle, CaseMessage, CustomerQuestion, CustomerVerificationResult } from '../api/types';
import { formatClock } from '../presentation';
import type { CustomerBookmark } from './bookmarks';
import { CustomerQuestionCard } from './CustomerQuestionCard';
import { RecoveryDetailCard } from './RecoveryCards';
import type { RecoveryStep } from './recovery';
import { buildCustomerTimeline, type CustomerTimelineEntry } from './timeline';
import { SafeMarkdown } from '../components/SafeMarkdown';

interface Props {
  bundle: CaseBundle;
  busy: boolean;
  bookmarkedIds: Set<string>;
  onAnswer: (question: CustomerQuestion, answer: string) => Promise<void>;
  onRecoveryRequest: (kind: 'AI_ADVICE' | 'HUMAN_HANDOFF', step: RecoveryStep) => Promise<void>;
  onToggleBookmark: (bookmark: CustomerBookmark) => void;
  onRetryMessage: (message: CaseMessage) => void;
  onDismissMessage: (message: CaseMessage) => void;
}

const BookmarkButton: React.FC<{ entry: CustomerTimelineEntry; active: boolean; label: string; summary: string; onToggle: Props['onToggleBookmark'] }> = ({ entry, active, label, summary, onToggle }) => <button type="button" className={`entry-bookmark ${active ? 'active' : ''}`} aria-label={active ? '북마크 해제' : '북마크 추가'} aria-pressed={active} onClick={() => onToggle({ entryId: entry.id, label, summary, createdAt: entry.occurredAt })}><Bookmark size={14} fill={active ? 'currentColor' : 'none'}/></button>;

const MessageEntry: React.FC<{ entry: CustomerTimelineEntry; message: CaseMessage; active: boolean; onToggle: Props['onToggleBookmark']; onRetry: Props['onRetryMessage']; onDismiss: Props['onDismissMessage'] }> = ({ entry, message, active, onToggle, onRetry, onDismiss }) => {
  const mine = message.actor_user_id === CURRENT_CUSTOMER_USER.user_id || message.actor_type === 'CUSTOMER';
  const ai = message.actor_type === 'CUSTOMER_AGENT' || message.message_kind === 'AI_RESPONSE';
  return <article id={entry.id} className={`customer-message-row ${mine ? 'mine' : ''}`}>
    <span className={`customer-avatar ${mine ? 'customer' : ai ? 'ai' : 'bank'}`}>{mine ? <UserRound size={17}/> : ai ? <Bot size={17}/> : <ShieldCheck size={17}/>}</span>
    <div className="customer-message-wrap"><div className="customer-entry-meta"><b>{mine ? '나' : message.actor_display_name || (ai ? '안전 상담 AI' : '은행 담당자')}</b><BookmarkButton entry={entry} active={active} label={mine ? '내 메시지' : ai ? 'AI 안내' : '은행 안내'} summary={message.content || '첨부파일'} onToggle={onToggle}/></div><div className="customer-message-bubble"><SafeMarkdown content={message.content}/>{message.attachments?.length > 0 && <div className="attachment-list">{message.attachments.map((attachment) => <a key={attachment.attachment_id} href={casesApi.customerAttachmentUrl(attachment)} target="_blank" rel="noreferrer"><FileText size={15}/><span>{attachment.original_name}</span><small>{Math.ceil(attachment.size_bytes / 1024)}KB</small></a>)}</div>}</div>{message.delivery_state === 'FAILED' && <div className="message-delivery-error"><span>전송되지 않았습니다.</span><button type="button" onClick={() => onRetry(message)}>다시 전송</button><button type="button" onClick={() => onDismiss(message)}>지우기</button></div>}<time className={message.delivery_state ? message.delivery_state.toLowerCase() : undefined}>{message.delivery_state === 'SENDING' ? '전송 중…' : message.delivery_state === 'FAILED' ? '전송 실패' : formatClock(message.created_at)}</time></div>
  </article>;
};

export const CustomerConversation: React.FC<Props> = ({ bundle, busy, bookmarkedIds, onAnswer, onRecoveryRequest, onToggleBookmark, onRetryMessage, onDismissMessage }) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const initialized = useRef(false);
  const followLatest = useRef(true);
  const entries = useMemo(() => buildCustomerTimeline(bundle), [bundle]);
  const latestEntry = entries[entries.length - 1];
  const latestEntryKey = latestEntry ? `${latestEntry.id}:${latestEntry.occurredAt}` : 'empty';
  const answeredCount = bundle.questions.filter((question) => question.status === 'ANSWERED').length;
  const totalQuestions = bundle.questions.filter((question) => question.status !== 'SKIPPED').length;
  useEffect(() => {
    const node = scrollRef.current;
    if (!node) return;
    if (!initialized.current || followLatest.current) node.scrollTop = node.scrollHeight;
    initialized.current = true;
  }, [latestEntryKey]);

  const renderEntry = (entry: CustomerTimelineEntry) => {
    const active = bookmarkedIds.has(entry.id);
    if (entry.kind === 'MESSAGE') return <MessageEntry key={entry.id} entry={entry} message={entry.data as CaseMessage} active={active} onToggle={onToggleBookmark} onRetry={onRetryMessage} onDismiss={onDismissMessage}/>;
    if (entry.kind === 'QUESTION') {
      const question = entry.data as CustomerQuestion;
      return <div id={entry.id} key={entry.id} className="customer-card-entry" data-active-question="true"><div className="customer-card-bookmark"><BookmarkButton entry={entry} active={active} label="확인 질문" summary={question.question_text} onToggle={onToggleBookmark}/></div><div id="active-customer-question"><CustomerQuestionCard question={question} position={answeredCount + 1} total={totalQuestions} busy={busy} onAnswer={(answer) => onAnswer(question, answer)}/></div><time>{formatClock(entry.occurredAt)}</time></div>;
    }
    if (entry.kind === 'ANSWER') {
      const question = entry.data as CustomerQuestion;
      return <article id={entry.id} key={entry.id} className="customer-card-entry customer-answer-card"><div className="customer-card-bookmark"><BookmarkButton entry={entry} active={active} label="접수된 답변" summary={`${question.question_text} — ${question.answer_text}`} onToggle={onToggleBookmark}/></div><div className="customer-card-kicker success"><CheckCircle2 size={16}/><span>답변이 안전하게 접수되었습니다.</span></div><h3>{question.question_text}</h3><p>{question.answer_text}</p><small>은행 담당자가 확인할 정보 후보로 전달되었습니다. 아직 최종 확정된 사실은 아닙니다.</small><time>{formatClock(entry.occurredAt)}</time></article>;
    }
    if (entry.kind === 'VERIFICATION') {
      const result = entry.data as CustomerVerificationResult;
      return <article id={entry.id} key={entry.id} className="customer-card-entry customer-verification-card"><div className="customer-card-bookmark"><BookmarkButton entry={entry} active={active} label="공식 확인 결과" summary={`${result.target} — ${result.result_summary}`} onToggle={onToggleBookmark}/></div><div className="customer-card-kicker"><BadgeCheck size={16}/><span>공식 확인 결과</span></div><h3>{result.target}</h3><p>{result.result_summary}</p><small>은행 담당자가 고객 공개를 승인한 내용입니다.</small><time>{formatClock(entry.occurredAt)}</time></article>;
    }
    const value = entry.data as { message: CaseMessage; step: RecoveryStep };
    return <div id={entry.id} key={entry.id} className="customer-card-entry recovery-entry" data-recovery-step={value.step.id}><div className="customer-card-bookmark"><BookmarkButton entry={entry} active={active} label={`피해구제 · ${value.step.title}`} summary={value.step.summary} onToggle={onToggleBookmark}/></div><RecoveryDetailCard step={value.step} busy={busy} onRequest={onRecoveryRequest}/><time>{formatClock(entry.occurredAt)}</time></div>;
  };

  return <div ref={scrollRef} className="customer-conversation-scroll" aria-live="polite" onScroll={(event) => { const node = event.currentTarget; followLatest.current = node.scrollHeight - node.scrollTop - node.clientHeight < 96; }}>
    {entries.length > 0 ? entries.map(renderEntry) : <div className="customer-conversation-empty"><Bot size={25}/><strong>아직 상담 대화가 없습니다.</strong><span>현재 상황을 알려주시면 필요한 내용을 차례로 확인합니다.</span></div>}
  </div>;
};
