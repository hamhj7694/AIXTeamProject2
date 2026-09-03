import React, { useEffect, useState } from 'react';
import { CheckCircle2, MessageCircleQuestion } from 'lucide-react';
import { mvpChatApi, type CustomerQuestion } from '../../../services/mvpChatApi';

export const BankQuestionAnswerFeed: React.FC<{ caseId: string }> = ({ caseId }) => {
  const [questions, setQuestions] = useState<CustomerQuestion[]>([]);

  useEffect(() => {
    let active = true;
    const load = () => mvpChatApi.listCustomerQuestions(caseId, 'bank')
      .then((items) => { if (active) setQuestions(items); })
      .catch(() => undefined);
    void load();
    const timer = window.setInterval(load, 3000);
    return () => { active = false; window.clearInterval(timer); };
  }, [caseId]);

  const answered = questions.filter((question) => question.status === 'ANSWERED' && question.answer_text);
  if (!answered.length) return null;

  return <div className="space-y-2">
    {answered.map((question) => <article key={question.question_id} className="rounded-xl border border-emerald-400/30 bg-emerald-950/30 px-3 py-2.5 text-slate-100">
      <div className="flex items-center gap-2 text-[10px] font-black text-emerald-300"><CheckCircle2 size={13}/>고객 답변 접수</div>
      <div className="mt-1.5 grid gap-1 text-xs sm:grid-cols-[18px_1fr]"><MessageCircleQuestion size={13} className="mt-0.5 text-slate-500"/><p className="text-slate-400">{question.question_text}</p></div>
      <p className="mt-1.5 rounded-lg bg-slate-900/70 px-3 py-2 text-sm font-bold text-white">{question.answer_text}</p>
      <p className="mt-1 text-[10px] text-slate-500">CaseFact 후보로 전달됨 · 담당자 확인 필요</p>
    </article>)}
  </div>;
};
