import React, { useEffect, useId, useRef, useState } from 'react';
import { AlertCircle, Check, ChevronDown, FileSearch, MoreHorizontal, Pause, Pencil, Play, RotateCcw, X } from 'lucide-react';
import type { ContextPanelItemV3 } from './types';

const sourceLabels: Record<string, string> = {
  AI_EXTRACTION: 'AI 추출', CUSTOMER_STATEMENT: '고객 진술', STAFF_OBSERVATION: '직원 입력',
  BANK_RECORD: '은행 기록', OFFICIAL_VERIFICATION: '기관 확인', AI_SUGGESTION: 'AI 제안',
  STAFF_CREATED: '직원 생성', AI_SUGGESTION_ACCEPTED: 'AI 제안 채택', SYSTEM_REQUIRED: '필수 업무',
  CUSTOMER_PROGRESS: '고객 진행', PUBLIC_MESSAGE: '고객 안내', STAFF_OVERRIDE: '직원 편집',
  DETERMINISTIC_PROJECTION: '자동 요약', STAFF_RECORD: '직원 기록',
};

const statusLabels: Record<string, string> = {
  PROPOSED: '확인 필요', CONFIRMED: '확정', CURRENT: '최신', PENDING: '확인 필요',
  IN_PROGRESS: '진행 중', ON_HOLD: '확인 중단', COMPLETED: '완료', FAILED: '확인 실패', TODO: '대기',
  BLOCKED: '보류', CANCELLED: '취소', PUBLISHED: '공개됨', SUBMITTED: '접수됨',
  NOT_APPLICABLE: '해당 없음', UNKNOWN: '미확인', UPDATING: '갱신 중', STALE: '오래된 정보',
  UNCACHED: '확인 필요', OPEN: '확인 필요',
};

const evidenceLabels: Record<string, string> = {
  MESSAGE: '대화 기록', QUESTION_ANSWER: '고객 답변', BANK_TRANSACTION: '거래 기록',
  VERIFICATION_RESULT: '기관 확인 결과', ATTACHMENT: '첨부 자료',
  STRUCTURED_SIGNAL: '분석 근거', STRUCTURED_ATOM: '분석 근거', STAFF_RECORD: '담당자 기록',
};

const internalDisplayLabels: Record<string, string> = {
  TRANSFERRED: '이체함', NOT_TRANSFERRED: '이체하지 않음', UNKNOWN: '확인 필요',
  YES: '예', NO: '아니요', PARTIAL: '일부 해당',
};

// Provider values are enum-like identifiers, not user-facing copy. Keep the
// identifiers in storage but translate them at the final presentation edge.
const providerValueLabels: Record<string, string> = {
  OTHER: '\uae30\ud0c0', UNKNOWN: '\ud655\uc778 \ud544\uc694', NONE: '\uc5c6\uc74c',
  POLICE_SERVICE: '\uacbd\ucc30', PROSECUTION_SERVICE: '\uac80\ucc30',
  FINANCIAL_SUPERVISORY_SERVICE: '\uae08\uc735\uac10\ub3c5\uc6d0',
  BANK: '\uc740\ud589', CARD_COMPANY: '\uce74\ub4dc\uc0ac', COURT: '\ubc95\uc6d0',
  REQUESTED: '\uc694\uccad\ub428', INSTRUCTED: '\uc9c0\uc2dc\ub428',
  TRANSFERRED: '\uc774\uccb4\ud568', NOT_TRANSFERRED: '\uc774\uccb4\ud558\uc9c0 \uc54a\uc74c',
  EXPOSED: '\ub178\ucd9c \uc758\uc2ec',
};

const providerCopy = (text: string): string => Object.entries(providerValueLabels)
  .reduce((current, [token, label]) => current.replace(new RegExp(`\\b${token}\\b`, 'g'), label), text);

export const staffDisplayLabel = (item: ContextPanelItemV3): string => {
  const keyLabels: Record<string, string> = {
    'offender.claimed_organization': '\uc0ac\uce6d \uae30\uad00',
    'offender.claimed_person_or_role': '\uc0ac\uce6d \uc778\ubb3c\u00b7\uc5ed\ud560',
    'circumstance.tactic': '\uc555\ubc15\u00b7\uc870\uc791 \uc218\ubc95',
    'circumstance.demand': '\uc0c1\ub300\ubc29 \uc694\uad6c',
  };
  return keyLabels[item.semantic_key] ?? providerCopy(item.label);
};

