import React from 'react';
import { AlertCircle, CheckCircle2, Pencil, Plus, RotateCcw } from 'lucide-react';
import { FactRow, HistoryHint, MoreMenu, SectionShell, StatusBadge, SuggestionCard, TaskCard, VerificationCard } from './components';
import type { ContextPanelItemV3, ContextPanelSectionV3 } from './types';

export type WorkflowAction = 'ACCEPT' | 'DISMISS' | 'START' | 'COMPLETE' | 'BLOCK' | 'CANCEL';
type SharedProps = { section: ContextPanelSectionV3; busy: boolean; onReview: (item: ContextPanelItemV3, decision: 'CONFIRM' | 'REJECT') => void };
type OpenStateProps = { open: boolean; onOpenChange: (open: boolean) => void };

const total = (section: ContextPanelSectionV3) => section.items.length + Object.values(section.groups).reduce((sum, items) => sum + items.length, 0);
const proposed = (section: ContextPanelSectionV3) => [...section.items, ...Object.values(section.groups).flat()].filter((item) => item.status === 'PROPOSED').length;
const FactList: React.FC<SharedProps> = ({ section, busy, onReview }) => section.items.length === 0 ? <p className="context-empty">등록된 정보가 없습니다.</p> : <div className="context-fact-list">{section.items.map((item) => <FactRow key={item.item_id} item={item} busy={busy} onConfirm={() => onReview(item, 'CONFIRM')} onReject={() => onReview(item, 'REJECT')}/>)}</div>;
const AddButton: React.FC<{ label: string; onClick: () => void; expanded: boolean; controls: string }> = ({ label, onClick, expanded, controls }) => <button type="button" className="context-section-add" onClick={onClick} aria-expanded={expanded} aria-controls={controls}><Plus size={13}/>{label}</button>;

export const visibleSummaryItems = (section: ContextPanelSectionV3, risk: string, status: string) => {
  const caseMetadata = `위험도 ${risk} · 진행 상태 ${status}`;
  return section.items.filter((item) => item.source_kind !== 'DETERMINISTIC_PROJECTION' || item.display_value !== caseMetadata);
};

export const SummarySection: React.FC<{ section: ContextPanelSectionV3; caseRisk: string; caseStatus: string; projectionStatus: string; editing: boolean; onEdit: () => void; onReset: () => void; editor: React.ReactNode }> = ({ section, caseRisk, caseStatus, projectionStatus, editing, onEdit, onReset, editor }) => <section id="context-section-summary" className="context-summary-area">
  <header><div><span>현재 사건 요약</span><StatusBadge status={projectionStatus}/></div>{!editing && <div className="context-summary-actions"><button type="button" onClick={onEdit}><Pencil size={13}/>표시 요약 편집</button><MoreMenu label="요약 추가 작업"><button onClick={onReset}><RotateCcw size={13}/>자동 요약으로 복원</button></MoreMenu></div>}</header>
  {editing ? editor : <div className="context-summary-copy">{visibleSummaryItems(section, caseRisk, caseStatus).map((item) => <p key={item.item_id}>{item.display_value}</p>)}</div>}
  <footer><span>사건 정보 기준 자동 요약</span></footer>
</section>;

type FactSectionProps = SharedProps & OpenStateProps & { onAdd: () => void; addOpen: boolean; createForm: React.ReactNode };
export const ExposureSection: React.FC<FactSectionProps> = (props) => <SectionShell id="EXPOSURE" title="피해·노출" count={total(props.section)} attention={proposed(props.section)} open={props.open} onOpenChange={props.onOpenChange} action={<AddButton label="정보 추가" onClick={props.onAdd} expanded={props.addOpen} controls="context-create-exposure"/>}>{props.createForm}<FactList {...props}/></SectionShell>;
export const ImpersonationSection: React.FC<FactSectionProps> = (props) => <SectionShell id="IMPERSONATION_CONTACT" title="사칭·접촉 정보" count={total(props.section)} attention={proposed(props.section)} open={props.open} onOpenChange={props.onOpenChange} action={<AddButton label="정보 추가" onClick={props.onAdd} expanded={props.addOpen} controls="context-create-impersonation_contact"/>}>{props.createForm}<FactList {...props}/><p className="context-section-note">계좌·연락처는 은행 내부 정보이며 화면에서 기본 마스킹됩니다.</p></SectionShell>;

export const FraudCircumstanceSection: React.FC<FactSectionProps> = (props) => {
  const labels: Record<string, string> = { claims: '상대방 주장', demands: '상대방 요구', tactics: '압박·조작 수법' };
  return <SectionShell id="FRAUD_CIRCUMSTANCES" title="사기 정황" count={total(props.section)} attention={proposed(props.section)} open={props.open} onOpenChange={props.onOpenChange} action={<AddButton label="정황 추가" onClick={props.onAdd} expanded={props.addOpen} controls="context-create-fraud_circumstances"/>}>
    {props.createForm}
    {['claims', 'demands', 'tactics'].map((group) => <section className="context-circumstance-group" key={group}><h4>{labels[group]}</h4>{(props.section.groups[group] ?? []).length === 0 ? <p className="context-empty">등록된 내용이 없습니다.</p> : <div className="context-fact-list">{(props.section.groups[group] ?? []).map((item) => <FactRow key={item.item_id} item={item} busy={props.busy} onConfirm={() => props.onReview(item, 'CONFIRM')} onReject={() => props.onReview(item, 'REJECT')}/>)}</div>}</section>)}
  </SectionShell>;
};

