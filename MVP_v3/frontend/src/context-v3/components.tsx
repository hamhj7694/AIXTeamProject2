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

export const SourceBadge: React.FC<{ source: string }> = ({ source }) => <span className="context-source-badge" title={sourceLabels[source] ? undefined : source}>{sourceLabels[source] ?? '기타 출처'}</span>;
export const StatusBadge: React.FC<{ status: string }> = ({ status }) => <span className={`context-status-badge tone-${statusLabels[status] ? status.toLowerCase() : 'unknown'}`} title={statusLabels[status] ? undefined : status}>{statusLabels[status] ?? '상태 확인 필요'}</span>;

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
  if (compact) return <>{item.evidence_refs.length === 0 ? <span className="context-evidence-empty" aria-disabled="true"><FileSearch size={12}/>근거 없음</span> : <button type="button" className="context-evidence-toggle" aria-expanded={open} aria-controls={detailsId} onClick={() => setOpen((value) => !value)}><FileSearch size={12}/>근거 {item.evidence_refs.length}건</button>}{open && item.evidence_refs.length > 0 && <div id={detailsId} className="context-compact-evidence-panel">{item.masked && <p>화면 마스킹 적용</p>}<ul>{item.evidence_refs.map((ref) => <li key={`${ref.type}-${ref.id}`}>{ref.type} · {ref.id}{ref.revision ? ` · r${ref.revision}` : ''}</li>)}</ul>{item.confidence != null && <p>AI 신뢰도 {Math.round(item.confidence * 100)}%</p>}</div>}</>;
  return <details className="context-item-details"><summary><FileSearch size={12}/>근거와 상세 정보</summary><div><SourceBadge source={item.source_kind}/>{item.masked && <span>화면 마스킹 적용</span>}</div>{item.evidence_refs.length > 0 ? <ul>{item.evidence_refs.map((ref) => <li key={`${ref.type}-${ref.id}`}>{ref.type} · {ref.id}{ref.revision ? ` · r${ref.revision}` : ''}</li>)}</ul> : <p>연결된 근거 참조가 없습니다.</p>}{item.confidence != null && <p>AI 신뢰도 {Math.round(item.confidence * 100)}%</p>}</details>;
};

type FactProps = { item: ContextPanelItemV3; busy: boolean; onConfirm: () => void; onReject: () => void };
export const FactRow: React.FC<FactProps> = ({ item, busy, onConfirm, onReject }) => {
  const proposed = item.status === 'PROPOSED';
  const confirmed = item.status === 'CONFIRMED';
  const terminalLabel = item.status === 'REJECTED' ? '검토에서 제외된 정보' : item.status === 'SUPERSEDED' ? '새 정보로 대체된 기록' : '읽기 전용 정보';
  const lowConfidence = item.source_kind === 'AI_EXTRACTION' && item.confidence != null && item.confidence < .7;
  const tone = statusLabels[item.status] ? item.status.toLowerCase() : 'unknown';
  return <article className={`context-fact-row is-${tone}`}>
    <div className="context-fact-main"><span className="context-fact-marker" aria-hidden="true">{confirmed ? <Check size={13}/> : proposed ? <AlertCircle size={13}/> : '·'}</span><p><strong>{item.label}</strong><span>·</span><span>{item.display_value}</span></p><div className="context-fact-actions">{proposed && <button className="context-primary-action" disabled={busy} onClick={onConfirm}><Check size={13}/>확정</button>}{proposed && <MoreMenu label={`${item.label} 추가 작업`}><button disabled={busy} onClick={onReject}><X size={13}/>잘못된 정보로 제외</button></MoreMenu>}</div></div>
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

export const TaskCard: React.FC<{ item: ContextPanelItemV3; busy: boolean; onStart: () => void; onComplete: () => void; onBlock: () => void; onCancel: () => void }> = ({ item, busy, onStart, onComplete, onBlock, onCancel }) => {
  const actionable = ['TODO', 'IN_PROGRESS', 'BLOCKED'].includes(item.status);
  const primary = item.status === 'TODO' || item.status === 'BLOCKED' ? { label: item.status === 'BLOCKED' ? '재개' : '시작', icon: <Play size={13}/>, run: onStart } : item.status === 'IN_PROGRESS' ? { label: '완료', icon: <Check size={13}/>, run: onComplete } : null;
  return <article className={`context-domain-card task-card is-${item.status.toLowerCase()}`}><header><div><strong>{item.label}</strong><SourceBadge source={item.source_kind}/></div><StatusBadge status={item.status}/></header><p>{item.display_value}</p>{actionable && <footer>{primary && <button className="context-primary-action" disabled={busy} onClick={primary.run}>{primary.icon}{primary.label}</button>}<MoreMenu label={`${item.label} 업무 작업`}>{item.status === 'IN_PROGRESS' && <button disabled={busy} onClick={onBlock}><Pause size={13}/>보류</button>}<button disabled={busy} onClick={onCancel}><X size={13}/>업무 취소</button></MoreMenu></footer>}<Evidence item={item}/></article>;
};

export const SectionShell: React.FC<{ id: string; title: string; count?: number; attention?: number; open: boolean; onOpenChange: (open: boolean) => void; action?: React.ReactNode; children: React.ReactNode }> = ({ id, title, count, attention = 0, open, onOpenChange, action, children }) => {
  const contentId = `context-section-${id.toLowerCase()}-content`;
  return <section id={`context-section-${id.toLowerCase()}`} className={`context-v3-accordion ${open ? 'is-open' : ''}`}>
    <header className="context-section-header"><button type="button" className="context-section-toggle" aria-expanded={open} aria-controls={contentId} onClick={() => onOpenChange(!open)}><ChevronDown size={15}/><strong>{title}</strong>{attention > 0 && <em>{attention}건 확인 필요</em>}{count != null && <b>{count}</b>}</button>{action && <div className="context-section-action">{action}</div>}</header>
    {open && <div id={contentId} className="context-v3-accordion-body">{children}</div>}
  </section>;
};

export const HistoryHint: React.FC<{ count: number; label?: string }> = ({ count, label = '완료·취소·제외 항목' }) => count > 0 ? <p className="context-history-summary">{label} {count}건</p> : null;
