import React, { useState } from 'react';
import { AlertTriangle, Check, ChevronRight, HelpCircle, Plus, RotateCcw, ShieldCheck } from 'lucide-react';
import type { CaseAction, CaseBundle, CaseFact, CaseSupportSnapshot, StoredCase, VerificationTask } from '../api/types';
import {
  activeVerifications, caseClaims, caseDemands, confirmedFacts, fieldLabel,
  riskReasons, verificationStatusLabel,
} from '../presentation';

interface Props {
  caseItem: StoredCase;
  bundle: CaseBundle;
  facts: CaseFact[];
  support: CaseSupportSnapshot | null;
  open: boolean;
  onEditVerification: (task: VerificationTask) => void;
  onCreateJudgment: (note: string) => Promise<boolean>;
  onToggleChecklist: (action: CaseAction, status: 'REQUESTED' | 'COMPLETED') => Promise<void>;
  checklistBusy: boolean;
}

const EmptyLine = ({ children }: { children: React.ReactNode }) => <p className="context-empty">{children}</p>;

const isAiChecklist = (action: CaseAction) => action.action_type.startsWith('AI_CHECKLIST:');
const isStaffJudgment = (action: CaseAction) => action.action_type === 'STAFF_JUDGMENT';
const checklistPriority = (action: CaseAction) => action.action_type.split(':')[1] || 'AI';

export const CaseContextPanel: React.FC<Props> = ({ caseItem, bundle, facts, support, open, onEditVerification, onCreateJudgment, onToggleChecklist, checklistBusy }) => {
  const [judgment, setJudgment] = useState('');
  const liveContext = support?.available ? support.case_context : null;
  const claims = liveContext?.offender_claims ?? caseClaims(caseItem);
  const demands = liveContext?.offender_demands ?? caseDemands(caseItem);
  const reasons = liveContext?.key_signals ?? riskReasons(caseItem);
  const confirmed = confirmedFacts(facts);
  const checklistItems = (bundle.recent_actions ?? []).filter((action) => isAiChecklist(action) || isStaffJudgment(action));
  const openAiChecks = checklistItems.filter((action) => isAiChecklist(action) && action.status !== 'COMPLETED');
  const openJudgments = checklistItems.filter((action) => isStaffJudgment(action) && action.status !== 'COMPLETED');
  const completedItems = checklistItems.filter((action) => action.status === 'COMPLETED');
  const activeTasks = activeVerifications(bundle.verification_tasks ?? []);
  const submitJudgment = async (event: React.FormEvent) => {
    event.preventDefault();
    const value = judgment.trim();
    if (!value || checklistBusy) return;
    if (await onCreateJudgment(value)) setJudgment('');
  };

  return <aside className={`context-panel ${open ? 'is-open' : ''}`} aria-label="사건 맥락">
    <div className="context-header"><div><p className="eyebrow">CASE CONTEXT</p><h2>사건 맥락</h2>{liveContext && <small>최신 Shared Case 반영</small>}</div></div>
    <div className="context-scroll">
      <section className="context-section"><h3><AlertTriangle size={15}/>탐지된 핵심 신호</h3>{reasons.length ? <ul>{reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul> : <EmptyLine>구조화된 핵심 신호가 아직 없습니다.</EmptyLine>}</section>
      <section className="context-section"><h3>범죄자 주장</h3>{claims.length ? <ul className="quote-list">{claims.map((claim) => <li key={claim}>“{claim}”</li>)}</ul> : <EmptyLine>확인된 주장이 없습니다.</EmptyLine>}</section>
      <section className="context-section"><h3>범죄자 요구</h3>{demands.length ? <ul className="quote-list demand">{demands.map((demand) => <li key={demand}>“{demand}”</li>)}</ul> : <EmptyLine>구조화된 요구가 없습니다.</EmptyLine>}</section>
      <section className="context-section"><h3><Check size={15}/>확인된 사실</h3>{confirmed.length ? <ul className="fact-list">{confirmed.map((fact) => <li key={fact.fact_id}><span>{fieldLabel(fact.field)}</span><b>{fact.value}</b></li>)}</ul> : <EmptyLine>담당자가 확정한 사실이 없습니다.</EmptyLine>}</section>
      <section className="context-section checklist-section"><h3><HelpCircle size={15}/>AI 추가 확인 체크리스트</h3><p className="context-section-description">AI가 현재 DB와 기존 기록을 검토한 뒤 아직 확인되지 않은 사항만 누적합니다.</p>{openAiChecks.length ? <div className="work-check-list">
        {openAiChecks.map((action) => <label key={action.action_id} className="work-check-item ai"><input type="checkbox" disabled={checklistBusy} onChange={() => void onToggleChecklist(action, 'COMPLETED')}/><span><b>{action.note}</b><small>AI 추천 · {checklistPriority(action)}</small></span></label>)}
      </div> : <EmptyLine>현재 남아 있는 AI 추가 확인 항목이 없습니다.</EmptyLine>}</section>
      <section className="context-section"><h3>기관 확인</h3>{bundle.verification_tasks?.length ? <div className="verification-summary-list">{bundle.verification_tasks.map((task) => <button key={task.verification_task_id} onClick={() => onEditVerification(task)}><span><b>{task.target}</b><small>{verificationStatusLabel(task.status)}</small></span><ChevronRight size={15}/></button>)}</div> : <EmptyLine>등록된 기관 확인이 없습니다.</EmptyLine>}{activeTasks.length > 0 && <p className="context-note">확인 중인 업무 {activeTasks.length}건</p>}</section>
      <section className="context-section checklist-section"><h3><ShieldCheck size={15}/>담당자 판단·조치 기록</h3><p className="context-section-description">은행 직원이 사건을 검토한 뒤 내린 판단이나 실행할 조치를 직접 기록합니다.</p><form className="judgment-entry" onSubmit={(event) => void submitJudgment(event)}><textarea value={judgment} onChange={(event) => setJudgment(event.target.value)} placeholder="예: 추가 송금을 중단하도록 안내하고 지급정지 가능 여부를 확인한다." maxLength={10000}/><button type="submit" disabled={!judgment.trim() || checklistBusy}><Plus size={13}/>추가</button></form>{openJudgments.length ? <div className="work-check-list">
        {openJudgments.map((action) => <label key={action.action_id} className="work-check-item staff"><input type="checkbox" disabled={checklistBusy} onChange={() => void onToggleChecklist(action, 'COMPLETED')}/><span><b>{action.note}</b><small>은행 직원 입력</small></span></label>)}
      </div> : <EmptyLine>현재 진행 중인 담당자 판단·조치가 없습니다.</EmptyLine>}</section>
      <details className="completed-checklist"><summary>완료·숨김 항목 <b>{completedItems.length}</b>건</summary>{completedItems.length ? <div className="work-check-list completed">
        {completedItems.map((action) => <label key={action.action_id} className="work-check-item"><input type="checkbox" checked disabled={checklistBusy} onChange={() => void onToggleChecklist(action, 'REQUESTED')}/><span><b>{action.note}</b><small>{isAiChecklist(action) ? `AI 추천 · ${checklistPriority(action)}` : '은행 직원 입력'}</small></span><RotateCcw size={13}/></label>)}
      </div> : <EmptyLine>완료 처리된 항목이 없습니다.</EmptyLine>}</details>
      {caseItem.mode === 'RECOVERY' && <section className="recovery-context"><strong>피해구제 모드</strong><p>추가 송금을 중단하고 지급정지 검토, 112 신고, 증빙 확보와 피해구제 신청을 순서대로 지원하세요.</p></section>}
    </div>
  </aside>;
};
