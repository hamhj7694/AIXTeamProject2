import React from 'react';
import { AlertCircle, CheckCircle2, Pencil, Plus, RotateCcw } from 'lucide-react';
import { FactRow, HistoryHint, MoreMenu, SectionShell, StatusBadge, SuggestionCard, TaskCard, VerificationCard } from './components';
import type { ContextPanelItemV3, ContextPanelSectionV3 } from './types';

export type WorkflowAction = 'ACCEPT' | 'DISMISS' | 'START' | 'COMPLETE' | 'BLOCK' | 'CANCEL' | 'RESTORE';
type SharedProps = { section: ContextPanelSectionV3; busy: boolean; onReview: (item: ContextPanelItemV3, decision: 'CONFIRM' | 'REJECT' | 'RESTORE' | 'UNCONFIRM' | 'INVALIDATE') => void; onCorrect: (item: ContextPanelItemV3) => void };
type OpenStateProps = { open: boolean; onOpenChange: (open: boolean) => void };

const total = (section: ContextPanelSectionV3) => section.items.length + Object.entries(section.groups).filter(([group]) => group !== 'archived').reduce((sum, [, items]) => sum + items.length, 0);
const proposed = (section: ContextPanelSectionV3) => [...section.items, ...Object.values(section.groups).flat()].filter((item) => item.status === 'PROPOSED').length;
const FactList: React.FC<SharedProps> = ({ section, busy, onReview, onCorrect }) => section.items.length === 0 ? <p className="context-empty">등록된 정보가 없습니다.</p> : <div className="context-fact-list">{section.items.map((item) => <FactRow key={item.item_id} item={item} busy={busy} onConfirm={() => onReview(item, 'CONFIRM')} onReject={() => onReview(item, 'REJECT')} onCorrect={() => onCorrect(item)} onUnconfirm={() => onReview(item, 'UNCONFIRM')} onInvalidate={() => onReview(item, 'INVALIDATE')}/>)}</div>;
const AddButton: React.FC<{ label: string; onClick: () => void; expanded: boolean; controls: string }> = ({ label, onClick, expanded, controls }) => <button type="button" className="context-section-add" onClick={onClick} aria-expanded={expanded} aria-controls={controls}><Plus size={13}/>{label}</button>;
const amountTotal = (items: ContextPanelItemV3[], semanticKey: string, status: 'CONFIRMED' | 'PROPOSED' = 'CONFIRMED') => {
  const candidates = items.filter((item) => item.semantic_key === semanticKey && item.status === status)
    .filter((item) => !['NEGATIVE', 'DENIED', 'UNKNOWN'].includes(String(item.value?.polarity ?? '').toUpperCase()))
    .filter((item) => !['UNCERTAIN', 'UNKNOWN', 'UNVERIFIED'].includes(String(item.value?.verification_status ?? '').toUpperCase()));
  const finalItems = candidates.filter((item) => item.value?.amount_scope === 'FINAL');
  const selected = finalItems.length > 0 ? finalItems : candidates;
  const values = selected
    .map((item) => Number(item.value?.amount_krw))
    .filter((value) => Number.isFinite(value) && value > 0);
  return { count: values.length, total: values.reduce((sum, value) => sum + value, 0) };
};
const amountTotalByDirection = (items: ContextPanelItemV3[], direction: 'OUT' | 'IN', status: 'CONFIRMED' | 'PROPOSED' = 'CONFIRMED') => {
  const values = items
    .filter((item) => item.semantic_key === 'transfer.actual.amount' && item.status === status)
    .filter((item) => (item.value?.direction ?? item.value?.amount_direction ?? 'OUT') === direction)
    .filter((item) => !['NEGATIVE', 'DENIED', 'UNKNOWN'].includes(String(item.value?.polarity ?? '').toUpperCase()))
    .filter((item) => !['UNCERTAIN', 'UNKNOWN', 'UNVERIFIED'].includes(String(item.value?.verification_status ?? '').toUpperCase()))
    .map((item) => Number(item.value?.amount_krw))
    .filter((value) => Number.isFinite(value) && value > 0);
  return { count: values.length, total: values.reduce((sum, value) => sum + value, 0) };
};
const AmountSummary: React.FC<{ section: ContextPanelSectionV3 }> = ({ section }) => {
  const requested = amountTotal(section.items, 'transfer.requested.amount');
  const sent = amountTotalByDirection(section.items, 'OUT');
  const returned = amountTotalByDirection(section.items, 'IN');
  // AI 추천(PROPOSED)은 개별 Fact에서만 보여주고, 직원 확정 전에는 공식 합계에 포함하지 않는다.
  if (requested.count === 0 && sent.count === 0 && returned.count === 0) return null;
  return <div className="context-amount-summary" aria-label="금액 합계">
    {(requested.count > 0 || sent.count > 0 || returned.count > 0) && <span><b>직원 확정 금액</b><em>{requested.count + sent.count + returned.count}건</em></span>}
    {requested.count > 0 && <span><b>요구 금액 {requested.count}건</b><em>합계 {requested.total.toLocaleString('ko-KR')}원</em></span>}
    {sent.count > 0 && <span><b>실제 송금 {sent.count}건</b><em>합계 {sent.total.toLocaleString('ko-KR')}원</em></span>}
    {returned.count > 0 && <span><b>반환 {returned.count}건</b><em>합계 {returned.total.toLocaleString('ko-KR')}원</em></span>}
    {sent.count > 0 && returned.count > 0 && <span><b>순손실</b><em>{(sent.total - returned.total).toLocaleString('ko-KR')}원</em></span>}
  </div>;
};
const summaryCountPattern = /^확정 사실 \d+건 · 검토 대기 \d+건$/;

