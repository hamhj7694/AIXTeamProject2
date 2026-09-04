import React, { useState } from 'react';
import { MessageCircleQuestion, Send, Sparkles } from 'lucide-react';
import type { CustomerQuestion } from '../../../services/mvpChatApi';

interface Props { question: CustomerQuestion; submitting?: boolean; onSubmit: (answer: string) => Promise<void>; }

export const CustomerQuestionCard: React.FC<Props> = ({ question, submitting = false, onSubmit }) => {
  const [selectedOption, setSelectedOption] = useState('');
  const [customAnswer, setCustomAnswer] = useState('');
  const answer = customAnswer.trim() || selectedOption;
  const allowFreeText = question.allow_free_text !== false;
  const submit = async () => { if (!answer || submitting) return; await onSubmit(answer); setSelectedOption(''); setCustomAnswer(''); };
  return <section className="rounded-2xl border border-blue-200 bg-blue-50 p-4 shadow-sm">
    <div className="flex items-center gap-2 text-blue-800">{question.source === 'CUSTOMER_AGENT' ? <Sparkles size={17}/> : <MessageCircleQuestion size={17}/>}<p className="text-xs font-black">{question.source === 'CUSTOMER_AGENT' ? 'AI가 먼저 확인하는 안전 질문' : '은행 담당자 확인 질문'} {question.sequence ? `· ${question.sequence}번` : ''}</p></div>
    <p className="mt-3 text-base font-black leading-7 tracking-tight text-slate-950 sm:text-lg">{question.question_text}</p>
    {question.options?.length ? <div className="mt-3 grid gap-2 sm:grid-cols-2">{question.options.map((option) => <button key={option} type="button" aria-pressed={selectedOption === option} onClick={() => { setSelectedOption(option); setCustomAnswer(''); }} className={`rounded-xl border px-3 py-2.5 text-left text-xs font-bold transition ${selectedOption === option ? 'border-blue-600 bg-blue-600 text-white ring-2 ring-blue-200' : 'border-blue-200 bg-white text-blue-800 hover:border-blue-500'}`}>{option}</button>)}</div> : null}
    {allowFreeText && <label className="mt-3 block text-[11px] font-bold text-slate-600">선택지에 없거나 자세히 설명하려면 직접 입력하세요.<input value={customAnswer} onChange={(event) => { setCustomAnswer(event.target.value); if (event.target.value) setSelectedOption(''); }} onKeyDown={(event) => { if (event.key === 'Enter' && !event.nativeEvent.isComposing) { event.preventDefault(); void submit(); } }} placeholder="직접 답변 입력" className="mt-1.5 w-full rounded-xl border border-blue-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-blue-500"/></label>}
    <div className="mt-3 flex items-center justify-between gap-3"><p className="text-[11px] leading-5 text-slate-500">확실하지 않으면 “잘 모르겠어요”를 선택하거나 직접 입력해 주세요.</p><button type="button" onClick={() => void submit()} disabled={!answer || submitting} className="inline-flex shrink-0 items-center gap-1 rounded-xl bg-blue-600 px-3 py-2 text-xs font-black text-white disabled:opacity-50"><Send size={14}/>{submitting ? '저장 중' : '답변 보내기'}</button></div>
  </section>;
};
