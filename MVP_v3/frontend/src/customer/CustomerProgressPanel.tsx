import React, { useState } from 'react';
import { Check, Circle, HelpCircle } from 'lucide-react';
import type { CaseBundle, ProgressStep } from '../api/types';

export const CustomerProgressPanel: React.FC<{
  bundle: CaseBundle; recovery: boolean;
  onRequestConfirmation: (step: ProgressStep) => Promise<void>;
}> = ({ bundle, recovery, onRequestConfirmation }) => {
  const [pending, setPending] = useState<ProgressStep | null>(null);
  const [error, setError] = useState('');
  const items = bundle.customer_progress ?? [];
  const waiting = bundle.questions.filter((question) => ['ASKED', 'PENDING'].includes(question.status)).length;
  const request = async (step: ProgressStep) => {
    setPending(step); setError('');
    try { await onRequestConfirmation(step); }
    catch (reason) { setError(reason instanceof Error ? reason.message : '확인 요청을 저장하지 못했습니다. 다시 시도해 주세요.'); }
    finally { setPending(null); }
  };
  return <section className="customer-side-card customer-progress">
    <div className="customer-side-title"><h2>현재 진행 상황</h2><span>{recovery ? '피해 대응' : '상황 확인'}</span></div>
    <p className="customer-progress-summary">이 상담에 기록된 처리 결과입니다. 안내를 열거나 채팅을 보내는 것만으로 신청·신고가 접수되지는 않습니다.</p>
    <div className="public-progress-list">{items.map((item) => <article key={item.step} className={item.status === 'COMPLETED' ? 'is-confirmed' : ''}>
      <header>{item.status === 'COMPLETED' ? <Check size={15}/> : <Circle size={12}/>}<strong>{item.label}</strong></header>
      <b>{item.status_label}</b><p>{item.summary}</p>
      {item.next_action && <p className="progress-next"><strong>지금 할 일</strong> {item.next_action}</p>}
      {item.reference && <small>확인 근거: {item.reference}</small>}
      {item.confirmed_at && <small>확인 시각: {new Date(item.confirmed_at).toLocaleString('ko-KR')}</small>}
      {item.confirmation_requested ? <><button type="button" disabled><Check size={13}/> 담당자 확인 요청됨</button><p role="status">고객·은행 채팅에 요청이 기록됐습니다. 담당자 답변 대기 중입니다.</p></> :
        <button type="button" disabled={pending !== null} onClick={() => void request(item.step)}>{pending === item.step ? '요청 저장 중…' : '담당자에게 확인 요청'}</button>}
    </article>)}</div>
    {!items.length && <p className="customer-progress-summary">처리 결과를 아직 불러오지 못했습니다. 완료 여부는 확인되지 않았습니다.</p>}
    {error && <p role="alert" className="progress-error">{error}</p>}
    {waiting > 0 && <p className="customer-progress-summary">답변이 필요한 질문 {waiting}건</p>}
  </section>;
};

export const CustomerSafetyGuide: React.FC = () => <section className="customer-side-card customer-safety-guide"><div className="customer-side-title"><HelpCircle size={17}/><h2>안전 상담 안내</h2></div><p>은행 담당자나 안전 상담 AI의 질문에는 기억나는 범위에서 답해 주세요. 확실하지 않다면 “잘 모르겠어요”를 선택해도 됩니다.</p></section>;
