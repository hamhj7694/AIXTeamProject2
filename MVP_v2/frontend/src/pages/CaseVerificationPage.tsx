import React, { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, Send, ShieldCheck } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import { CaseContextBar } from '../components/case/CaseContextBar';
import { caseApi, type CaseDetail } from '../services/caseApi';
import { caseWorkflowApi, VerificationTask } from '../services/caseWorkflowApi';
import { useCaseEventRefresh } from '../features/case-state/useCaseEventRefresh';

type Answer = '사실임' | '사실 아님' | '확인 불가';
export const CaseVerificationPage: React.FC = () => {
  const { caseId = '' } = useParams();
  const [item, setItem] = useState<CaseDetail | null>(null);
  const [tasks, setTasks] = useState<VerificationTask[]>([]);
  const [answers, setAnswers] = useState<Record<number, Answer | undefined>>({});
  const [opinion, setOpinion] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [eventCursor, setEventCursor] = useState<string | null>(null);
  const [refreshNonce, setRefreshNonce] = useState(0);

  const load = async () => {
    const [caseDetail, bundle] = await Promise.all([caseApi.get(caseId), caseWorkflowApi.getBundle(caseId, 'entry')]);
    setItem(caseDetail);
    setTasks(bundle.verification_tasks);
    setEventCursor(bundle.cursor);
  };

  useEffect(() => {
    let active = true;
    setError(''); setItem(null);
    load().catch((reason) => { if (active) setError(reason instanceof Error ? reason.message : 'Case 데이터를 불러오지 못했습니다.'); });
    return () => { active = false; };
  }, [caseId, refreshNonce]);

  useCaseEventRefresh({
    caseId,
    cursor: eventCursor,
    onEvents: (events) => {
      setEventCursor(String(events[events.length - 1].event_id));
      setRefreshNonce((current) => current + 1);
    },
  });

  const questions = useMemo(() => item?.verificationQuestions ?? [], [item]);
  const choose = (id: number, answer: Answer) => setAnswers((current) => ({ ...current, [id]: current[id] === answer ? undefined : answer }));
  const submit = async () => {
    if (!item || (!Object.keys(answers).length && !opinion.trim())) return;
    const claim = questions.filter((question) => answers[question.id]).map((question) => `${question.question}: ${answers[question.id]}`).join('\n') || opinion.trim();
    setSubmitting(true); setError('');
    try {
      await caseWorkflowApi.createVerification(item.id, claim, item.type || '기관 확인');
      setAnswers({}); setOpinion(''); await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '검증 요청을 저장하지 못했습니다.');
    } finally { setSubmitting(false); }
  };

  if (error) return <AppLayout><div className="mx-auto max-w-4xl py-8 lg:ml-64"><div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm font-bold text-rose-700">{error}</div></div></AppLayout>;
  if (!item) return <AppLayout><div className="mx-auto max-w-4xl py-8 lg:ml-64"><div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm font-bold text-slate-500">Case 데이터를 불러오는 중입니다.</div></div></AppLayout>;

  return <AppLayout><div className="mx-auto max-w-4xl py-8 lg:ml-64">
    <Link to={`/cases/${item.id}`} className="mb-5 inline-flex items-center gap-1 text-sm font-bold text-slate-500"><ArrowLeft size={16}/> Case 상세</Link>
    <div className="mb-4"><p className="text-xs font-bold text-blue-600">CASE VERIFICATION</p><h1 className="mt-2 text-2xl font-black">사실 확인 요청</h1></div><CaseContextBar item={item} compact/>
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex items-center gap-2"><ShieldCheck size={19} className="text-blue-600"/><h2 className="text-sm font-extrabold">Case 진단 근거</h2></div><p className="mt-4 rounded-xl border border-slate-100 p-4 text-sm leading-6 text-slate-700">{item.verificationBrief || '추가 사실 확인이 필요합니다.'}</p></section>
    <section className="mt-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-sm font-extrabold">실제 분석 근거 기반 확인 항목</h2><div className="mt-4 space-y-4">{questions.length ? questions.map((question) => <div key={question.id} className="rounded-xl border border-slate-100 p-4"><p className="text-sm font-bold"><span className="mr-2 text-blue-600">확인 항목 {String(question.id).padStart(2, '0')}</span>{question.question}</p><div className="mt-3 grid gap-2 sm:grid-cols-3">{(['사실임', '사실 아님', '확인 불가'] as Answer[]).map((option) => <label key={option} className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-xs font-bold ${answers[question.id] === option ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-slate-200 text-slate-600 hover:border-blue-300'}`}><input type="checkbox" checked={answers[question.id] === option} onChange={() => choose(question.id, option)} className="h-4 w-4 accent-blue-600"/>{option}</label>)}</div></div>) : <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">현재 분석 결과에 추가 확인 항목이 없습니다.</p>}</div></section>
    <section className="mt-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-sm font-extrabold">기관 추가 의견</h2><textarea value={opinion} onChange={(event) => setOpinion(event.target.value)} disabled={submitting} placeholder="확인 내용을 입력해주세요" className="mt-3 min-h-32 w-full resize-y rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm outline-none focus:border-blue-500"/><button onClick={submit} disabled={submitting || (!Object.keys(answers).length && !opinion.trim())} className="mt-3 inline-flex items-center justify-center gap-2 rounded-xl bg-slate-900 px-5 py-3 text-sm font-bold text-white disabled:opacity-40"><Send size={15}/> {submitting ? '저장 중' : '검증 요청 저장'}</button></section>
    <section className="mt-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-sm font-extrabold">저장된 검증 요청</h2><div className="mt-3 space-y-2">{tasks.length ? tasks.map((task) => <div key={task.verification_task_id} className="rounded-xl border border-slate-100 p-3"><div className="flex justify-between gap-3 text-xs"><span className="font-bold">{task.target}</span><span className="text-blue-600">{task.status}</span></div><p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">{task.claim}</p></div>) : <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">저장된 검증 요청이 없습니다.</p>}</div></section>
  </div></AppLayout>;
};
