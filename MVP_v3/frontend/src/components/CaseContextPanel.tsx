import React from 'react';
import { AlertTriangle, Check, ChevronRight, HelpCircle, ShieldCheck, X } from 'lucide-react';
import type { CaseBundle, CaseFact, CaseSupportSnapshot, StoredCase, VerificationTask } from '../api/types';
import {
  activeVerifications, caseClaims, caseDemands, confirmedFacts, fieldLabel, proposedFacts,
  recommendedSteps, riskLabel, riskReasons, riskTone, verificationStatusLabel,
} from '../presentation';

interface Props {
  caseItem: StoredCase;
  bundle: CaseBundle;
  support: CaseSupportSnapshot | null;
  facts: CaseFact[];
  open: boolean;
  onClose: () => void;
  onEditVerification: (task: VerificationTask) => void;
  onCreateAction: () => void;
}

const EmptyLine = ({ children }: { children: React.ReactNode }) => <p className="context-empty">{children}</p>;

export const CaseContextPanel: React.FC<Props> = ({ caseItem, bundle, support, facts, open, onClose, onEditVerification, onCreateAction }) => {
  const claims = caseClaims(caseItem);
  const demands = caseDemands(caseItem);
  const reasons = riskReasons(caseItem);
  const confirmed = confirmedFacts(facts);
  const proposed = proposedFacts(facts);
  const unresolved = support?.unresolved_items ?? [];
  const recommended = [...(support?.case_brief?.next_checks ?? []), ...recommendedSteps(caseItem)].filter((value, index, list) => value && list.indexOf(value) === index).slice(0, 5);
  const activeTasks = activeVerifications(bundle.verification_tasks ?? []);

  return <aside className={`context-panel ${open ? 'is-open' : ''}`} aria-label="사건 맥락">
    <div className="context-header"><div><p className="eyebrow">CASE CONTEXT</p><h2>사건 맥락</h2></div><button className="icon-button context-close" onClick={onClose} aria-label="사건 맥락 닫기"><X size={18}/></button></div>
    <div className="context-scroll">
      <section className={`risk-summary ${riskTone(caseItem.risk)}`}>
        <div><span>현재 위험</span><strong>{riskLabel(caseItem.risk)}</strong></div><b>{Math.round(caseItem.risk_score)}</b>
      </section>
      <section className="context-section"><h3><AlertTriangle size={15}/>왜 위험한가</h3>{reasons.length ? <ul>{reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul> : <EmptyLine>구조화된 위험 근거가 아직 없습니다.</EmptyLine>}</section>
      <section className="context-section"><h3>범죄자 주장</h3>{claims.length ? <ul className="quote-list">{claims.map((claim) => <li key={claim}>“{claim}”</li>)}</ul> : <EmptyLine>확인된 주장이 없습니다.</EmptyLine>}</section>
      <section className="context-section"><h3>범죄자 요구</h3>{demands.length ? <ul className="quote-list demand">{demands.map((demand) => <li key={demand}>“{demand}”</li>)}</ul> : <EmptyLine>구조화된 요구가 없습니다.</EmptyLine>}</section>
      <section className="context-section"><h3><Check size={15}/>확인된 사실</h3>{confirmed.length ? <ul className="fact-list">{confirmed.map((fact) => <li key={fact.fact_id}><span>{fieldLabel(fact.field)}</span><b>{fact.value}</b></li>)}</ul> : <EmptyLine>담당자가 확정한 사실이 없습니다.</EmptyLine>}</section>
      <section className="context-section"><h3><HelpCircle size={15}/>확인 필요</h3>{unresolved.length || proposed.length ? <ul>{unresolved.map((item) => <li key={`${item.target_field}-${item.description}`}><b>{item.priority}</b> {item.description}</li>)}{proposed.map((fact) => <li key={fact.fact_id}>{fieldLabel(fact.field)}: 고객 답변 “{fact.value}” 확인 필요</li>)}</ul> : <EmptyLine>현재 추가 확인 항목이 없습니다.</EmptyLine>}</section>
      <section className="context-section"><h3>기관 확인</h3>{bundle.verification_tasks?.length ? <div className="verification-summary-list">{bundle.verification_tasks.map((task) => <button key={task.verification_task_id} onClick={() => onEditVerification(task)}><span><b>{task.target}</b><small>{verificationStatusLabel(task.status)}</small></span><ChevronRight size={15}/></button>)}</div> : <EmptyLine>등록된 기관 확인이 없습니다.</EmptyLine>}{activeTasks.length > 0 && <p className="context-note">확인 중인 업무 {activeTasks.length}건</p>}</section>
      <section className="context-section recommendations"><h3><ShieldCheck size={15}/>권장 조치</h3>{recommended.length ? <ol>{recommended.map((step) => <li key={step}>{step}</li>)}</ol> : <EmptyLine>AI 권장 조치를 준비 중입니다.</EmptyLine>}<button className="primary-action full" onClick={onCreateAction}>대응 업무 기록</button></section>
      {caseItem.mode === 'RECOVERY' && <section className="recovery-context"><strong>피해구제 모드</strong><p>추가 송금을 중단하고 지급정지 검토, 112 신고, 증빙 확보와 피해구제 신청을 순서대로 지원하세요.</p></section>}
    </div>
  </aside>;
};
