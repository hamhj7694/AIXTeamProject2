import React, { useState } from 'react';
import { ClipboardCheck } from 'lucide-react';
import { caseWorkflowApi, type CaseAction } from '../../../services/caseWorkflowApi';
import { mvpChatApi } from '../../../services/mvpChatApi';
import { WorkCardFrame } from './WorkCardFrame';
import type { WorkCardStage } from './types';

const actions = [
  ['PAYMENT_HOLD_REVIEW', '송금·지급정지 검토'],
  ['ACCOUNT_REPORT_GUIDANCE', '사기이용계좌 신고 안내'],
  ['EVIDENCE_PRESERVATION', '증빙자료 확보'],
  ['DEVICE_SECURITY_GUIDANCE', '기기·계정 보호 안내'],
  ['CUSTOMER_CALLBACK', '고객 재확인 일정'],
  ['OTHER', '기타 업무'],
] as const;

interface Props { caseId: string; requestedBy: string; onCompleted: () => Promise<void> | void; onClose: () => void; }

export const BankActionCard: React.FC<Props> = ({ caseId, requestedBy, onCompleted, onClose }) => {
  const [actionType, setActionType] = useState<(typeof actions)[number][0]>('PAYMENT_HOLD_REVIEW');
  const [note, setNote] = useState('');
  const [stage, setStage] = useState<WorkCardStage>('DRAFT');
  const [result, setResult] = useState<CaseAction | null>(null);
  const [error, setError] = useState('');
  const [noticeWarning, setNoticeWarning] = useState('');
  const submit = async () => {
    if (!note.trim() || stage === 'SUBMITTING') return;
    setStage('SUBMITTING'); setError('');
    try {
      const created = await caseWorkflowApi.createAction(caseId, actionType, note.trim());
      const actionLabel = actions.find(([value]) => value === actionType)?.[1] ?? '보호조치';
      setResult(created); setStage('REGISTERED');
      try { await mvpChatApi.createMessage(caseId, { actor_type: 'SYSTEM', actor_user_id: 'case-system', actor_display_name: '시스템', actor_role: null, content: `${requestedBy}님이 ${actionLabel} 업무를 등록했습니다. 실제 실행 여부는 담당자 확인이 필요합니다.`, channel: 'TEAM', audience: 'BANK_INTERNAL', visibility: 'BANK_INTERNAL', message_kind: 'SYSTEM_EVENT' }); }
      catch { setNoticeWarning('업무는 등록됐지만 은행 협업 알림을 동기화하지 못했습니다. 새로고침 후 확인해 주세요.'); }
      try { await onCompleted(); } catch { setNoticeWarning('업무는 등록됐지만 최신 화면을 불러오지 못했습니다. 새로고침해 주세요.'); }
    } catch (reason) { setError(reason instanceof Error ? reason.message : '보호조치 업무를 등록하지 못했습니다.'); setStage('FAILED'); }
  };
  return <WorkCardFrame eyebrow="AI 개인 작업 · 보호조치" title="보호조치 업무 등록" description="실제 금융 조치를 자동 실행하지 않습니다. 담당자가 수행·확인할 업무를 Case에 등록합니다." stage={stage} onClose={onClose}>
    {result ? <div className="mt-4 rounded-xl border border-emerald-500/30 bg-emerald-950/40 p-3 text-xs text-emerald-100"><p className="font-black">업무가 등록되었습니다.</p><p className="mt-1">상태: {result.status} · 업무 ID: {result.action_id}</p><p className="mt-1 text-emerald-200/80">실제 실행 완료 여부는 담당자가 별도로 확인해야 합니다.</p></div> : <>
      <label className="mt-4 block text-xs font-bold text-slate-300">업무 유형<select value={actionType} onChange={(event) => { setActionType(event.target.value as typeof actionType); setStage('READY'); }} className="mt-1.5 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white">{actions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      <label className="mt-3 block text-xs font-bold text-slate-300">업무 내용<textarea value={note} onChange={(event) => { setNote(event.target.value); setStage(event.target.value.trim() ? 'READY' : 'DRAFT'); }} rows={3} placeholder="확인 대상, 필요한 조치, 담당자에게 전달할 내용을 적어주세요." className="mt-1.5 w-full resize-none rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white outline-none focus:border-violet-400"/></label>
      <p className="mt-3 rounded-xl bg-amber-500/10 p-3 text-[11px] leading-5 text-amber-200">지급정지·계좌조치 등 실제 금융 업무는 은행 권한과 별도 승인 절차를 거쳐야 합니다.</p>
    </>}
    {error && <p className="mt-3 rounded-xl bg-rose-950/60 p-3 text-xs text-rose-200">{error}</p>}
    {noticeWarning && <p className="mt-3 rounded-xl bg-amber-950/60 p-3 text-xs text-amber-200">{noticeWarning}</p>}
    <div className="mt-4 flex justify-end gap-2"><button type="button" onClick={onClose} className="rounded-xl border border-slate-700 px-3 py-2 text-xs font-bold text-slate-300">닫기</button>{!result && <button type="button" disabled={!note.trim() || stage === 'SUBMITTING'} onClick={() => void submit()} className="inline-flex items-center gap-1 rounded-xl bg-violet-500 px-3 py-2 text-xs font-black text-white disabled:opacity-50"><ClipboardCheck size={14}/>검토 업무 등록</button>}</div>
  </WorkCardFrame>;
};
