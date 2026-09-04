import React, { useMemo, useState } from 'react';
import { MessageCircleQuestion, Send } from 'lucide-react';
import type { CustomerQuestion } from '../api/types';

interface Props {
  question: CustomerQuestion;
  position: number;
  total: number;
  busy: boolean;
  onAnswer: (answer: string) => Promise<void>;
}

export const CustomerQuestionCard: React.FC<Props> = ({ question, position, total, busy, onAnswer }) => {
  const [selected, setSelected] = useState('');
  const [custom, setCustom] = useState('');
  const [error, setError] = useState('');
  const options = useMemo(() => {
    const values = [...(question.options ?? [])];
    if (!values.some((value) => value.replace(/\s/g, '').includes('잘모르'))) values.push('잘 모르겠어요');
    return Array.from(new Set(values.filter(Boolean)));
  }, [question.options]);
  const answer = custom.trim() || selected;
  const submit = async () => {
    if (!answer || busy) return;
    try { setError(''); await onAnswer(answer); setSelected(''); setCustom(''); }
    catch (reason) { setError(reason instanceof Error ? reason.message : '답변을 저장하지 못했습니다.'); }
  };

  return <article className="customer-question-card">
    <div className="customer-card-kicker"><MessageCircleQuestion size={16}/><span>확인이 필요한 질문</span><b>{position}/{Math.max(total, position)}</b></div>
    <fieldset disabled={busy}>
      <legend>{question.question_text}</legend>
      {options.length > 0 && <div className="customer-question-options">{options.map((option) => <button key={option} type="button" className={selected === option ? 'selected' : ''} aria-pressed={selected === option} onClick={() => { setSelected(option); setCustom(''); }}>{option}</button>)}</div>}
      {question.allow_free_text !== false && <label className="customer-free-answer"><span>선택지에 없으면 직접 입력해 주세요.</span><input value={custom} onChange={(event) => { setCustom(event.target.value); if (event.target.value) setSelected(''); }} onKeyDown={(event) => { if (event.key === 'Enter' && !event.nativeEvent.isComposing) { event.preventDefault(); void submit(); } }} placeholder="직접 답변 입력"/></label>}
      <div className="customer-question-footer"><small>확실하지 않아도 괜찮습니다. 기억나는 범위에서 답해 주세요.</small><button type="button" onClick={() => void submit()} disabled={!answer || busy}><Send size={15}/>{busy ? '저장 중' : '답변 보내기'}</button></div>
      {error && <p className="customer-inline-error">{error} 입력한 답변은 유지했습니다.</p>}
    </fieldset>
  </article>;
};