export const staffDisplayValue = (item: ContextPanelItemV3): string => {
  const typedStatus = typeof item.value?.status === 'string' ? item.value.status : '';
  const organizationCode = typeof item.value?.organization_code === 'string' ? item.value.organization_code : '';
  const organization = providerValueLabels[organizationCode];
  if (organization && item.semantic_key === 'offender.claimed_organization' && (!item.display_value || /OTHER|UNKNOWN/.test(item.display_value))) {
    return `${organization} \uc0ac\uce6d \uc815\ud669`;
  }
  return providerCopy(internalDisplayLabels[item.display_value] ?? internalDisplayLabels[typedStatus] ?? item.display_value);
};

export const evidenceSummaries = (refs: ContextPanelItemV3['evidence_refs']): string[] => {
  const detailed = refs.map((ref) => ref.summary?.trim()).filter((summary): summary is string => Boolean(summary));
  if (detailed.length === refs.length) return detailed;
  const counts = new Map<string, number>();
  refs.forEach((ref) => {
    if (ref.summary) return;
    const label = evidenceLabels[ref.type] ?? '기타 근거';
    counts.set(label, (counts.get(label) ?? 0) + 1);
  });
  return [...detailed, ...[...counts].map(([label, count]) => `${label} ${count}건`)];
};

export const SourceBadge: React.FC<{ source: string }> = ({ source }) => <span className="context-source-badge">{sourceLabels[source] ?? '기타 출처'}</span>;
export const StatusBadge: React.FC<{ status: string }> = ({ status }) => <span className={`context-status-badge tone-${statusLabels[status] ? status.toLowerCase() : 'unknown'}`}>{statusLabels[status] ?? '상태 확인 필요'}</span>;

export const MoreMenu: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const popoverId = useId();
  useEffect(() => {
    if (!open) return;
    root.current?.querySelector<HTMLButtonElement>('.context-more-popover button:not(:disabled)')?.focus();
    const close = (event: MouseEvent | KeyboardEvent) => {
      if (event instanceof KeyboardEvent && event.key !== 'Escape') return;
      if (event instanceof MouseEvent && root.current?.contains(event.target as Node)) return;
      setOpen(false);
      if (event instanceof KeyboardEvent) trigger.current?.focus();
    };
    window.addEventListener('mousedown', close); window.addEventListener('keydown', close);
    return () => { window.removeEventListener('mousedown', close); window.removeEventListener('keydown', close); };
  }, [open]);
  return <div className="context-more-menu" ref={root}>
    <button ref={trigger} type="button" className="context-more-trigger" aria-label={label} aria-expanded={open} aria-controls={popoverId} onClick={() => setOpen((value) => !value)}><MoreHorizontal size={15}/></button>
    {open && <div id={popoverId} className="context-more-popover" role="group" aria-label={label} onClick={(event) => { if ((event.target as HTMLElement).closest('button:not(:disabled)')) setOpen(false); }}>{children}</div>}
  </div>;
};

const Evidence: React.FC<{ item: ContextPanelItemV3; compact?: boolean }> = ({ item, compact = false }) => {
  const [open, setOpen] = useState(false);
  const detailsId = useId();
  const summaries = evidenceSummaries(item.evidence_refs);
  const summaryList = summaries.length > 0 ? <ul>{summaries.map((summary, index) => <li key={summary + '-' + index}>{summary}</li>)}</ul> : null;
  if (compact) return <>{item.evidence_refs.length === 0 ? <span className="context-evidence-empty" aria-disabled="true"><FileSearch size={12}/>근거 없음</span> : <button type="button" className="context-evidence-toggle" aria-expanded={open} aria-controls={detailsId} onClick={() => setOpen((value) => !value)}><FileSearch size={12}/>근거 {item.evidence_refs.length}건</button>}{open && summaryList && <div id={detailsId} className="context-compact-evidence-panel">{item.masked && <p>민감정보가 가려진 화면용 근거입니다.</p>}{summaryList}</div>}</>;
  return <details className="context-item-details"><summary><FileSearch size={12}/>근거와 상세 정보</summary><div><SourceBadge source={item.source_kind}/>{item.masked && <span>민감정보 가림 적용</span>}</div>{summaryList ?? <p>연결된 근거가 없습니다.</p>}</details>;
};

