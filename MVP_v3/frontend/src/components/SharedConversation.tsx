import React, { useEffect, useMemo, useRef } from 'react';
import { Bookmark, Bot, CheckCircle2, CircleDot, Download, FileText, Landmark, MessageCircleQuestion, ShieldCheck, UserRound } from 'lucide-react';
import { casesApi, CURRENT_BANK_USER } from '../api/cases';
import type { CaseAction, CaseEvent, CaseMessage, CustomerQuestion, InitialReport, InitialReportSection, StoredCase, VerificationTask } from '../api/types';
import { actionLabel, formatClock, verificationStatusLabel } from '../presentation';
import { buildTimeline, type TimelineEntry } from '../timeline';
import type { CaseBundle } from '../api/types';
import type { BankBookmark } from '../bank/bookmarks';
import { eventLabel, userText, questionAnswerLabel } from '../userText';
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
    if (message.message_kind === 'REPORT_CARD') return { label: 'AI 최종 결과 보고서', summary: '사건 종결 시점의 최종 결과 보고서' };
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
  if (entry.kind === 'FINAL_REPORT') return { label: 'AI 최종 결과 보고서', summary: '사건 종결 시점의 최종 결과 보고서' };
  return { label: 'Case 이벤트', summary: eventLabel((entry.data as CaseEvent).event_type) };
};

interface FinalReportCardPayload {
  report_id: string;
  report_version: number;
  title: string;
  executive_summary: string;
  incident_summary: string;
  customer_impact_summary?: string;
  verified_facts: string[];
  verification_results?: string[];
  actions_taken: string[];
  unresolved_items?: string[];
  decision_basis?: string[];
  resolution: string;
  follow_up: string[];
  cautions: string[];
}

const parseFinalReport = (content: string): FinalReportCardPayload | null => {
  try {
    const parsed = JSON.parse(content) as FinalReportCardPayload | { report_card?: FinalReportCardPayload } | string;
    const value = typeof parsed === 'string' ? JSON.parse(parsed) as FinalReportCardPayload : 'report_card' in parsed && parsed.report_card ? parsed.report_card : parsed as FinalReportCardPayload;
    return value?.report_id && value?.title ? value : null;
  } catch {
    return null;
  }
};

const section = (report: InitialReport, key: string): InitialReportSection | undefined => report.sections.find((item) => item.section_key === key);
const sectionText = (report: InitialReport, ...keys: string[]): string => {
  for (const key of keys) {
    const value = section(report, key)?.content.text;
    if (typeof value === 'string' && value.trim()) return value.trim();
  }
  return '';
};
const sectionItems = (report: InitialReport, ...keys: string[]): string[] => {
  for (const key of keys) {
    const value = section(report, key)?.content.items;
    if (Array.isArray(value)) return value.filter((item): item is string => typeof item === 'string' && Boolean(item.trim()));
  }
  return [];
};
const storedReportPayload = (stored: InitialReport): FinalReportCardPayload => ({
  report_id: stored.report_id,
  report_version: stored.report_version,
  title: sectionText(stored, 'title') || '보이스피싱 대응 최종 결과 보고서',
  executive_summary: sectionText(stored, 'executive_summary', 'summary') || '담당자가 사건 종결을 승인했습니다.',
  incident_summary: sectionText(stored, 'incident_summary', 'summary') || '저장된 사건 기록과 처리 결과를 기준으로 작성된 최종 보고서입니다.',
  customer_impact_summary: sectionText(stored, 'customer_impact_summary'),
  verified_facts: sectionItems(stored, 'verified_facts'),
  verification_results: sectionItems(stored, 'verification_results', 'verification_status'),
  actions_taken: sectionItems(stored, 'actions_taken', 'current_actions'),
  unresolved_items: sectionItems(stored, 'unresolved_items', 'next_checks'),
  decision_basis: sectionItems(stored, 'decision_basis'),
  resolution: sectionText(stored, 'resolution') || stored.note || '담당자 승인에 따라 사건을 종결했습니다. 실제 금융 조치 결과는 기록된 근거를 기준으로 확인해야 합니다.',
  follow_up: sectionItems(stored, 'follow_up'),
  cautions: sectionItems(stored, 'cautions'),
});