export const visibleSummaryItems = (section: ContextPanelSectionV3, risk: string, status: string) => {
  const caseMetadata = `위험도 ${risk} · 진행 상태 ${status}`;
  return section.items
    .filter((item) => item.source_kind !== 'DETERMINISTIC_PROJECTION' || item.display_value !== caseMetadata)
    .filter((item) => !summaryCountPattern.test(item.display_value))
    .filter((item) => !/^확인 필요 · 추가 확인이 필요한 정보 \d+건$/.test(item.display_value))
    // 금액 건수·합계는 피해·노출 Section의 전용 요약에서 표시한다.
    .filter((item) => !/^확인된 사실 · 실제 이체 \d+건 · 합계 /.test(item.display_value));
};

const summaryCount = (section: ContextPanelSectionV3) => section.items.find((item) => summaryCountPattern.test(item.display_value))?.display_value ?? '확정 사실 0건 · 검토 대기 0건';

export const SummarySection: React.FC<{ section: ContextPanelSectionV3; caseRisk: string; caseStatus: string; projectionStatus: string; editing: boolean; onEdit: () => void; onReset: () => void; editor: React.ReactNode }> = ({ section, caseRisk, caseStatus, projectionStatus, editing, onEdit, onReset, editor }) => <section id="context-section-summary" className="context-summary-area">
  <header><div><span>현재 사건 요약</span><StatusBadge status={projectionStatus}/></div>{!editing && <div className="context-summary-actions"><button type="button" onClick={onEdit} aria-label="표시 요약 편집" title="표시 요약 편집"><Pencil size={13}/><span>표시 요약 편집</span></button><MoreMenu label="요약 추가 작업"><button onClick={onReset}><RotateCcw size={13}/>자동 요약으로 복원</button></MoreMenu></div>}</header>
  {editing ? editor : <div className="context-summary-copy">{visibleSummaryItems(section, caseRisk, caseStatus).map((item) => {
    const amountMatch = item.display_value.match(/^확인된 사실 · 실제 이체 (\d+)건 · 합계 ([^:]+): (.+)$/);
    if (!amountMatch) return <p key={item.item_id}>{item.display_value}</p>;
    return <div className="context-summary-amount" key={item.item_id}>
      <div><span>확인된 실제 이체</span><strong>{amountMatch[1]}건</strong></div>
      <div><span>확정 합계</span><strong>{amountMatch[2]}</strong></div>
    </div>;
  })}</div>}
  <footer><span className="context-summary-count">{summaryCount(section)}</span><span>사건 정보 기준 자동 요약</span></footer>
</section>;

