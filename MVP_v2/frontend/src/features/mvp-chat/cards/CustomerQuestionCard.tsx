import React, { useState } from 'react';
import { MessageCircleQuestion, Send } from 'lucide-react';
import type { CustomerQuestion } from '../../../services/mvpChatApi';

interface Props { question: CustomerQuestion; submitting?: boolean; onSubmit: (answer: string) => Promise<void>; }

export const CustomerQuestionCard: React.FC<Props> = ({ question, submitting = false, onSubmit }) => {
  const [answer, setAnswer] = useState('');
  const submit = async () => { if (!answer.trim() || submitting) return; await onSubmit(answer.trim()); setAnswer(''); };
  return <section className="rounded-2xl border border-blue-200 bg-blue-50 p-4 shadow-sm">
    <div className="flex items-center gap-2 text-blue-800"><MessageCircleQuestion size={17}/><p className="text-xs font-black">현재 확인 중인 질문 · {question.priority}</p></div>
    <p className="mt-2 text-sm font-black leading-6 text-slate-900">{question.question_text}</p>
    <p className="mt-1 text-xs leading-5 text-slate-600">기억나는 범위에서 답변해 주세요. 확실하지 않으면 “잘 모르겠어요”라고 답해도 됩니다.</p>
    {question.options?.length ? <div className="mt-3 flex flex-wrap gap-2">{question.options.map((option) => <button key={option} type="button" onClick={() => setAnswer(option)} className={`rounded-full border px-3 py-1.5 text-xs font-bold transition ${answer === option ? 'border-blue-600 bg-blue-600 text-white' : 'border-blue-200 bg-white text-blue-800 hover:border-blue-500'}`}>{option}</button>)}</div> : null}
    <div className="mt-3 flex gap-2"><input value={answer} onChange={(event) => setAnswer(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); void submit(); } }} placeholder="직접 답변 입력" className="min-w-0 flex-1 rounded-xl border border-blue-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-500"/><button type="button" onClick={() => void submit()} disabled={!answer.trim() || submitting} className="inline-flex items-center gap-1 rounded-xl bg-blue-600 px-3 py-2 text-xs font-black text-white disabled:opacity-50"><Send size={14}/>{submitting ? '저장 중' : '답변 보내기'}</button></div>
  </section>;
};
