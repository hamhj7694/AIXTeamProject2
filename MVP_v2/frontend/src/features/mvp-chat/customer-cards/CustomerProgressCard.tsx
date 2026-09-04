import React from 'react';
import { Check, Circle, Loader2 } from 'lucide-react';
import type { CustomerQuestion } from '../../../services/mvpChatApi';
import { caseProgressMessage, caseProgressStage } from '../../../utils/casePresentation';

const statusLabel: Record<string, string> = { NEW: '사건 접수', TRIAGE: '상황 확인', VERIFYING: '기관 확인', IN_PROGRESS: '보호 조치', CLOSED: '처리 완료' };

interface Props { currentCase: Record<string, unknown>; questions: CustomerQuestion[]; verificationCount: number; recoveryActive?: boolean; }

export const CustomerProgressCard: React.FC<Props> = ({ currentCase, questions, verificationCount, recoveryActive = false }) => {
  const status = String(currentCase.status ?? 'TRIAGE');
  const mode = String(currentCase.mode ?? 'PREVENT');
  const answered = questions.filter((question) => question.status === 'ANSWERED').length;
  const waiting = questions.filter((question) => question.status === 'ASKED' || question.status === 'PENDING').length;
  const stage = caseProgressStage(status, String(currentCase.victim_transfer_status ?? '') === 'YES', mode);
  const preventSteps = [
    { label: '상황 접수', done: true, active: false },
    { label: '필요 정보 확인', done: stage > 1, active: stage === 1 },
    { label: '기관 확인', done: stage > 2, active: stage === 2 },
    { label: '보호 조치', done: stage > 3, active: stage === 3 },
    { label: '처리 완료', done: stage === 4, active: stage === 4 },
  ];
  const recoverySteps = [
    { label: '피해 상황 접수', done: true, active: false },
    { label: '추가 송금·접촉 중단', done: false, active: true },
    { label: '거래내역·대화 증빙 확보', done: false, active: false },
    { label: '은행 지급정지·신고 확인', done: false, active: false },
    { label: '피해구제 신청', done: false, active: false },
  ];
  const recovery = recoveryActive || mode === 'RECOVERY';
  const steps = recovery ? recoverySteps : preventSteps;
  return <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
    <div className="flex items-center justify-between gap-2"><p className="text-sm font-black">현재 진행 상황</p><span className={`rounded-full px-2.5 py-1 text-[10px] font-black ${recovery ? 'bg-rose-50 text-rose-700' : 'bg-blue-50 text-blue-700'}`}>{recovery ? '피해구제 안내' : statusLabel[status] ?? '확인 중'}</span></div>
    <div className="mt-4 space-y-3">{steps.map((step) => <div key={step.label} className="flex items-center gap-2.5"><span className={`grid h-6 w-6 shrink-0 place-items-center rounded-full ${step.done ? 'bg-emerald-100 text-emerald-700' : step.active ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-400'}`}>{step.done ? <Check size={13}/> : step.active ? <Loader2 size={13} className="animate-spin"/> : <Circle size={10}/>}</span><span className={`text-xs font-bold ${step.done ? 'text-emerald-800' : step.active ? 'text-blue-800' : 'text-slate-500'}`}>{step.label}</span></div>)}</div>
    <p className="mt-4 rounded-xl bg-slate-50 p-3 text-[11px] leading-5 text-slate-600">{caseProgressMessage(stage, recovery)}<span className="mt-1 block text-slate-500">답변 완료 {answered}건 · 확인 대기 {waiting}건{verificationCount > 0 ? ` · 공개 확인 결과 ${verificationCount}건` : ''}</span></p>
  </section>;
};
