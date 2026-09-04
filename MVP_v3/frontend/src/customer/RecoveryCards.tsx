import React, { useState } from 'react';
import { Bot, CheckCircle2, Headphones, ShieldAlert } from 'lucide-react';
import { recoverySteps, type RecoveryStep, type RecoveryStepId } from './recovery';

export const RecoveryNavigator: React.FC<{ selected?: RecoveryStepId | null; busy: boolean; onSelect: (step: RecoveryStep) => Promise<void> }> = ({ selected, busy, onSelect }) => <section className="customer-side-card recovery-navigator">
  <div className="customer-side-title danger"><ShieldAlert size={18}/><h2>보이스피싱 피해 구제 안내</h2></div>
  <p>필요한 단계를 선택하면 채팅 기록에 상세 절차가 열립니다.</p>
  <div className="recovery-step-grid">{recoverySteps.map((step) => { const Icon = step.icon; return <button key={step.id} type="button" className={selected === step.id ? 'selected' : ''} disabled={busy} onClick={() => void onSelect(step)}><span><Icon size={16}/>{step.title}</span><small>{step.summary}</small></button>; })}</div>
  <strong><CheckCircle2 size={14}/>빠른 신고와 증빙 확보가 피해구제에 중요합니다.</strong>
</section>;

export const RecoveryDetailCard: React.FC<{ step: RecoveryStep; busy: boolean; onRequest: (kind: 'AI_ADVICE' | 'HUMAN_HANDOFF', step: RecoveryStep) => Promise<void> }> = ({ step, busy, onRequest }) => {
  const [requested, setRequested] = useState<'AI_ADVICE' | 'HUMAN_HANDOFF' | null>(null);
  const Icon = step.icon;
  const request = async (kind: 'AI_ADVICE' | 'HUMAN_HANDOFF') => { await onRequest(kind, step); setRequested(kind); };
  return <article className="recovery-detail-card">
    <header><span><Icon size={22}/></span><div><small>보이스피싱 피해구제 · 단계별 안내</small><h3>{step.title}</h3><p>{step.purpose}</p></div></header>
    <section><h4>지금 해야 할 순서</h4><ol>{step.actions.map((action, index) => <li key={action}><b>{index + 1}</b><span>{action}</span></li>)}</ol></section>
    <div className="recovery-notes"><div><b>주의사항</b><p>{step.caution}</p></div><div><b>공식 확인·연락처</b><p>{step.contact}</p></div></div>
    <footer><button type="button" disabled={busy} onClick={() => void request('AI_ADVICE')}><Bot size={15}/>내 상황에 맞는 AI 조언</button><button type="button" disabled={busy} onClick={() => void request('HUMAN_HANDOFF')}><Headphones size={15}/>은행 담당자에게 지원 요청</button></footer>
    {requested && <p className="recovery-requested"><CheckCircle2 size={15}/>{requested === 'AI_ADVICE' ? 'AI 안내 요청을 Case에 남겼습니다.' : '은행 담당자 지원 요청을 Case에 남겼습니다.'}</p>}
    <small className="recovery-disclaimer">요청을 Case에 기록하며, 지급정지·신고 등 외부 업무를 자동 실행하지 않습니다.</small>
  </article>;
};
