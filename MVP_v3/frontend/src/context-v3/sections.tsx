import React from 'react';
import { Check, Eye, EyeOff, Play, X } from 'lucide-react';
import type { ContextPanelItemV3, ContextPanelSectionV3 } from './types';

const groupLabels: Record<string, string> = {
  claims: '상대방 주장', demands: '상대방 요구', tactics: '압박·조작 수법',
  needs_attention: '확인이 필요한 항목', in_progress: '확인 중', confirmed: '확인 완료', failed: '확인 실패',
  suggestions: 'AI 제안 · 직원 검토 필요', active: '진행 중', completed: '완료·취소',
};

export type WorkflowAction = 'ACCEPT' | 'DISMISS' | 'START' | 'COMPLETE' | 'CANCEL';

const Item: React.FC<{ item: ContextPanelItemV3; busy: boolean; onReview?: (item: ContextPanelItemV3, decision: 'CONFIRM' | 'REJECT') => void; onWorkflow?: (item: ContextPanelItemV3, action: WorkflowAction) => void; onOpenVerification?: (id: string) => void }> = ({ item, busy, onReview, onWorkflow, onOpenVerification }) => <article className={`context-v3-item is-${item.status.toLowerCase()}`}>
  <header><b>{item.label}</b><span>{item.status === 'PROPOSED' ? '검토 대기' : item.status === 'CONFIRMED' ? '확정' : item.status}</span></header>
  <p>{item.display_value}</p>
  <small>{item.source_kind}{item.confidence != null ? ` · 신뢰도 ${Math.round(item.confidence * 100)}%` : ''}{item.masked ? ' · 일부 마스킹' : ''}</small>
  {item.evidence_refs.length > 0 && <small>근거 {item.evidence_refs.map((ref) => `${ref.type}:${ref.id}`).join(', ')}</small>}
  {item.status === 'PROPOSED' && item.source_kind !== 'AI_SUGGESTION' && onReview && <div className="context-v3-actions"><button disabled={busy} onClick={() => onReview(item, 'CONFIRM')}><Check size={13}/>확정</button><button disabled={busy} onClick={() => onReview(item, 'REJECT')}><X size={13}/>거절</button></div>}
  {item.source_kind === 'AI_SUGGESTION' && item.status === 'PROPOSED' && onWorkflow && <div className="context-v3-actions"><button disabled={busy} onClick={() => onWorkflow(item, 'ACCEPT')}><Check size={13}/>업무로 채택</button><button disabled={busy} onClick={() => onWorkflow(item, 'DISMISS')}><X size={13}/>제외</button></div>}
  {item.semantic_key.startsWith('task.') && !['COMPLETED', 'CANCELLED'].includes(item.status) && onWorkflow && <div className="context-v3-actions"><button disabled={busy} onClick={() => onWorkflow(item, 'START')}><Play size={13}/>시작</button><button disabled={busy} onClick={() => onWorkflow(item, 'COMPLETE')}><Check size={13}/>결과 기록</button><button disabled={busy} onClick={() => onWorkflow(item, 'CANCEL')}><X size={13}/>취소</button></div>}
  {item.semantic_key === 'verification.institution' && onOpenVerification && <div className="context-v3-actions"><button disabled={busy} onClick={() => onOpenVerification(item.item_id)}>기관 확인 열기</button></div>}
</article>;

export const ContextV3Section: React.FC<{ section: ContextPanelSectionV3; busy: boolean; onReview: (item: ContextPanelItemV3, decision: 'CONFIRM' | 'REJECT') => void; onWorkflow: (item: ContextPanelItemV3, action: WorkflowAction) => void; onOpenVerification?: (id: string) => void }> = ({ section, busy, onReview, onWorkflow, onOpenVerification }) => {
  const count = section.items.length + Object.values(section.groups).reduce((sum, items) => sum + items.length, 0);
  return <section className={`context-section context-v3-section section-${section.section_id.toLowerCase()}`}>
    <h3>{section.section_id === 'CUSTOMER_SHARE' ? <Eye size={14}/> : <EyeOff size={14}/>} {section.title}<small>{count}건</small></h3>
    {section.items.map((item) => <Item key={item.item_id} item={item} busy={busy} onReview={onReview} onWorkflow={onWorkflow} onOpenVerification={onOpenVerification}/>)}
    {Object.entries(section.groups).map(([group, items]) => <div className="context-v3-group" key={group}><h4>{groupLabels[group] ?? group}</h4>{items.map((item) => <Item key={item.item_id} item={item} busy={busy} onReview={onReview} onWorkflow={onWorkflow} onOpenVerification={onOpenVerification}/>)}</div>)}
    {count === 0 && <p className="context-empty">등록된 내용이 없습니다.</p>}
  </section>;
};
