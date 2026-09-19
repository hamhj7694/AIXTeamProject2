import React, { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Check, Loader2, RefreshCw, UserPlus, Users, Wifi, WifiOff, X } from 'lucide-react';
import { casesApi, CURRENT_BANK_USER, CURRENT_CUSTOMER_USER, displayBankUserName } from '../api/cases';
import type { CaseAssignmentRole, CaseMember, CasePresence } from '../api/types';
import { generateUuid } from '../uuid';

interface Props {
  caseId: string;
  open: boolean;
  onClose: () => void;
  onChanged: () => Promise<void>;
}

const presenceLabel = (presence?: CasePresence['presence']) => ({ VIEWING: '온라인', TYPING: '입력 중', AWAY: '자리 비움', OFFLINE: '오프라인' }[presence ?? 'OFFLINE']);

export const ParticipantManager: React.FC<Props> = ({ caseId, open, onClose, onChanged }) => {
  const closeRef = useRef<HTMLButtonElement>(null);
  const onCloseRef = useRef(onClose);
  const [members, setMembers] = useState<CaseMember[]>([]);
  const [presence, setPresence] = useState<CasePresence[]>([]);
  const [assignee, setAssignee] = useState('');
  const [newName, setNewName] = useState('');
  const [newAssignmentRole, setNewAssignmentRole] = useState<CaseAssignmentRole>('VIEWER');
  const [loading, setLoading] = useState(false);
  const [initialized, setInitialized] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const [memberList, presenceList] = await Promise.all([casesApi.members(caseId), casesApi.presence(caseId)]);
      setMembers(memberList); setPresence(presenceList);
      const owner = memberList.find((item) => item.assignment_role === 'SUPERVISOR');
      setAssignee(owner ? displayBankUserName(owner.user_id, owner.display_name) : '');
      setInitialized(true);
    } catch (reason) { setError(reason instanceof Error ? reason.message : '참여자 정보를 불러오지 못했습니다.'); }
    finally { setLoading(false); }
  }, [caseId]);

  useEffect(() => { onCloseRef.current = onClose; }, [onClose]);
  useEffect(() => {
    setMembers([]); setPresence([]); setAssignee(''); setInitialized(false); setError('');
  }, [caseId]);

  useEffect(() => {
    if (!open) return;
    void load(); closeRef.current?.focus();
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === 'Escape') onCloseRef.current(); };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [load, open]);

  const presenceByUser = useMemo(() => new Map(presence.map((item) => [item.user_id, item])), [presence]);
  const customerPresence = presenceByUser.get(CURRENT_CUSTOMER_USER.user_id) ?? presence.find((item) => item.channel === 'CUSTOMER' && item.display_name === CURRENT_CUSTOMER_USER.display_name);

  const saveAssignee = async () => {
    if (busy) return;
    setBusy(true); setError('');
    try { await casesApi.setPrimaryAssignee(caseId, assignee || null); await load(); await onChanged(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : '메인 담당자를 설정하지 못했습니다.'); }
    finally { setBusy(false); }
  };
  const updateAssignmentRole = async (member: CaseMember, assignment_role: CaseAssignmentRole) => {
    if (busy) return;
    setBusy(true); setError('');
    try { await casesApi.upsertMember(caseId, { user_id: member.user_id, display_name: displayBankUserName(member.user_id, member.display_name), assignment_role }); await load(); await onChanged(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : '케이스 배정 역할을 변경하지 못했습니다.'); }
    finally { setBusy(false); }
  };
  const addMember = async (event: FormEvent) => {
    event.preventDefault();
    if (!newName.trim() || busy) return;
    setBusy(true); setError('');
    try {
      await casesApi.upsertMember(caseId, { user_id: `staff-${generateUuid()}`, display_name: newName.trim(), assignment_role: newAssignmentRole });
      setNewName(''); setNewAssignmentRole('VIEWER'); await load(); await onChanged();
    } catch (reason) { setError(reason instanceof Error ? reason.message : '참여자를 추가하지 못했습니다.'); }
    finally { setBusy(false); }
  };

  if (!open) return null;
  return <div className="participant-backdrop" role="presentation" onMouseDown={onClose}>
    <aside className="participant-drawer" role="dialog" aria-modal="true" aria-labelledby="participant-title" onMouseDown={(event) => event.stopPropagation()}>
      <header><Users size={19}/><div><h2 id="participant-title">참여자 관리</h2><p>현재 관계자와 접속 상태, 메인 담당자를 관리합니다.</p></div><button type="button" onClick={() => void load()} aria-label="참여자 정보 새로고침"><RefreshCw size={16} className={loading ? 'spin' : ''}/></button><button ref={closeRef} type="button" onClick={onClose} aria-label="참여자 관리 닫기"><X size={18}/></button></header>
      {error && <p className="participant-error">{error}</p>}
      <div className="participant-scroll">
        <section className="customer-presence-card"><div className={customerPresence && customerPresence.presence !== 'OFFLINE' ? 'online' : 'offline'}>{customerPresence && customerPresence.presence !== 'OFFLINE' ? <Wifi size={17}/> : <WifiOff size={17}/>}</div><span><small>고객 연결 상태</small><strong>{presenceLabel(customerPresence?.presence)}</strong><p>{customerPresence ? `마지막 확인 ${new Date(customerPresence.last_seen_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}` : '현재 고객 접속 신호가 없습니다.'}</p></span></section>
        <section className="assignee-setting"><h3>메인 담당자 설정</h3><p>사건 대응을 총괄할 담당자를 한 명 지정합니다.</p><div><select value={assignee} onChange={(event) => setAssignee(event.target.value)} disabled={loading || busy}><option value="">미배정</option>{members.map((member) => { const displayName = displayBankUserName(member.user_id, member.display_name); return <option key={member.user_id} value={displayName}>{displayName}</option>; })}</select><button type="button" onClick={() => void saveAssignee()} disabled={loading || busy}><Check size={14}/>설정</button></div></section>
        <section className="participant-list"><div><h3>현재 관계자</h3><span>{members.length}명</span></div>{loading && !initialized ? <p className="participant-state"><Loader2 className="spin" size={17}/>불러오는 중</p> : members.length === 0 ? <p className="participant-state">등록된 관계자가 없습니다.</p> : members.map((member) => {
          const memberPresence = presenceByUser.get(member.user_id);
          const online = Boolean(memberPresence && memberPresence.presence !== 'OFFLINE');
          const displayName = displayBankUserName(member.user_id, member.display_name);
          return <article key={member.user_id}><div className={online ? 'online' : 'offline'}>{displayName.slice(0, 1)}</div><span><strong>{displayName}{member.user_id === CURRENT_BANK_USER.user_id && <em>나</em>}</strong><small>{presenceLabel(memberPresence?.presence)}</small></span><select value={member.assignment_role} disabled={busy} onChange={(event) => void updateAssignmentRole(member, event.target.value as CaseAssignmentRole)} aria-label={`${displayName} 배정 역할`}><option value="SUPERVISOR">배정: 사건 총괄</option><option value="MONITORING">배정: 모니터링</option><option value="CONSULTATION">배정: 상담·대응</option><option value="VIEWER">배정: 기타 열람자</option><option value="HANDOVER_PENDING">배정: 인수인계 대기자</option></select></article>;
        })}</section>
        <form className="participant-add" onSubmit={addMember}><h3><UserPlus size={15}/>관계자 추가</h3><div><input value={newName} maxLength={80} onChange={(event) => setNewName(event.target.value)} placeholder="이름 또는 표시 이름"/><select value={newAssignmentRole} onChange={(event) => setNewAssignmentRole(event.target.value as CaseAssignmentRole)}><option value="SUPERVISOR">사건 총괄</option><option value="MONITORING">모니터링</option><option value="CONSULTATION">상담·대응</option><option value="VIEWER">기타 열람자</option><option value="HANDOVER_PENDING">인수인계 대기자</option></select><button type="submit" disabled={busy || !newName.trim()}>추가</button></div></form>
      </div>
    </aside>
  </div>;
};
