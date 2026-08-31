import React, { useMemo, useState } from 'react';
import { ArrowLeft, Check, Send, ShieldCheck } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import { getCase } from '../data/mock/caseData';

type Answer = '사실임' | '사실 아님' | '확인 불가';
type VerificationQuestion = { id: number; question: string };

const questionsByCase: Record<string, VerificationQuestion[]> = {
  'VP-014': [
    { id: 1, question: '해당 통화의 상대방이 검찰청 소속 직원이 맞습니까?' },
    { id: 2, question: '상대방이 안내한 사건 처리 절차가 검찰청의 공식 절차에 해당합니까?' },
    { id: 3, question: '검찰청에서 해당 사건과 관련하여 피해자에게 500만원의 송금을 요청한 사실이 있습니까?' },
    { id: 4, question: '통화에서 안내된 연락처 또는 담당자가 검찰청의 공식 연락처 및 담당자로 확인됩니까?' },
  ],
  'VP-013': [
    { id: 1, question: '해당 통화의 상대방이 은행 고객센터 소속 직원이 맞습니까?' },
    { id: 2, question: '상대방이 안내한 대출 및 계좌 확인 절차가 은행의 공식 절차에 해당합니까?' },
    { id: 3, question: '은행에서 해당 고객에게 별도 계좌로 송금하거나 수수료를 납부하라고 요청한 사실이 있습니까?' },
    { id: 4, question: '통화에 사용된 연락처와 담당자가 은행의 공식 연락처 및 직원으로 확인됩니까?' },
  ],
  'VP-012': [
    { id: 1, question: '해당 통화의 상대방이 경찰청 소속 직원이 맞습니까?' },
    { id: 2, question: '상대방이 안내한 사건 확인 절차가 경찰청의 공식 절차에 해당합니까?' },
    { id: 3, question: '경찰청에서 해당 사건과 관련하여 금전 또는 계좌 정보를 요청한 사실이 있습니까?' },
    { id: 4, question: '통화에서 안내된 연락처 또는 담당자가 경찰청의 공식 연락처 및 담당자로 확인됩니까?' },
  ],
};

export const CaseVerificationPage: React.FC = () => {
  const { caseId = 'VP-014' } = useParams();
  const item = getCase(caseId);
  const target = item.id === 'VP-014' ? '검찰청' : item.id === 'VP-013' ? '은행 고객센터' : '경찰청';
  const questions = useMemo(() => questionsByCase[item.id] ?? questionsByCase['VP-014'], [item.id]);
  const [answers, setAnswers] = useState<Record<number, Answer | undefined>>({});
  const [opinion, setOpinion] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const choose = (id: number, answer: Answer) => setAnswers((current) => ({ ...current, [id]: current[id] === answer ? undefined : answer }));
  const submit = () => { if (Object.keys(answers).length || opinion.trim()) setSubmitted(true); };

  return <AppLayout><div className="mx-auto max-w-4xl py-8 lg:ml-64">
    <Link to={`/cases/${item.id}`} className="mb-5 inline-flex items-center gap-1 text-sm font-bold text-slate-500"><ArrowLeft size={16}/> Case 상세</Link>
    <div className="mb-6"><p className="text-xs font-bold text-blue-600">CASE VERIFICATION</p><h1 className="mt-2 text-2xl font-black">사실 확인 요청</h1><div className="mt-3 flex flex-wrap items-center gap-2 text-sm"><span className="font-bold">CASE #{item.id}</span><span className="rounded-full bg-rose-50 px-2.5 py-1 text-xs font-bold text-rose-700">{item.risk}</span><span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-bold text-blue-700">{item.status}</span></div></div>
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex items-center gap-2"><ShieldCheck size={19} className="text-blue-600"/><h2 className="text-sm font-extrabold">사건 상세 브리핑</h2></div><div className="mt-4 grid gap-3 sm:grid-cols-2"><div className="rounded-xl border border-blue-100 bg-blue-50 p-4"><p className="text-xs font-bold text-blue-700">검증 요청 기관</p><p className="mt-1 text-base font-extrabold text-slate-900">{target}</p></div><div className="rounded-xl border border-slate-100 bg-slate-50 p-4"><p className="text-xs font-bold text-slate-500">검증 목적</p><p className="mt-1 text-sm font-semibold text-slate-800">상대방의 소속·절차·요청 내용이 공식 사실인지 확인</p></div></div><div className="mt-3 rounded-xl border border-slate-100 p-4"><p className="text-xs font-bold text-slate-500">통화에서 확인된 주요 내용</p><p className="mt-1 text-sm leading-6 text-slate-700">{item.verificationBrief}</p></div><div className="mt-3 rounded-xl border border-amber-100 bg-amber-50 p-4"><p className="text-xs font-bold text-amber-700">검증이 필요한 내용</p><p className="mt-1 text-sm leading-6 text-slate-700">{item.type} 사칭 여부, 안내된 공식 절차, {item.amount ? `${item.amount} 금액 요청 여부` : '금전 요청 여부'}, 연락처와 담당자 정보</p></div><p className="mt-4 rounded-xl bg-blue-50 p-3 text-xs font-semibold leading-5 text-blue-800">아래 질문을 확인하여 질문별 사실 여부를 체크해주세요.</p></section>
    <section className="mt-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-sm font-extrabold">{target} 확인 질문</h2><div className="mt-4 space-y-4">{questions.map((question) => <div key={question.id} className="rounded-xl border border-slate-100 p-4"><p className="text-sm font-bold"><span className="mr-2 text-blue-600">확인 질문 {String(question.id).padStart(2, '0')}</span>{question.question}</p><div className="mt-3 grid gap-2 sm:grid-cols-3">{(['사실임', '사실 아님', '확인 불가'] as Answer[]).map((option) => <label key={option} className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-xs font-bold ${answers[question.id] === option ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-slate-200 text-slate-600 hover:border-blue-300'}`}><input type="checkbox" checked={answers[question.id] === option} onChange={() => choose(question.id, option)} className="h-4 w-4 accent-blue-600"/>{option}</label>)}</div></div>)}</div></section>
    <section className="mt-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-sm font-extrabold">기관 추가 의견</h2><textarea value={opinion} onChange={(e) => setOpinion(e.target.value)} disabled={submitted} placeholder="추가로 전달할 의견이나 확인 내용을 입력해주세요" className="mt-3 min-h-32 w-full resize-y rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm outline-none focus:border-blue-500"/><button onClick={submit} disabled={submitted || (!Object.keys(answers).length && !opinion.trim())} className="mt-3 inline-flex items-center justify-center gap-2 rounded-xl bg-slate-900 px-5 py-3 text-sm font-bold text-white disabled:opacity-40"><Send size={15}/> {submitted ? '전송 완료' : '전송'}</button>{submitted && <p className="mt-3 rounded-xl bg-emerald-50 p-3 text-sm font-bold text-emerald-700"><Check size={16} className="mr-1 inline"/> 검증 답변이 프론트엔드 mock 상태로 저장되었습니다.</p>}</section>
  </div></AppLayout>;
};
