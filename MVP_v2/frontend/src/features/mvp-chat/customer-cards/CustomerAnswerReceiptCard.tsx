import React from 'react';
import { CheckCircle2, X } from 'lucide-react';
import type { CustomerQuestion } from '../../../services/mvpChatApi';

interface Props { question: CustomerQuestion; answer: string; onClose?: () => void; }

export const CustomerAnswerReceiptCard: React.FC<Props> = ({ question, answer, onClose }) => (
  <section className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 shadow-sm">
    <div className="flex items-start gap-2">
      <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-emerald-600"/>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-black text-emerald-800">답변이 안전하게 접수되었습니다.</p>
        <p className="mt-2 text-xs leading-5 text-slate-600">{question.question_text}</p>
        <p className="mt-2 rounded-xl bg-white px-3 py-2 text-sm font-bold text-slate-800">{answer}</p>
        <p className="mt-2 text-[11px] leading-5 text-emerald-700">은행 담당자가 확인할 정보 후보로 전달됩니다. 아직 최종 확정된 사실은 아닙니다.</p>
      </div>
      {onClose && <button type="button" onClick={onClose} className="rounded-lg p-1 text-emerald-700 hover:bg-emerald-100" aria-label="답변 접수 카드 닫기"><X size={15}/></button>}
    </div>
  </section>
);
