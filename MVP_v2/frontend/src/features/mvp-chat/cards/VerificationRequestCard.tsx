import React, { useState } from 'react';
import { Building2, Send, X } from 'lucide-react';
import { caseWorkflowApi } from '../../../services/caseWorkflowApi';
import { mvpChatApi } from '../../../services/mvpChatApi';

interface Props { caseId: string; onCreated: () => Promise<void> | void; onClose: () => void; }

export const VerificationRequestCard: React.FC<Props> = ({ caseId, onCreated, onClose }) => {
  const [claim, setClaim] = useState('');
  const [target, setTarget] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [completed, setCompleted] = useState(false);
  const [noticeWarning, setNoticeWarning] = useState('');
  const submit = async () => {
    if (!claim.trim() || !target.trim()) return;
    setSaving(true); setError('');
    try {
      await caseWorkflowApi.createVerification(caseId, claim.trim(), target.trim());
      setCompleted(true);
      try { await mvpChatApi.createMessage(caseId, { actor_type: 'SYSTEM', actor_user_id: 'case-system', actor_display_name: '시스템', actor_role: null, content: `기관 검증 업무가 등록되었습니다. 확인 대상: ${target.trim()}`, channel: 'TEAM', audience: 'BANK_INTERNAL', visibility: 'BANK_INTERNAL', message_kind: 'SYSTEM_EVENT' }); }
      catch { setNoticeWarning('검증 업무는 등록됐지만 은행 협업 알림을 동기화하지 못했습니다. 다시 등록하지 말고 새로고침해 주세요.'); }
      try { await onCreated(); } catch { setNoticeWarning('검증 업무는 등록됐지만 최신 화면을 불러오지 못했습니다. 새로고침해 주세요.'); }
    }
    catch (reason) { setError(reason instanceof Error ? reason.message : '검증 요청을 만들지 못했습니다.'); }
    finally { setSaving(false); }
  };
  return <section className="rounded-2xl border border-violet-400/50 bg-slate-950 p-4 text-slate-100 shadow-lg"><div className="flex items-start justify-between gap-3"><div><p className="text-[11px] font-black tracking-wide text-violet-300">AI 개인 작업 · 기관 확인 요청</p><h2 className="mt-1 font-black">검증 업무 초안</h2><p className="mt-1 text-xs leading-5 text-slate-400">외부 기관에 자동 전송하지 않습니다. 공식 채널로 확인할 업무만 Case에 등록합니다.</p></div><button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-800" aria-label="검증 요청 카드 닫기"><X size={17}/></button></div><label className="mt-4 block text-xs font-bold text-slate-300">사칭 주장<input value={claim} disabled={completed} onChange={(event) => setClaim(event.target.value)} placeholder="예: 금융감독원 직원이라고 주장" className="mt-1.5 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white outline-none focus:border-violet-400 disabled:opacity-60"/></label><label className="mt-3 block text-xs font-bold text-slate-300">확인 대상<input value={target} disabled={completed} onChange={(event) => setTarget(event.target.value)} placeholder="기관명, 전화번호, 계좌번호 등" className="mt-1.5 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white outline-none focus:border-violet-400 disabled:opacity-60"/></label>{completed && <p className="mt-3 rounded-xl border border-emerald-500/30 bg-emerald-950/40 p-3 text-xs font-bold text-emerald-200">검증 업무가 Case에 등록되었습니다.</p>}{error && <p className="mt-3 rounded-xl bg-rose-950/60 p-3 text-xs text-rose-200">{error}</p>}{noticeWarning && <p className="mt-3 rounded-xl bg-amber-950/60 p-3 text-xs text-amber-200">{noticeWarning}</p>}<div className="mt-4 flex justify-end gap-2"><button onClick={onClose} className="rounded-xl border border-slate-700 px-3 py-2 text-xs font-bold text-slate-300">닫기</button>{!completed && <button disabled={!claim.trim() || !target.trim() || saving} onClick={() => void submit()} className="inline-flex items-center gap-1 rounded-xl bg-violet-500 px-3 py-2 text-xs font-black text-white disabled:opacity-50"><Building2 size={14}/>{saving ? '등록 중' : '검증 업무 등록'}</button>}</div></section>;
};