export const FactVerificationSection: React.FC<SharedProps & OpenStateProps & { onOpenVerification: (id: string) => void; onCreateVerification: () => void }> = ({ section, busy, onReview, open, onOpenChange, onOpenVerification, onCreateVerification }) => {
  const needs = section.groups.needs_attention ?? [];
  const verificationItems = [...(section.groups.in_progress ?? []), ...(section.groups.confirmed ?? []), ...(section.groups.failed ?? [])].filter((item, index, items) => items.findIndex((candidate) => candidate.item_id === item.item_id) === index);
  const pending = verificationItems.filter((item) => item.status === 'PENDING');
  const progress = verificationItems.filter((item) => item.status === 'IN_PROGRESS');
  const done = verificationItems.filter((item) => item.status === 'COMPLETED');
  const stopped = verificationItems.filter((item) => !['PENDING', 'IN_PROGRESS', 'COMPLETED'].includes(item.status));
  const openCard = (item: ContextPanelItemV3) => <VerificationCard key={item.item_id} item={item} busy={busy} onOpen={() => onOpenVerification(item.item_id)}/>;
  return <SectionShell id="FACT_VERIFICATION" title="사실·확인 현황" count={total(section)} attention={needs.length + pending.length + stopped.length} open={open} onOpenChange={onOpenChange} action={<button type="button" className="context-section-add" onClick={onCreateVerification}><Plus size={13}/>확인 요청</button>}>
    <section className="context-verification-lane"><h4><AlertCircle size={13}/>확인 필요 <b>{needs.length + pending.length}</b></h4>{needs.length > 0 && <div className="context-fact-list">{needs.map((item) => <FactRow key={item.item_id} item={item} busy={busy} onConfirm={() => onReview(item, 'CONFIRM')} onReject={() => onReview(item, 'REJECT')}/>)}</div>}{pending.map(openCard)}{needs.length + pending.length === 0 && <p className="context-empty">새로 확인할 항목이 없습니다.</p>}</section>
    <section className="context-verification-lane"><h4><RotateCcw size={13}/>확인 중 <b>{progress.length}</b></h4>{progress.map(openCard)}{progress.length === 0 && <p className="context-empty">진행 중인 기관 확인이 없습니다.</p>}</section>
    <section className="context-verification-lane"><h4><CheckCircle2 size={13}/>확인 완료 <b>{done.length}</b></h4>{done.map(openCard)}{done.length === 0 && <p className="context-empty">완료된 기관 확인이 없습니다.</p>}</section>
    {stopped.length > 0 && <section className="context-verification-lane"><h4><AlertCircle size={13}/>확인 실패·중단 <b>{stopped.length}</b></h4>{stopped.map(openCard)}</section>}
  </SectionShell>;
};

export const StaffActionSection: React.FC<OpenStateProps & { section: ContextPanelSectionV3; busy: boolean; onWorkflow: (item: ContextPanelItemV3, action: WorkflowAction) => void; onAddTask: () => void; addOpen: boolean; createForm: React.ReactNode }> = ({ section, busy, onWorkflow, onAddTask, addOpen, createForm, open, onOpenChange }) => {
  const suggestions = section.groups.suggestions ?? []; const active = section.groups.active ?? []; const archived = section.groups.completed ?? [];
  return <SectionShell id="STAFF_ACTIONS" title="담당자 조치 및 결과" count={suggestions.length + active.length} attention={suggestions.length} open={open} onOpenChange={onOpenChange} action={<AddButton label="업무 추가" onClick={onAddTask} expanded={addOpen} controls="context-create-staff_actions"/>}>
    {createForm}
    {suggestions.length > 0 && <section className="context-action-lane"><h4>AI 제안 · 직원 검토 필요</h4>{suggestions.map((item) => <SuggestionCard key={item.item_id} item={item} busy={busy} onAccept={() => onWorkflow(item, 'ACCEPT')} onDismiss={() => onWorkflow(item, 'DISMISS')}/>)}</section>}
    <section className="context-action-lane"><h4>현재 업무</h4>{active.length === 0 ? <p className="context-empty">진행할 담당자 업무가 없습니다.</p> : active.map((item) => <TaskCard key={item.item_id} item={item} busy={busy} onStart={() => onWorkflow(item, 'START')} onComplete={() => onWorkflow(item, 'COMPLETE')} onBlock={() => onWorkflow(item, 'BLOCK')} onCancel={() => onWorkflow(item, 'CANCEL')}/>)}</section>
    <HistoryHint count={archived.length}/>
  </SectionShell>;
};

export const CustomerShareSection: React.FC<OpenStateProps & { section: ContextPanelSectionV3; progressEditor: React.ReactNode }> = ({ progressEditor, open, onOpenChange }) => <SectionShell id="CUSTOMER_SHARE" title="고객 공유 결과" open={open} onOpenChange={onOpenChange}>
  {progressEditor}
</SectionShell>;