const FinalReportCard: React.FC<{ report: FinalReportCardPayload; caseId: string; createdAt: string; bookmark: React.ReactNode }> = ({ report, caseId, createdAt, bookmark }) => {
  // Work on a display copy after parsing. Never run prose substitution on JSON keys/IDs.
  report = { ...report };
  for (const key of ['title', 'executive_summary', 'incident_summary', 'customer_impact_summary', 'resolution'] as const) {
    const text = report[key];
    if (text) report[key] = userText(text);
  }
  const list = (title: string, items: string[]) => items.length > 0 && <section><h4>{title}</h4><ul>{items.map((item, index) => <li key={`${title}-${index}`}>{userText(item)}</li>)}</ul></section>;
  return <article className="final-report-card">
    <header><span><FileText size={18}/></span><div><small>AI FINAL REPORT · v{report.report_version}</small><h3>{report.title}</h3></div>{bookmark}</header>
    <p className="final-report-summary">{report.executive_summary}</p>
    <div className="final-report-sections">
      <section><h4>사건 개요</h4><p>{report.incident_summary}</p></section>
      {report.customer_impact_summary && <section><h4>고객 피해·노출 상태</h4><p>{report.customer_impact_summary}</p></section>}
      {list('확인된 사실', report.verified_facts ?? [])}
      {list('기관 확인 결과', report.verification_results ?? [])}
      {list('대응 및 처리 내역', report.actions_taken ?? [])}
      {list('남은 미확인 사항', report.unresolved_items ?? [])}
      {list('종결 판단 근거', report.decision_basis ?? [])}
      <section className="final-report-resolution"><h4>최종 처리 결과</h4><p>{report.resolution}</p></section>
      {list('후속 업무', report.follow_up ?? [])}
      {list('유의사항', report.cautions ?? [])}
    </div>
    <footer><a href={casesApi.finalReportDownloadUrl(caseId, 'pdf')}><Download size={14}/>PDF 다운로드</a><a href={casesApi.finalReportDownloadUrl(caseId, 'docx')}><Download size={14}/>Word 다운로드</a><time>{formatClock(createdAt)}</time></footer>
  </article>;
};

const EntryBookmark: React.FC<{ entry: TimelineEntry; active: boolean; onToggle: Props['onToggleBookmark'] }> = ({ entry, active, onToggle }) => {
  const details = bookmarkDetails(entry);
  return <button type="button" className={`bank-entry-bookmark ${active ? 'active' : ''}`} aria-label={active ? '북마크 해제' : '북마크 추가'} aria-pressed={active} onClick={() => onToggle({ entryId: entry.id, ...details, createdAt: entry.occurredAt })}><Bookmark size={14} fill={active ? 'currentColor' : 'none'}/></button>;
};

const MessageEntry: React.FC<{ message: CaseMessage; bookmark: React.ReactNode; onRetry: Props['onRetryMessage']; onDismiss: Props['onDismissMessage'] }> = ({ message, bookmark, onRetry, onDismiss }) => {
  if (message.message_kind === 'REPORT_CARD') {
    const report = parseFinalReport(message.content);
    if (report) return <FinalReportCard report={report} caseId={message.case_id} createdAt={message.created_at} bookmark={bookmark}/>;
    const readableLegacyText = message.content.trim() && !message.content.trim().startsWith('{') ? message.content.trim() : '저장된 종결 기록을 문서 형식으로 정리했습니다.';
    return <FinalReportCard report={{
      report_id: message.message_id,
      report_version: 1,
      title: '보이스피싱 대응 최종 결과 보고서',
      executive_summary: readableLegacyText,
      incident_summary: '사건 종결 시점까지 Shared Case에 저장된 내용을 기준으로 한 기록입니다.',
      verified_facts: [], actions_taken: [],
      resolution: '담당자가 사건 종결을 승인했습니다. 실제 금융 조치 결과는 별도 기록과 근거를 확인해야 합니다.',
      follow_up: [], cautions: ['이전 보고서 형식으로 저장된 기록은 세부 항목이 제한될 수 있습니다.'],
    }} caseId={message.case_id} createdAt={message.created_at} bookmark={bookmark}/>;
  }
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
    if (entry.kind === 'QUESTION') return <article className="question-dispatch-card"><MessageCircleQuestion size={15}/><div><div className="entry-meta"><b>고객에게 확인 질문 발송</b>{bookmark}<time>{formatClock(entry.occurredAt)}</time></div><p>{question.question_text}</p></div><span>{question.status === 'ANSWERED' ? '답변 수신' : '답변 대기'}</span></article>;
    return <article className="timeline-card question-card is-complete"><div className="timeline-card-icon"><CheckCircle2 size={17}/></div><div><div className="entry-meta"><b>고객 답변</b>{bookmark}<time>{formatClock(entry.occurredAt)}</time></div><p className="timeline-title">{question.question_text}</p><p className="timeline-result">{questionAnswerLabel(question.answer_text ?? '', question.options)}</p><small>담당자 확인 전 고객 진술입니다.</small></div></article>;
  }
  if (entry.kind === 'FINAL_REPORT') {
    const stored = entry.data as InitialReport;
    return <FinalReportCard report={storedReportPayload(stored)} caseId={stored.case_id} createdAt={stored.created_at} bookmark={bookmark}/>;
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
  return <article className="timeline-event"><CircleDot size={13}/><span>{eventLabel(event.event_type)}</span>{bookmark}<time>{formatClock(event.occurred_at)}</time></article>;
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