type FactSectionProps = SharedProps & OpenStateProps & { onAdd: () => void; addOpen: boolean; createForm: React.ReactNode; onDeleteExcluded: (item: ContextPanelItemV3) => void };
export const ExposureSection: React.FC<FactSectionProps> = (props) => <SectionShell id="EXPOSURE" title="피해·노출" count={total(props.section)} attention={proposed(props.section)} open={props.open} onOpenChange={props.onOpenChange} action={<AddButton label="정보 추가" onClick={props.onAdd} expanded={props.addOpen} controls="context-create-exposure"/>}>{props.createForm}<AmountSummary section={props.section}/><FactList {...props}/><HistoryHint kind="fact" items={props.section.groups.archived ?? []} busy={props.busy} onRestore={(item) => props.onReview(item, 'RESTORE')} onDelete={props.onDeleteExcluded}/></SectionShell>;
export const ImpersonationSection: React.FC<FactSectionProps> = (props) => <SectionShell id="IMPERSONATION_CONTACT" title="사칭·접촉 정보" count={total(props.section)} attention={proposed(props.section)} open={props.open} onOpenChange={props.onOpenChange} action={<AddButton label="정보 추가" onClick={props.onAdd} expanded={props.addOpen} controls="context-create-impersonation_contact"/>}>{props.createForm}<FactList {...props}/><p className="context-section-note">계좌·연락처는 은행 내부 정보이며 화면에서 기본 마스킹됩니다.</p><HistoryHint kind="fact" items={props.section.groups.archived ?? []} busy={props.busy} onRestore={(item) => props.onReview(item, 'RESTORE')} onDelete={props.onDeleteExcluded}/></SectionShell>;

export const FraudCircumstanceSection: React.FC<FactSectionProps> = (props) => {
  const labels: Record<string, string> = { claims: '상대방 주장', demands: '상대방 요구', tactics: '압박·조작 수법' };
  return <SectionShell id="FRAUD_CIRCUMSTANCES" title="사기 정황" count={total(props.section)} attention={proposed(props.section)} open={props.open} onOpenChange={props.onOpenChange} action={<AddButton label="정황 추가" onClick={props.onAdd} expanded={props.addOpen} controls="context-create-fraud_circumstances"/>}>
    {props.createForm}
    {['claims', 'demands', 'tactics'].map((group) => <section className="context-circumstance-group" key={group}><h4>{labels[group]}</h4>{(props.section.groups[group] ?? []).length === 0 ? <p className="context-empty">등록된 내용이 없습니다.</p> : <div className="context-fact-list">{(props.section.groups[group] ?? []).map((item) => <FactRow key={item.item_id} item={item} busy={props.busy} onConfirm={() => props.onReview(item, 'CONFIRM')} onReject={() => props.onReview(item, 'REJECT')} onCorrect={() => props.onCorrect(item)} onUnconfirm={() => props.onReview(item, 'UNCONFIRM')} onInvalidate={() => props.onReview(item, 'INVALIDATE')}/>)}</div>}</section>)}
    <HistoryHint kind="fact" items={props.section.groups.archived ?? []} busy={props.busy} onRestore={(item) => props.onReview(item, 'RESTORE')} onDelete={props.onDeleteExcluded}/>
  </SectionShell>;
};

export const FactVerificationSection: React.FC<SharedProps & OpenStateProps & { onOpenVerification: (id: string) => void; onCreateVerification: () => void; onDeleteExcluded: (item: ContextPanelItemV3) => void }> = ({ section, busy, onReview, onCorrect, open, onOpenChange, onOpenVerification, onCreateVerification, onDeleteExcluded }) => {
  const needs = section.groups.needs_attention ?? [];
  const verificationItems = [...(section.groups.in_progress ?? []), ...(section.groups.confirmed ?? []), ...(section.groups.failed ?? [])].filter((item, index, items) => items.findIndex((candidate) => candidate.item_id === item.item_id) === index);
  const pending = verificationItems.filter((item) => item.status === 'PENDING');
  const progress = verificationItems.filter((item) => item.status === 'IN_PROGRESS');
  const done = verificationItems.filter((item) => item.status === 'COMPLETED');
  const stopped = verificationItems.filter((item) => !['PENDING', 'IN_PROGRESS', 'COMPLETED'].includes(item.status));
  const unmapped = section.groups.unmapped_observations ?? [];
  const openCard = (item: ContextPanelItemV3) => <VerificationCard key={item.item_id} item={item} busy={busy} onOpen={() => onOpenVerification(item.item_id)}/>;
  return <SectionShell id="FACT_VERIFICATION" title="사실·확인 현황" count={total(section)} attention={needs.length + pending.length + stopped.length} open={open} onOpenChange={onOpenChange} action={<button type="button" className="context-section-add" onClick={onCreateVerification}><Plus size={13}/>확인 요청</button>}>
    <section className="context-verification-lane"><h4><AlertCircle size={13}/>확인 필요 <b>{needs.length + pending.length}</b></h4>{needs.length > 0 && <div className="context-fact-list">{needs.map((item) => <FactRow key={item.item_id} item={item} busy={busy} onConfirm={() => onReview(item, 'CONFIRM')} onReject={() => onReview(item, 'REJECT')} onCorrect={() => onCorrect(item)} onUnconfirm={() => onReview(item, 'UNCONFIRM')} onInvalidate={() => onReview(item, 'INVALIDATE')}/>)}</div>}{pending.map(openCard)}{needs.length + pending.length === 0 && <p className="context-empty">새로 확인할 항목이 없습니다.</p>}</section>
    <section className="context-verification-lane"><h4><RotateCcw size={13}/>확인 중 <b>{progress.length}</b></h4>{progress.map(openCard)}{progress.length === 0 && <p className="context-empty">진행 중인 기관 확인이 없습니다.</p>}</section>
    <section className="context-verification-lane"><h4><CheckCircle2 size={13}/>확인 완료 <b>{done.length}</b></h4>{done.map(openCard)}{done.length === 0 && <p className="context-empty">완료된 기관 확인이 없습니다.</p>}</section>
    {stopped.length > 0 && <section className="context-verification-lane"><h4><AlertCircle size={13}/>확인 실패·중단 <b>{stopped.length}</b></h4>{stopped.map(openCard)}</section>}
    {unmapped.length > 0 && <section className="context-verification-lane"><h4><AlertCircle size={13}/>분류 대기 · 기타 관찰 <b>{unmapped.length}</b></h4><div className="context-fact-list">{unmapped.map((item) => <article className="context-domain-card verification-card is-unmapped" key={item.item_id}><header><div><strong>{item.label}</strong><small>{item.source_kind}</small></div><StatusBadge status={item.status}/></header><p>{item.display_value}</p><small>근거 턴: {String(item.value?.source_turn_id ?? '-')}</small></article>)}</div></section>}
    <HistoryHint kind="fact" items={section.groups.archived ?? []} busy={busy} onRestore={(item) => onReview(item, 'RESTORE')} onDelete={onDeleteExcluded}/>
  </SectionShell>;
};