type FactProps = { item: ContextPanelItemV3; busy: boolean; onConfirm: () => void; onReject: () => void; onCorrect: () => void; onUnconfirm: () => void; onInvalidate: () => void };
export const FactRow: React.FC<FactProps> = ({ item, busy, onConfirm, onReject, onCorrect, onUnconfirm, onInvalidate }) => {
  const proposed = item.status === 'PROPOSED';
  const confirmed = item.status === 'CONFIRMED';
  const terminalLabel = item.status === 'REJECTED' ? '검토에서 제외된 정보' : item.status === 'SUPERSEDED' ? '새 정보로 대체된 기록' : '읽기 전용 정보';
  const lowConfidence = item.source_kind === 'AI_EXTRACTION' && item.confidence != null && item.confidence < .7;
  const tone = statusLabels[item.status] ? item.status.toLowerCase() : 'unknown';
  return <article className={`context-fact-row is-${tone}`}>
    <div className="context-fact-main"><span className="context-fact-marker" aria-hidden="true">{confirmed ? <Check size={13}/> : proposed ? <AlertCircle size={13}/> : '·'}</span><p><strong>{item.label}</strong><span>·</span><span>{staffDisplayValue(item)}</span></p><div className="context-fact-actions">{proposed && <button className="context-primary-action" disabled={busy} onClick={onConfirm}><Check size={13}/>확정</button>}{(proposed || confirmed) && <MoreMenu label={`${item.label} 추가 작업`}>{confirmed && <button disabled={busy} onClick={onCorrect}><Pencil size={13}/>정보 정정</button>}{confirmed && <button disabled={busy} onClick={onUnconfirm}><RotateCcw size={13}/>확정 취소</button>}<button disabled={busy} onClick={confirmed ? onInvalidate : onReject}><X size={13}/>잘못된 정보로 제외</button></MoreMenu>}</div></div>
    <div className="context-fact-meta"><SourceBadge source={item.source_kind}/><StatusBadge status={item.status}/><Evidence item={item} compact/></div>
    {!proposed && !confirmed && <span className="context-readonly-note">{terminalLabel}</span>}
    {lowConfidence && <div className="context-confidence-warning"><AlertCircle size={12}/>AI 추출 · 확인 필요</div>}
  </article>;
};

export const VerificationCard: React.FC<{ item: ContextPanelItemV3; busy: boolean; onOpen: () => void }> = ({ item, busy, onOpen }) => {
  const primary = item.status === 'PENDING' ? '확인 시작' : item.status === 'IN_PROGRESS' ? '결과 기록' : item.status === 'ON_HOLD' ? '확인 재개·결과 기록' : item.status === 'FAILED' ? '재시도' : '';
  return <article className={`context-domain-card verification-card is-${item.status.toLowerCase()}`}><header><div><strong>{item.label}</strong><SourceBadge source={item.source_kind}/></div><StatusBadge status={item.status}/></header><p>{item.display_value}</p>{primary && <footer><button className="context-primary-action" disabled={busy} onClick={onOpen}>{item.status === 'PENDING' ? <Play size={13}/> : item.status === 'FAILED' ? <RotateCcw size={13}/> : <Pencil size={13}/>}{primary}</button></footer>}<Evidence item={item}/></article>;
};

export const SuggestionCard: React.FC<{ item: ContextPanelItemV3; busy: boolean; onAccept: () => void; onDismiss: () => void }> = ({ item, busy, onAccept, onDismiss }) => <article className="context-domain-card suggestion-card"><header><div><strong>{item.label}</strong><SourceBadge source={item.source_kind}/></div><StatusBadge status={item.status}/></header><p>{item.display_value}</p>{item.status === 'PROPOSED' && <footer><button className="context-primary-action" disabled={busy} onClick={onAccept}><Check size={13}/>업무로 채택</button><MoreMenu label={`${item.label} 제안 작업`}><button disabled={busy} onClick={onDismiss}><X size={13}/>제안 제외</button></MoreMenu></footer>}<Evidence item={item}/></article>;

