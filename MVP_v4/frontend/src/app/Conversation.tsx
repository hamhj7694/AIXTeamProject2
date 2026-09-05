import { useState, type ReactNode } from 'react';
import { type CaseEvent } from '../api/cases.ts';
import { displayTime } from '../shared/caseList.ts';
import { composerKey, conversationPlacement, projectEvent, type Channel, type ConversationItem } from '../shared/conversation.ts';
import { createUuid } from '../shared/uuid.ts';

export function ConversationEntry({ item, actorId, utility }: { item: ConversationItem; actorId: string | null; utility?: ReactNode }) {
  const placement = conversationPlacement(item, actorId);
  return <li id={`conversation-${item.id}`} tabIndex={-1} className={`conversation-item ${placement}`} data-item-id={item.id}>
    <article className={item.kind === 'notice' ? 'conversation-notice' : 'conversation-bubble'}>
      <div className="conversation-meta"><strong>{item.title}</strong><time dateTime={item.createdAt}>{displayTime(item.createdAt)}</time>{utility}</div>
      <p>{item.body}</p>
    </article>
  </li>;
}

export function ConversationTimeline({ events, actorId = null, renderUtility }: {
  events: CaseEvent[]; actorId?: string | null; renderUtility?: (id: string) => ReactNode;
}) {
  const items = events.map(projectEvent).filter((item): item is ConversationItem => item !== null);
  return <ol className="timeline conversation-timeline" aria-label="사건 대화 기록">
    {!items.length && <li className="state">아직 대화나 사건 업데이트가 없습니다.</li>}
    {items.map(item => <ConversationEntry key={item.id} item={item} actorId={actorId} utility={renderUtility?.(item.id)} />)}
  </ol>;
}

const functions = ['고객에게 확인 질문', '기관 확인', '조치 기록', '사건 정리', 'AI에게 물어보기'];
export function ConversationComposer({ caseId, utilities }: { caseId: string; utilities?: ReactNode }) {
  const [channels, setChannels] = useState<Record<string, Channel>>({});
  const [participation, setParticipation] = useState<Record<string, boolean>>({});
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [panel, setPanel] = useState<string | null>(null);
  const [questions, setQuestions] = useState<Record<string, { id: string; content: string; selected: boolean }[]>>({});
  const [questionDrafts, setQuestionDrafts] = useState<Record<string, string>>({});
  const channel = channels[caseId] ?? 'BANK_INTERNAL';
  const enabled = participation[caseId] ?? true;
  const draftKey = composerKey(caseId, channel);
  const activeQuestions = questions[caseId] ?? [];
  const addQuestion = () => {
    const content = (questionDrafts[caseId] ?? '').trim();
    if (!content) return;
    setQuestions(value => ({ ...value, [caseId]: [...(value[caseId] ?? []), { id: createUuid(), content, selected: true }] }));
    setQuestionDrafts(value => ({ ...value, [caseId]: '' }));
  };
  return <div className="conversation-composer">
    <nav className="function-toolbar" aria-label="사건 대응 기능">
      {functions.slice(0, 2).map(label => <button key={label} onClick={() => setPanel(label)}>{label}</button>)}
      <details><summary>더보기</summary><div>{functions.slice(2).map(label => <button key={label} onClick={() => setPanel(label)}>{label}</button>)}</div></details>
      {utilities}
    </nav>
    <div className="composer-options">
      <button role="switch" aria-checked={enabled} aria-label="AI 대화 참여" onClick={() => setParticipation(value => ({ ...value, [caseId]: !enabled }))}>AI 참여 {enabled ? 'ON' : 'OFF'}</button>
      <div role="group" aria-label="메시지 채널">
        <button aria-pressed={channel === 'BANK_INTERNAL'} onClick={() => setChannels(value => ({ ...value, [caseId]: 'BANK_INTERNAL' }))}>은행 내부</button>
        <button aria-pressed={channel === 'CUSTOMER'} onClick={() => setChannels(value => ({ ...value, [caseId]: 'CUSTOMER' }))}>고객에게</button>
      </div>
    </div>
    <label htmlFor="message-draft" className="channel-caption">{channel === 'BANK_INTERNAL' ? '은행 내부 메시지 입력 중' : '고객에게 보내는 메시지 입력 중'}</label>
    <div className="composer-input"><button disabled title="첨부 기능 준비 중">첨부</button>
      <textarea id="message-draft" rows={3} maxLength={4000} value={drafts[draftKey] ?? ''} onChange={event => setDrafts(value => ({ ...value, [draftKey]: event.target.value }))} placeholder="메시지 초안을 작성하세요" />
      <button disabled title="대화 전송 기능 준비 중">전송</button>
    </div>
    <p className="composer-hint">현재는 초안만 작성할 수 있습니다. 메시지 전송과 AI 대화 참여는 준비 중입니다.</p>
    {panel && <div className="modal-backdrop"><section className="utility-dialog" role="dialog" aria-modal="true" aria-label={panel}>
      <div className="panel-heading"><h2>{panel}</h2><button autoFocus onClick={() => setPanel(null)}>닫기</button></div>
      {panel === '고객에게 확인 질문' ? <>
        <p>이미 확인된 내용을 제외하고 필요한 질문을 준비합니다. 현재는 질문 초안만 작성할 수 있습니다.</p>
        <button disabled>AI에게 질문 추천 받기</button>
        <label>직접 질문 추가<input aria-label="직접 질문 추가" maxLength={500} value={questionDrafts[caseId] ?? ''} onChange={event => setQuestionDrafts(value => ({ ...value, [caseId]: event.target.value }))} /></label>
        <button onClick={addQuestion}>추가</button>
        <ul className="question-drafts">{activeQuestions.map(question => <li key={question.id}><label><input type="checkbox" checked={question.selected} onChange={() => setQuestions(value => ({ ...value, [caseId]: (value[caseId] ?? []).map(item => item.id === question.id ? { ...item, selected: !item.selected } : item) }))} />{question.content}</label></li>)}</ul>
        <button disabled>선택한 질문 고객에게 전달</button><p>고객 전달과 답변 연결 기능은 준비 중입니다.</p>
      </> : <p>이 기능은 준비 중입니다. 실행 결과나 AI 응답은 아직 생성되지 않습니다.</p>}
    </section></div>}
  </div>;
}