export const StaffActionSection: React.FC<OpenStateProps & { section: ContextPanelSectionV3; busy: boolean; onWorkflow: (item: ContextPanelItemV3, action: WorkflowAction) => void; onEditTask: (item: ContextPanelItemV3) => void; onAddTask: () => void; addOpen: boolean; createForm: React.ReactNode; editForm: React.ReactNode }> = ({ section, busy, onWorkflow, onEditTask, onAddTask, addOpen, createForm, editForm, open, onOpenChange }) => {
  const suggestions = section.groups.suggestions ?? []; const active = section.groups.active ?? []; const archived = section.groups.completed ?? [];
  return <SectionShell id="STAFF_ACTIONS" title="담당자 조치 및 결과" count={suggestions.length + active.length} attention={suggestions.length} open={open} onOpenChange={onOpenChange} action={<AddButton label="업무 추가" onClick={onAddTask} expanded={addOpen} controls="context-create-staff_actions"/>}>
    {createForm}{editForm}
    {suggestions.length > 0 && <section className="context-action-lane"><h4>AI 제안 · 직원 검토 필요</h4>{suggestions.map((item) => <SuggestionCard key={item.item_id} item={item} busy={busy} onAccept={() => onWorkflow(item, 'ACCEPT')} onDismiss={() => onWorkflow(item, 'DISMISS')}/>)}</section>}
    <section className="context-action-lane"><h4>현재 업무</h4>{active.length === 0 ? <p className="context-empty">진행할 담당자 업무가 없습니다.</p> : active.map((item) => <TaskCard key={item.item_id} item={item} busy={busy} onStart={() => onWorkflow(item, 'START')} onComplete={() => onWorkflow(item, 'COMPLETE')} onBlock={() => onWorkflow(item, 'BLOCK')} onCancel={() => onWorkflow(item, 'CANCEL')} onEdit={() => onEditTask(item)}/>)}</section>
    <HistoryHint items={archived} busy={busy} onRestore={(item) => onWorkflow(item, 'RESTORE')}/>
  </SectionShell>;
};

export const CustomerShareSection: React.FC<OpenStateProps & { section: ContextPanelSectionV3; progressEditor: React.ReactNode }> = ({ progressEditor, open, onOpenChange }) => <SectionShell id="CUSTOMER_SHARE" title="고객 공유 결과" open={open} onOpenChange={onOpenChange}>
  {progressEditor}
</SectionShell>;
export const CustomerSharedTaskResults: React.FC<{ section: ContextPanelSectionV3 }> = ({ section }) => section.items.length === 0 ? null : <div className="context-fact-list">{section.items.map((item) => <FactRow key={item.item_id} item={item} busy={false} onConfirm={() => undefined} onReject={() => undefined} onCorrect={() => undefined} onUnconfirm={() => undefined} onInvalidate={() => undefined}/>)}</div>;