export const TaskCard: React.FC<{ item: ContextPanelItemV3; busy: boolean; onStart: () => void; onComplete: () => void; onBlock: () => void; onCancel: () => void; onEdit: () => void }> = ({ item, busy, onStart, onComplete, onBlock, onCancel, onEdit }) => {
  const actionable = ['TODO', 'IN_PROGRESS', 'BLOCKED'].includes(item.status);
  const primary = item.status === 'TODO' || item.status === 'BLOCKED' ? { label: item.status === 'BLOCKED' ? '재개' : '시작', icon: <Play size={13}/>, run: onStart } : item.status === 'IN_PROGRESS' ? { label: '완료', icon: <Check size={13}/>, run: onComplete } : null;
  return <article className={`context-domain-card task-card is-${item.status.toLowerCase()}`}><header><div><strong>{item.label}</strong><SourceBadge source={item.source_kind}/></div><StatusBadge status={item.status}/></header><p>{item.display_value}</p>{actionable && <footer>{primary && <button className="context-primary-action" disabled={busy} onClick={primary.run}>{primary.icon}{primary.label}</button>}<MoreMenu label={`${item.label} 업무 작업`}><button disabled={busy} onClick={onEdit}><Pencil size={13}/>업무 수정</button>{item.status === 'IN_PROGRESS' && <button disabled={busy} onClick={onBlock}><Pause size={13}/>보류</button>}<button disabled={busy} onClick={onCancel}><X size={13}/>업무 취소</button></MoreMenu></footer>}<Evidence item={item}/></article>;
};

export const SectionShell: React.FC<{ id: string; title: string; count?: number; attention?: number; open: boolean; onOpenChange: (open: boolean) => void; action?: React.ReactNode; children: React.ReactNode }> = ({ id, title, count, attention = 0, open, onOpenChange, action, children }) => {
  const contentId = `context-section-${id.toLowerCase()}-content`;
  return <section id={`context-section-${id.toLowerCase()}`} className={`context-v3-accordion ${open ? 'is-open' : ''}`}>
    <header className="context-section-header"><button type="button" className="context-section-toggle" aria-expanded={open} aria-controls={contentId} onClick={() => onOpenChange(!open)}><ChevronDown size={15}/><strong>{title}</strong>{attention > 0 && <em>{attention}건 확인 필요</em>}{count != null && <b>{count}</b>}</button>{action && <div className="context-section-action">{action}</div>}</header>
    {open && <div id={contentId} className="context-v3-accordion-body">{children}</div>}
  </section>;
};

export const HistoryHint: React.FC<{ items: ContextPanelItemV3[]; busy: boolean; onRestore: (item: ContextPanelItemV3) => void; onDelete?: (item: ContextPanelItemV3) => void; kind?: 'task' | 'fact' }> = ({ items, busy, onRestore, onDelete, kind = 'task' }) => {
  const [open, setOpen] = useState(false);
  const contentId = useId();
  if (items.length === 0 && kind === 'task') return null;
  return <section className="context-archive-history">
    <button type="button" className="context-history-summary" aria-expanded={open} aria-controls={contentId} onClick={() => setOpen((value) => !value)}><RotateCcw size={13}/><span>{kind === 'fact' ? '제외된 정보' : '완료·취소 업무'} {items.length}건</span><ChevronDown size={14}/></button>
    {open && <div id={contentId} className="context-archive-list"><p>{items.length === 0 ? '제외된 정보가 없습니다.' : kind === 'fact' ? '검토에서 제외한 정보입니다. 복구하면 다시 확인 필요 상태로 돌아갑니다.' : '완료하거나 취소한 업무입니다. 복구하면 대기 상태의 현재 업무로 돌아갑니다.'}</p>{items.map((item) => <article key={item.item_id}><header><strong>{item.label}</strong><StatusBadge status={item.status}/></header><p>{staffDisplayValue(item)}</p><footer><SourceBadge source={item.source_kind}/><button type="button" disabled={busy} onClick={() => onRestore(item)}><RotateCcw size={12}/>{kind === 'fact' ? '정보 복구' : '업무 복구'}</button>{kind === 'fact' && onDelete && <button type="button" className="context-danger-action" disabled={busy} onClick={() => onDelete(item)}><X size={12}/>완전 삭제</button>}</footer></article>)}</div>}
  </section>;
};
