import React, { useEffect, useMemo, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { caseWorkflowApi } from '../../../services/caseWorkflowApi';
import { mvpChatApi } from '../../../services/mvpChatApi';
import { WorkCardFrame } from './WorkCardFrame';
import type { WorkCardStage } from './types';

type Target = 'TRIAGE' | 'VERIFYING' | 'IN_PROGRESS' | 'RECOVERY';
const labels: Record<Target, { title: string; description: string }> = {
  TRIAGE: { title: '초기 분류', description: '신규 Case의 기본 정보와 우선순위를 확인합니다.' },
  VERIFYING: { title: '기관 검증 중', description: '기관·계좌·연락처 확인 업무를 진행합니다.' },
  IN_PROGRESS: { title: '대응 진행 중', description: '고객 확인과 은행 보호조치를 진행합니다.' },
  RECOVERY: { title: '피해구제 모드', description: '확인된 피해를 기준으로 Recovery 절차로 전환합니다.' },
};

const availableTargetsFor = (status: string, mode: string): Target[] => {
  if (status === 'CLOSED' || mode === 'CLOSED') return [];
  if (status === 'NEW') return ['TRIAGE'];
  if (status === 'TRIAGE') return mode === 'PREVENT' ? ['VERIFYING', 'IN_PROGRESS', 'RECOVERY'] : ['VERIFYING', 'IN_PROGRESS'];
  if (status === 'VERIFYING') return mode === 'PREVENT' ? ['IN_PROGRESS', 'RECOVERY'] : ['IN_PROGRESS'];
  if (status === 'IN_PROGRESS' && mode === 'PREVENT') return ['RECOVERY'];
  return [];
};

interface Props { caseId: string; requestedBy: string; currentCase: Record<string, unknown>; initialTarget?: string | null; onCompleted: () => Promise<void> | void; onClose: () => void; }

export const CaseTransitionCard: React.FC<Props> = ({ caseId, requestedBy, currentCase, initialTarget, onCompleted, onClose }) => {
  const currentStatus = String(currentCase.status ?? 'TRIAGE');
  const currentMode = String(currentCase.mode ?? 'PREVENT');
  const availableTargets = useMemo(() => availableTargetsFor(currentStatus, currentMode), [currentMode, currentStatus]);
  const [target, setTarget] = useState<Target>(() => availableTargets.includes(initialTarget as Target) ? initialTarget as Target : availableTargets[0] ?? 'IN_PROGRESS');
  const [confirmed, setConfirmed] = useState(false);
  const [stage, setStage] = useState<WorkCardStage>('DRAFT');
  const [error, setError] = useState('');
  const [noticeWarning, setNoticeWarning] = useState('');
  const disabled = availableTargets.length === 0;

  useEffect(() => {
    if (availableTargets.length && !availableTargets.includes(target)) {
      setTarget(availableTargets[0]);
      setConfirmed(false);
      setStage('DRAFT');
    }
  }, [availableTargets, target]);

  const submit = async () => {
    if (!confirmed || disabled || stage === 'SUBMITTING') return;
    setStage('SUBMITTING'); setError(''); setNoticeWarning('');
    try {
      const changes = target === 'RECOVERY'
        ? { status: currentStatus === 'TRIAGE' || currentStatus === 'VERIFYING' ? 'IN_PROGRESS' : currentStatus, mode: 'RECOVERY' }
        : { status: target };
      await caseWorkflowApi.patchCase(caseId, Number(currentCase.version ?? 1), changes);
      setStage('REGISTERED');
      try { await mvpChatApi.createMessage(caseId, { actor_type: 'SYSTEM', actor_user_id: 'case-system', actor_display_name: '시스템', actor_role: null, content: `${requestedBy}님이 Case 업무 단계를 ‘${labels[target].title}’(으)로 변경했습니다.`, channel: 'TEAM', audience: 'BANK_INTERNAL', visibility: 'BANK_INTERNAL', message_kind: 'SYSTEM_EVENT' }); }
      catch { setNoticeWarning('상태는 변경됐지만 은행 협업 알림을 동기화하지 못했습니다. 새로고침해 주세요.'); }
      try { await onCompleted(); } catch { setNoticeWarning('상태는 변경됐지만 최신 화면을 불러오지 못했습니다. 새로고침해 주세요.'); }
      onClose();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Case 상태를 변경하지 못했습니다. 최신 상태를 다시 확인해 주세요.');
      setStage('FAILED');
    }
  };

  return <WorkCardFrame eyebrow="AI 개인 작업 · Case 상태" title="업무 단계 변경" description={`현재 ${currentStatus} · ${currentMode}. Backend가 허용하는 다음 단계만 표시합니다.`} stage={stage} onClose={onClose}>
    {availableTargets.length > 0 ? <div className="mt-4 grid gap-2 sm:grid-cols-3">{availableTargets.map((value) => <button key={value} type="button" disabled={stage === 'REGISTERED'} onClick={() => { setTarget(value); setConfirmed(false); setStage('READY'); }} className={`rounded-xl border p-3 text-left ${target === value ? 'border-violet-400 bg-violet-500/15' : 'border-slate-700 bg-slate-900'}`}><b className="block text-xs">{labels[value].title}</b><span className="mt-1 block text-[10px] leading-4 text-slate-400">{labels[value].description}</span></button>)}</div> : <p className="mt-4 rounded-xl bg-slate-800 p-3 text-xs text-slate-300">현재 상태에서 이 카드로 진행할 수 있는 다음 단계가 없습니다.</p>}
    {target === 'RECOVERY' && availableTargets.includes('RECOVERY') && <p className="mt-3 rounded-xl bg-rose-500/10 p-3 text-[11px] leading-5 text-rose-200">피해 발생 여부와 실제 피해액을 먼저 확인하세요. 이 변경은 기존 Case를 유지한 채 피해구제 흐름을 시작합니다.</p>}
    {stage !== 'REGISTERED' && !disabled && <label className="mt-3 flex cursor-pointer gap-2 rounded-xl border border-slate-700 p-3 text-xs text-slate-300"><input type="checkbox" checked={confirmed} onChange={(event) => { setConfirmed(event.target.checked); if (event.target.checked) setStage('READY'); }} className="mt-0.5 accent-violet-500"/><span><b>변경 내용을 확인했습니다.</b><span className="mt-1 block text-[11px] text-slate-400">AI 제안이 아니라 현재 담당자의 명시적 상태 변경으로 기록됩니다.</span></span></label>}
    {stage === 'REGISTERED' && <p className="mt-3 rounded-xl border border-emerald-500/30 bg-emerald-950/40 p-3 text-xs font-bold text-emerald-200">Case 상태가 변경되었습니다. 새 상태는 모든 역할 화면에서 같은 Case 데이터로 조회됩니다.</p>}
    {error && <p className="mt-3 rounded-xl bg-rose-950/60 p-3 text-xs text-rose-200">{error}</p>}
    {noticeWarning && <p className="mt-3 rounded-xl bg-amber-950/60 p-3 text-xs text-amber-200">{noticeWarning}</p>}
    <div className="mt-4 flex justify-end gap-2"><button type="button" onClick={onClose} className="rounded-xl border border-slate-700 px-3 py-2 text-xs font-bold text-slate-300">닫기</button>{stage !== 'REGISTERED' && !disabled && <button type="button" disabled={!confirmed || stage === 'SUBMITTING'} onClick={() => void submit()} className="inline-flex items-center gap-1 rounded-xl bg-violet-500 px-3 py-2 text-xs font-black text-white disabled:opacity-50"><RefreshCw size={14}/>상태 변경 적용</button>}</div>
  </WorkCardFrame>;
};
