import React, { useEffect, useMemo, useRef } from 'react';
import { Bookmark, Bot, CheckCircle2, CircleDot, FileText, Landmark, MessageCircleQuestion, ShieldCheck, UserRound } from 'lucide-react';
import { casesApi, CURRENT_BANK_USER } from '../api/cases';
import type { CaseAction, CaseEvent, CaseMessage, CustomerQuestion, StoredCase, VerificationTask } from '../api/types';
import { actionLabel, formatClock, verificationStatusLabel } from '../presentation';
import { buildTimeline, type TimelineEntry } from '../timeline';
import type { CaseBundle } from '../api/types';
import type { BankBookmark } from '../bank/bookmarks';
import { SafeMarkdown } from './SafeMarkdown';

interface Props {
  caseItem: StoredCase;
  bundle: CaseBundle;
  view: 'conversation' | 'timeline';
  onEditVerification: (task: VerificationTask) => void;
  bookmarkedIds: Set<string>;
  onToggleBookmark: (bookmark: BankBookmark) => void;
  onRetryMessage: (message: CaseMessage) => void;
  onDismissMessage: (message: CaseMessage) => void;
}

const bookmarkDetails = (entry: TimelineEntry): Pick<BankBookmark, 'label' | 'summary'> => {
  if (entry.kind === 'BRIEF') return { label: 'AI 사건 정리', summary: (entry.data as StoredCase).initial_brief };
  if (entry.kind === 'MESSAGE') {
    const message = entry.data as CaseMessage;
    return { label: message.channel === 'CUSTOMER' ? '고객 대화' : '은행 내부 대화', summary: message.content || '첨부파일' };
  }
  if (entry.kind === 'QUESTION' || entry.kind === 'ANSWER') {
    const question = entry.data as CustomerQuestion;
    return { label: entry.kind === 'QUESTION' ? '고객 확인 질문' : '고객 답변', summary: entry.kind === 'ANSWER' ? `${question.question_text} — ${question.answer_text || ''}` : question.question_text };
  }
  if (entry.kind === 'VERIFICATION_REQUEST' || entry.kind === 'VERIFICATION_RESULT') {
    const task = entry.data as VerificationTask;
    return { label: entry.kind === 'VERIFICATION_REQUEST' ? '기관 확인 요청' : '기관 확인 결과', summary: task.result_summary || task.claim || task.target };
  }
  if (entry.kind === 'ACTION') {
    const action = entry.data as CaseAction;
    return { label: '대응 업무 기록', summary: action.note || actionLabel(action.action_type) };
  }
  return { label: 'Case 이벤트', summary: (entry.data as CaseEvent).event_type.replace(/_/g, ' ') };
};

const EntryBookmark: React.FC<{ entry: TimelineEntry; active: boolean; onToggle: Props['onToggleBookmark'] }> = ({ entry, active, onToggle }) => {
  const details = bookmarkDetails(entry);
  return <button type="button" className={`bank-entry-bookmark ${active ? 'active' : ''}`} aria-label={active ? '북마크 해제' : '북마크 추가'} aria-pressed={active} onClick={() => onToggle({ entryId: entry.id, ...details, createdAt: entry.occurredAt })}><Bookmark size={14} fill={active ? 'currentColor' : 'none'}/></button>;
};

const MessageEntry: React.FC<{ message: CaseMessage; bookmark: React.ReactNode; onRetry: Props['onRetryMessage']; onDismiss: Props['onDismissMessage'] }> = ({ message, bookmark, onRetry, onDismiss }) => {
  const mine = message.actor_user_id === CURRENT_BANK_USER.user_id;
  const system = message.message_kind === 'SYSTEM_EVENT';
  if (system) return <article className="timeline-system"><Bot size={15}/><div><div className="entry-meta"><b>{message.actor_display_name || 'Case 업데이트'}</b>{bookmark}<time>{formatClock(message.created_at)}</time></div><SafeMarkdown content={message.content}/></div></article>;
  const scope = message.channel === 'CUSTOMER' ? 'customer-message' : 'internal-message';
  return <article className={`message-row ${mine ? 'mine' : ''} ${scope}`}>
    <span className={`avatar ${message.actor_type.toLowerCase()}`}>{message.actor_type === 'BANK_AGENT' || message.actor_type === 'CUSTOMER_AGENT' ? <Bot size={16}/> : message.actor_type === 'CUSTOMER' ? <UserRound size={16}/> : <ShieldCheck size={16}/>}</span>
    <div className="message-wrap"><div className="entry-meta"><b>{mine ? '나' : message.actor_display_name}</b><span>{message.channel === 'CUSTOMER' ? '고객에게' : '은행 내부'}</span>{bookmark}</div><div className="message-bubble"><SafeMarkdown content={message.content}/>{message.attachments?.length > 0 && <div className="attachment-list">{message.attachments.map((attachment) => <a key={attachment.attachment_id} href={casesApi.attachmentUrl(attachment)} target="_blank" rel="noreferrer"><FileText size={14}/><span>{attachment.original_name}</span><small>{Math.ceil(attachment.size_bytes / 1024)}KB</small></a>)}</div>}</div>{message.delivery_state === 'FAILED' && <div className="message-delivery-error"><span>전송되지 않았습니다.</span><button type="button" onClick={() => onRetry(message)}>다시 전송</button><button type="button" onClick={() => onDismiss(message)}>지우기</button></div>}<time className={`message-time${message.delivery_state ? ` ${message.delivery_state.toLowerCase()}` : ''}`}>{message.delivery_state === 'SENDING' ? '전송 중…' : message.delivery_state === 'FAILED' ? '전송 실패' : formatClock(message.created_at)}</time></div>
  </article>;
};

