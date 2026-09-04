import React from 'react';
import { Check, Circle, HelpCircle, Loader2 } from 'lucide-react';
import type { CaseBundle } from '../api/types';
import type { RecoveryStepId } from './recovery';

const normalLabels = ['상황 접수', '필요 정보 확인', '기관 확인', '보호 조치', '처리 완료'];
const recoveryLabels = ['피해 상황 접수', '추가 송금·접촉 중단', '거래내역·대화 증빙 확보', '은행 지급정지·신고 확인', '피해구제 신청'];
const recoveryIndex: Record<RecoveryStepId, number> = { CONTACT: 1, EVIDENCE: 2, REPORT: 3, RELIEF: 4 };

const normalStage = (status: string) => {
  if (status === 'CLOSED') return 4;
  if (status === 'IN_PROGRESS') return 3;
  if (status === 'VERIFYING') return 2;
  return 1;
};

export const CustomerProgressPanel: React.FC<{ bundle: CaseBundle; recovery: boolean; selectedStep?: RecoveryStepId | null }> = ({ bundle, recovery, selectedStep }) => {
  const status = String(bundle.case.status ?? 'TRIAGE');
  const stage = recovery ? (selectedStep ? recoveryIndex[selectedStep] : 1) : normalStage(status);
  const labels = recovery ? recoveryLabels : normalLabels;
  const answered = bundle.questions.filter((question) => question.status === 'ANSWERED').length;
  const waiting = bundle.questions.filter((question) => question.status === 'ASKED' || question.status === 'PENDING').length;
  const verificationCount = bundle.customer_verification_results?.length ?? 0;
  const go = (index: number) => {
    if (!recovery && index === 1) document.getElementById('active-customer-question')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    if (recovery && selectedStep) document.querySelector(`[data-recovery-step="${selectedStep}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };
  return <section className="customer-side-card customer-progress">
    <div className="customer-side-title"><h2>현재 진행 상황</h2><span>{recovery ? '피해구제' : status === 'CLOSED' ? '상담 완료' : '안전 확인'}</span></div>
    <div className="customer-progress-steps">{labels.map((label, index) => { const done = index < stage || (stage === 4 && index === 4); const active = index === stage && !done; return <button type="button" key={label} onClick={() => go(index)} className={active ? 'active' : done ? 'done' : ''}><i>{done ? <Check size={13}/> : active ? <Loader2 size={13} className="spin"/> : <Circle size={10}/>}</i><span>{label}</span></button>; })}</div>
    <p className="customer-progress-summary">{recovery ? '선택한 피해구제 절차와 은행 처리 결과에 따라 단계가 갱신됩니다.' : '고객 답변과 은행 담당자의 확인 결과에 따라 단계가 갱신됩니다.'}<small>답변 완료 {answered}건 · 확인 대기 {waiting}건{verificationCount ? ` · 공개 확인 결과 ${verificationCount}건` : ''}</small></p>
  </section>;
};

export const CustomerSafetyGuide: React.FC = () => <section className="customer-side-card customer-safety-guide"><div className="customer-side-title"><HelpCircle size={17}/><h2>안전 상담 안내</h2></div><p>은행 담당자나 안전 상담 AI의 질문에는 기억나는 범위에서 답해 주세요. 확실하지 않다면 “잘 모르겠어요”를 선택해도 됩니다.</p></section>;
