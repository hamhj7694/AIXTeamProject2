import React, { useState } from 'react';
import { Check, CheckCircle2, Circle, CircleDot, Clock3, HelpCircle, Minus } from 'lucide-react';
import type { CaseBundle, CustomerProgressItem, ProgressStatus, ProgressStep } from '../api/types';

const statusLabels: Record<ProgressStatus, string> = {
  UNKNOWN: '확인 전', IN_PROGRESS: '처리 중', SUBMITTED: '제출 확인 · 결과 대기',
  COMPLETED: '완료', NOT_APPLICABLE: '해당 없음',
};

const StatusIcon: React.FC<{ status: ProgressStatus }> = ({ status }) => {
  if (status === 'COMPLETED') return <CheckCircle2 size={18} aria-hidden="true"/>;
  if (status === 'IN_PROGRESS') return <CircleDot size={18} aria-hidden="true"/>;
  if (status === 'SUBMITTED') return <Clock3 size={18} aria-hidden="true"/>;
  if (status === 'NOT_APPLICABLE') return <Minus size={18} aria-hidden="true"/>;
  return <Circle size={18} aria-hidden="true"/>;
};

const meaningfulSummary = (item: CustomerProgressItem) => item.revision > 0 && Boolean(item.summary.trim());

export const CustomerProgressPanel: React.FC<{
  bundle: CaseBundle; recovery: boolean;
  onRequestConfirmation: (step: ProgressStep) => Promise<void>;
}> = ({ bundle, onRequestConfirmation }) => {
  const [pending, setPending] = useState<ProgressStep | null>(null);
  const [error, setError] = useState<{ step: ProgressStep; message: string } | null>(null);
  const items = bundle.customer_progress ?? [];
  const waiting = bundle.questions.filter((question) => ['ASKED', 'PENDING'].includes(question.status)).length;
  const actionItems = items.filter((item) => ['IN_PROGRESS', 'SUBMITTED'].includes(item.status) && item.next_action.trim());
  const primaryAction = actionItems.length === 1 ? actionItems[0] : null;
  const request = async (step: ProgressStep) => {
    setPending(step); setError(null);
    try { await onRequestConfirmation(step); }
    catch (reason) { setError({ step, message: reason instanceof Error ? reason.message : '확인 요청을 저장하지 못했습니다. 다시 시도해 주세요.' }); }
    finally { setPending(null); }
  };
  return <section className="customer-side-card customer-progress">
    <div className="customer-side-title"><h2>현재 진행 상황</h2>{waiting > 0 && <span className="customer-progress-questions">답변할 질문 {waiting}개</span>}</div>
    {items.length > 0 ? <ul className="customer-progress-list">{items.map((item) => {
      const active = item.status === 'IN_PROGRESS' || item.status === 'SUBMITTED';
      const canRequestConfirmation = !['COMPLETED', 'NOT_APPLICABLE'].includes(item.status);
      return <li key={item.step} className={`customer-progress-step is-${item.status.toLowerCase()} ${active ? 'is-active' : ''}`}>
        <div className="customer-progress-row"><span className="customer-progress-icon"><StatusIcon status={item.status}/></span><strong>{item.label}</strong><span className="customer-progress-status">{statusLabels[item.status]}</span></div>
        <details><summary aria-label={`${item.label} 단계 상세 정보`}>상세 보기</summary><div className="customer-progress-detail">
          {meaningfulSummary(item) && <p><strong>처리 내용</strong>{item.summary}</p>}
          {item.next_action && <p><strong>고객이 할 일</strong>{item.next_action}</p>}
          {item.reference && <p><strong>확인 근거</strong>{item.reference}</p>}
          {item.confirmed_at && <p><strong>확인 시각</strong>{new Date(item.confirmed_at).toLocaleString('ko-KR')}</p>}
          {item.confirmation_requested ? <p className="customer-progress-requested" role="status"><Check size={14}/>담당자 확인 요청됨 · 답변 대기 중</p> : canRequestConfirmation && <button type="button" className="customer-progress-confirm" aria-label={`${item.label} 단계 담당자 확인 요청`} disabled={pending !== null} onClick={() => void request(item.step)}>{pending === item.step ? '요청 저장 중…' : '담당자에게 확인 요청'}</button>}
          {error?.step === item.step && <p role="alert" className="progress-error">{error.message}</p>}
        </div></details>
      </li>;
    })}</ul> : <p className="customer-progress-empty">아직 확인된 진행 정보가 없습니다. 완료 여부는 확인되지 않았습니다.</p>}
    {primaryAction && <div className="customer-progress-primary-action"><strong>지금 할 일</strong><p>{primaryAction.next_action}</p></div>}
    <p className="customer-progress-disclaimer">안내나 채팅만으로 신청·신고가 접수되지는 않습니다.</p>
  </section>;
};

export const CustomerSafetyGuide: React.FC = () => <section className="customer-side-card customer-safety-guide"><div className="customer-side-title"><HelpCircle size={17}/><h2>안전 상담 안내</h2></div><p>은행 담당자나 안전 상담 AI의 질문에는 기억나는 범위에서 답해 주세요. 확실하지 않다면 “잘 모르겠어요”를 선택해도 됩니다.</p></section>;