const EntryCard: React.FC<{ entry: TimelineEntry; bookmark: React.ReactNode; onEditVerification: (task: VerificationTask) => void; onRetryMessage: Props['onRetryMessage']; onDismissMessage: Props['onDismissMessage'] }> = ({ entry, bookmark, onEditVerification, onRetryMessage, onDismissMessage }) => {
  if (entry.kind === 'MESSAGE') return <MessageEntry message={entry.data as CaseMessage} bookmark={bookmark} onRetry={onRetryMessage} onDismiss={onDismissMessage}/>;
  if (entry.kind === 'BRIEF') {
    const item = entry.data as StoredCase;
    return <article className="timeline-brief"><div className="entry-kicker"><Bot size={15}/>AI BRIEF{bookmark}</div><p>{item.initial_brief}</p><time>{formatClock(entry.occurredAt)}</time></article>;
  }
  if (entry.kind === 'QUESTION' || entry.kind === 'ANSWER') {
    const question = entry.data as CustomerQuestion;
    return <article className={`timeline-card question-card ${entry.kind === 'ANSWER' ? 'is-complete' : ''}`}><div className="timeline-card-icon">{entry.kind === 'ANSWER' ? <CheckCircle2 size={17}/> : <MessageCircleQuestion size={17}/>}</div><div><div className="entry-meta"><b>{entry.kind === 'ANSWER' ? '고객 답변' : '고객 확인 질문'}</b>{bookmark}<time>{formatClock(entry.occurredAt)}</time></div><p className="timeline-title">{question.question_text}</p>{entry.kind === 'ANSWER' && <p className="timeline-result">{question.answer_text}</p>}<small>{entry.kind === 'ANSWER' ? '담당자 확인 전 고객 진술입니다.' : '고객 답변을 기다리고 있습니다.'}</small></div></article>;
  }
  if (entry.kind === 'VERIFICATION_REQUEST' || entry.kind === 'VERIFICATION_RESULT') {
    const task = entry.data as VerificationTask;
    const result = entry.kind === 'VERIFICATION_RESULT';
    return <article className={`timeline-card verification-card ${result && task.status === 'COMPLETED' ? 'is-complete' : ''}`}><div className="timeline-card-icon"><Landmark size={17}/></div><div><div className="entry-meta"><b>{result ? '기관 확인 업데이트' : '기관 확인 요청'}</b>{bookmark}<time>{formatClock(entry.occurredAt)}</time></div><p className="timeline-title">{task.target}</p><p>{result && task.result_summary ? task.result_summary : task.claim}</p><div className="entry-actions"><span className="status-chip">{verificationStatusLabel(task.status)}</span><button onClick={() => onEditVerification(task)}>결과 확인·수정</button></div></div></article>;
  }
  if (entry.kind === 'ACTION') {
    const action = entry.data as CaseAction;
    return <article className="timeline-card action-card"><div className="timeline-card-icon"><ShieldCheck size={17}/></div><div><div className="entry-meta"><b>대응 업무 기록</b>{bookmark}<time>{formatClock(entry.occurredAt)}</time></div><p className="timeline-title">{actionLabel(action.action_type)}</p><p>{action.note}</p><small>업무 기록이며 실제 금융 조치 완료를 의미하지 않습니다.</small></div></article>;
  }
  const event = entry.data as CaseEvent;
  return <article className="timeline-event"><CircleDot size={13}/><span>{event.event_type.replace(/_/g, ' ')}</span>{bookmark}<time>{formatClock(event.occurred_at)}</time></article>;
};

export const SharedConversation: React.FC<Props> = ({ caseItem, bundle, view, onEditVerification, bookmarkedIds, onToggleBookmark, onRetryMessage, onDismissMessage }) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const initialized = useRef(false);
  const followLatest = useRef(true);
  const entries = useMemo(() => buildTimeline(caseItem, bundle, view === 'timeline'), [bundle, caseItem, view]);
  const latestEntry = entries[entries.length - 1];
  const latestEntryKey = latestEntry ? `${latestEntry.id}:${latestEntry.occurredAt}` : 'empty';
  useEffect(() => {
    const node = scrollRef.current;
    if (!node) return;
    if (!initialized.current || followLatest.current) node.scrollTop = node.scrollHeight;
    initialized.current = true;
  }, [latestEntryKey]);
  return <div ref={scrollRef} onScroll={(event) => { const node = event.currentTarget; followLatest.current = node.scrollHeight - node.scrollTop - node.clientHeight < 80; }} className="conversation-scroll" aria-live="polite">
    {entries.length === 0 ? <div className="conversation-empty">아직 Case 기록이 없습니다.</div> : entries.map((entry) => <div id={entry.id} className="bank-timeline-entry" key={entry.id}><EntryCard entry={entry} bookmark={<EntryBookmark entry={entry} active={bookmarkedIds.has(entry.id)} onToggle={onToggleBookmark}/>} onEditVerification={onEditVerification} onRetryMessage={onRetryMessage} onDismissMessage={onDismissMessage}/></div>) }
  </div>;
};
