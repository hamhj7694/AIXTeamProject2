import React, { useMemo, useState } from 'react';
import { MessageCircleQuestion, Send } from 'lucide-react';
import type { CustomerQuestion, StructuredQuestionAnswer } from '../api/types';
import { optionLabel } from '../userText';

interface Props {
  question: CustomerQuestion;
  position: number;
  total: number;
  busy: boolean;
  onAnswer: (answer: StructuredQuestionAnswer) => Promise<void>;
}

export const CustomerQuestionCard: React.FC<Props> = ({ question, position, total, busy, onAnswer }) => {
  const [selected, setSelected] = useState<string[]>([]);
  const [custom, setCustom] = useState('');
  const [error, setError] = useState('');
  const options = useMemo(() => question.option_items ?? [], [question.option_items]);
  const hasAnswer = selected.length > 0 || custom.trim().length > 0;
  const submit = async () => {
    if (!hasAnswer || busy) return;
    try {
      setError('');
      await onAnswer({ selected_option_ids: selected, free_text: custom.trim() || null, question_version: question.question_version ?? 1 });
      setSelected([]); setCustom('');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '답변을 저장하지 못했습니다.');
    }
  };

  return <article className="customer-question-card">
    <div className="customer-card-kicker"><MessageCircleQuestion size={16}/><span>확인이 필요한 질문</span><b>{position}/{Math.max(total, position)}</b></div>
    <fieldset disabled={busy}>
      <legend>{question.question_text}</legend>
      {options.length > 0 && <div className="customer-question-options">{options.map((option) => {
        const active = selected.includes(option.option_id);
        return <button key={option.option_id} type="button" className={active ? 'selected' : ''} aria-pressed={active} onClick={() => setSelected((current) => question.allow_multi_select ? (active ? current.filter((id) => id !== option.option_id) : [...current, option.option_id]) : (active ? [] : [option.option_id]))}>{optionLabel(option.label)}</button>;
      })}</div>}
      {question.allow_free_text !== false && <label className="customer-free-answer"><span>선택지와 함께 추가 내용을 직접 입력할 수 있습니다.</span><input value={custom} onChange={(event) => setCustom(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.nativeEvent.isComposing) { event.preventDefault(); void submit(); } }} placeholder="직접 답변 입력"/></label>}
      <div className="customer-question-footer"><small>선택한 답과 직접 입력 내용이 함께 전달됩니다.</small><button type="button" onClick={() => void submit()} disabled={!hasAnswer || busy}><Send size={15}/>{busy ? '전송 중' : '답변 보내기'}</button></div>
      {error && <p className="customer-inline-error">{error} 입력한 답변은 유지됩니다.</p>}
    </fieldset>
  </article>;
};
