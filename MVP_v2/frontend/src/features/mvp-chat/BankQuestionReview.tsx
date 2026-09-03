import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ClipboardCheck, Clock3, MessageCircleQuestion, X } from 'lucide-react';
import { mvpChatApi, type CustomerQuestion } from '../../services/mvpChatApi';
import { useCaseSyncRefresh } from '../case-sync/useCaseSyncRefresh';

const statusLabel: Record<CustomerQuestion['status'], string> = {
  PENDING: '질문 대기', ASKED: '답변 대기', ANSWERED: '답변 완료', SKIPPED: '건너뜀',
};

export const BankQuestionReview: React.FC<{ caseId: string }> = ({ caseId }) => {
  const [open, setOpen] = useState(false);
  const [questions, setQuestions] = useState<CustomerQuestion[]>([]);
  const [error, setError] = useState('');
  const load = useCallback(() => mvpChatApi.listCustomerQuestions(caseId, 'bank').then(setQuestions).catch(() => setError('질문·답변 정보를 불러오지 못했습니다.')), [caseId]);
  useCaseSyncRefresh(caseId, load);
  useEffect(() => { void load(); const timer = window.setInterval(load, 3000); return () => window.clearInterval(timer); }, [load]);
  const answeredCount = useMemo(() => questions.filter((item) => item.status === 'ANSWERED').length, [questions]);

  return <>
    <button type="button" onClick={() => setOpen(true)} className="fixed bottom-20 right-[310px] z-40 hidden items-center gap-2 rounded-full bg-slate-900 px-4 py-3 text-sm font-black text-white shadow-lg hover:bg-slate-800 sm:inline-flex lg:bottom-6">
      <ClipboardCheck size={17}/>확인 및 확인중 정보
      {questions.length > 0 && <span className="rounded-full bg-blue-600 px-1.5 py-0.5 text-[10px] text-white">{answeredCount}/{questions.length}</span>}
    </button>
    {open && <div className="fixed inset-0 z-50 bg-slate-950/30" onMouseDown={(event) => { if (event.target === event.currentTarget) setOpen(false); }}>
      <aside className="absolute bottom-0 right-0 flex h-[min(760px,92vh)] w-full max-w-lg flex-col rounded-t-3xl bg-white shadow-2xl sm:bottom-4 sm:right-4 sm:rounded-3xl">
        <header className="flex items-center gap-3 border-b p-4"><div className="grid h-9 w-9 place-items-center rounded-xl bg-blue-100 text-blue-700"><ClipboardCheck size={18}/></div><div><h2 className="text-sm font-black">확인 및 확인중 정보</h2><p className="text-[11px] text-slate-500">은행이 요청한 질문과 고객 답변을 한곳에서 확인합니다.</p></div><button type="button" onClick={() => setOpen(false)} className="ml-auto rounded-lg p-2 hover:bg-slate-100" aria-label="확인 정보 닫기"><X size={18}/></button></header>
        <div className="border-b bg-slate-50 px-4 py-3 text-xs font-bold text-slate-600">전체 {questions.length}건 · 답변 완료 {answeredCount}건 · 확인 중 {questions.length - answeredCount}건</div>
        {error && <p className="mx-4 mt-3 rounded-xl bg-rose-50 p-3 text-xs font-bold text-rose-700">{error}</p>}
        <div className="flex-1 space-y-3 overflow-y-auto p-4">{questions.length ? questions.map((question) => <article key={question.question_id} className="rounded-2xl border border-slate-200 p-4 shadow-sm">
          <div className="flex items-center justify-between gap-2"><span className="inline-flex items-center gap-1 text-[11px] font-black text-blue-700"><MessageCircleQuestion size={14}/>질문 {question.sequence}</span><span className={`rounded-full px-2 py-1 text-[10px] font-black ${question.status === 'ANSWERED' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>{statusLabel[question.status]}</span></div>
          <p className="mt-2 text-sm font-bold leading-6 text-slate-800">{question.question_text}</p>
          {question.answer_text ? <div className="mt-3 rounded-xl bg-emerald-50 p-3"><p className="text-[10px] font-black text-emerald-700">고객 답변</p><p className="mt-1 text-sm font-bold text-slate-900">{question.answer_text}</p></div> : <p className="mt-3 inline-flex items-center gap-1 rounded-xl bg-amber-50 px-3 py-2 text-xs font-bold text-amber-700"><Clock3 size={13}/>고객 답변을 기다리고 있습니다.</p>}
        </article>) : <p className="rounded-2xl border border-dashed p-8 text-center text-sm text-slate-500">아직 요청한 질문이 없습니다.</p>}</div>
      </aside>
    </div>}
  </>;
};
