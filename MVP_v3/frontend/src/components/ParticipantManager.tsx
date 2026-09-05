import React, { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Check, Loader2, RefreshCw, UserPlus, Users, Wifi, WifiOff, X } from 'lucide-react';
import { casesApi, CURRENT_BANK_USER, CURRENT_CUSTOMER_USER } from '../api/cases';
import type { CaseMember, CaseMemberRole, CasePresence } from '../api/types';

interface Props {
  caseId: string;
  open: boolean;
  onClose: () => void;
  onChanged: () => Promise<void>;
}

const roleLabel = (role: CaseMemberRole) => ({ CASE_OWNER: '메인 담당자', CHAT_OPERATOR: '상담 담당자', REVIEWER: '검토자', VIEWER: '열람자' }[role]);
const presenceLabel = (presence?: CasePresence['presence']) => ({ VIEWING: '온라인', TYPING: '입력 중', AWAY: '자리 비움', OFFLINE: '오프라인' }[presence ?? 'OFFLINE']);

export const ParticipantManager: React.FC<Props> = ({ caseId, open, onClose, onChanged }) => {
  const closeRef = useRef<HTMLButtonElement>(null);
  const onCloseRef = useRef(onClose);
  const [members, setMembers] = useState<CaseMember[]>([]);
  const [presence, setPresence] = useState<CasePresence[]>([]);
  const [assignee, setAssignee] = useState('');
  const [newName, setNewName] = useState('');
  const [newRole, setNewRole] = useState<CaseMemberRole>('VIEWER');
  const [loading, setLoading] = useState(false);
  const [initialized, setInitialized] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const [memberList, presenceList] = await Promise.all([casesApi.members(caseId), casesApi.presence(caseId)]);
      setMembers(memberList); setPresence(presenceList);
      setAssignee(memberList.find((item) => item.role === 'CASE_OWNER')?.display_name ?? '');
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
  const updateRole = async (member: CaseMember, role: CaseMemberRole) => {
    if (busy) return;
    setBusy(true); setError('');
    try {
      if (role === 'CASE_OWNER') await casesApi.setPrimaryAssignee(caseId, member.display_name);
      else await casesApi.upsertMember(caseId, { user_id: member.user_id, display_name: member.display_name, role });
      await load(); await onChanged();
    }
    catch (reason) { setError(reason instanceof Error ? reason.message : '참여자 역할을 변경하지 못했습니다.'); }
    finally { setBusy(false); }
  };
  const addMember = async (event: FormEvent) => {
    event.preventDefault();
    if (!newName.trim() || busy) return;
    setBusy(true); setError('');
    try {
      await casesApi.upsertMember(caseId, { user_id: `staff-${crypto.randomUUID()}`, display_name: newName.trim(), role: newRole });
      setNewName(''); setNewRole('VIEWER'); await load(); await onChanged();
    } catch (reason) { setError(reason instanceof Error ? reason.message : '참여자를 추가하지 못했습니다.'); }
    finally { setBusy(false); }
  };

  if (!open) return null;
  return <div className="participant-backdrop" role="presentation" onMouseDown={onClose}>
    <aside className="participant-drawer" role="dialog" aria-modal="true" aria-labelledby="participant-title" onMouseDown={(event) => event.stopPropagation()}>
      <header><Users size={19}/><div><h2 id="participant-title">참여자 관리</h2><p>현재 관계자와 접속 상태, 메인 담당자를 관리합니다.</p></div><button type="button" onClick={() => void load()} aria-label="참여자 정보 새로고침"><RefreshCw size={16} className={loading ? 'spin' : ''}/></button><button ref={closeRef} type="button" onClick={onClose} aria-label="참여자 관리 닫기"><X size={18}/></button></header>
      {error && <p className="participant-error">{error}</p>}
      <div className="participant-scroll">
        <section className="assignee-setting"><h3>현재 사용자 역할</h3><p>로그인 없는 시연 환경입니다. 내 역할을 검토자로 설정하면 사실 확정·AI 제안 채택·업무 완료를 처리할 수 있습니다. 다른 메인 담당자는 변경하지 않습니다.</p>{members.filter((member) => member.user_id === CURRENT_BANK_USER.user_id).map((member) => <div key={member.user_id}><strong>{member.display_name} · {roleLabel(member.role)}</strong>{!['CASE_OWNER', 'REVIEWER'].includes(member.role) && <button type="button" disabled={loading || busy} onClick={() => void updateRole(member, 'REVIEWER')}>내 역할을 검토자로 설정</button>}</div>)}</section>
        <section className="customer-presence-card"><div className={customerPresence && customerPresence.presence !== 'OFFLINE' ? 'online' : 'offline'}>{customerPresence && customerPresence.presence !== 'OFFLINE' ? <Wifi size={17}/> : <WifiOff size={17}/>}</div><span><small>고객 연결 상태</small><strong>{presenceLabel(customerPresence?.presence)}</strong><p>{customerPresence ? `마지막 확인 ${new Date(customerPresence.last_seen_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}` : '현재 고객 접속 신호가 없습니다.'}</p></span></section>
        <section className="assignee-setting"><h3>메인 담당자 설정</h3><p>사건 대응을 총괄할 담당자를 한 명 지정합니다.</p><div><select value={assignee} onChange={(event) => setAssignee(event.target.value)} disabled={loading || busy}><option value="">미배정</option>{members.map((member) => <option key={member.user_id} value={member.display_name}>{member.display_name}</option>)}</select><button type="button" onClick={() => void saveAssignee()} disabled={loading || busy}><Check size={14}/>설정</button></div></section>
        <section className="participant-list"><div><h3>현재 관계자</h3><span>{members.length}명</span></div>{loading && !initialized ? <p className="participant-state"><Loader2 className="spin" size={17}/>불러오는 중</p> : members.length === 0 ? <p className="participant-state">등록된 관계자가 없습니다.</p> : members.map((member) => {
          const memberPresence = presenceByUser.get(member.user_id);
          const online = Boolean(memberPresence && memberPresence.presence !== 'OFFLINE');
          return <article key={member.user_id}><div className={online ? 'online' : 'offline'}>{member.display_name.slice(0, 1)}</div><span><strong>{member.display_name}{member.user_id === CURRENT_BANK_USER.user_id && <em>나</em>}</strong><small>{presenceLabel(memberPresence?.presence)}</small></span><select value={member.role} disabled={busy || member.role === 'CASE_OWNER'} onChange={(event) => void updateRole(member, event.target.value as CaseMemberRole)}><option value="CASE_OWNER">메인 담당자</option><option value="CHAT_OPERATOR">상담 담당자</option><option value="REVIEWER">검토자</option><option value="VIEWER">열람자</option></select></article>;
        })}</section>
        <form className="participant-add" onSubmit={addMember}><h3><UserPlus size={15}/>관계자 추가</h3><div><input value={newName} maxLength={80} onChange={(event) => setNewName(event.target.value)} placeholder="이름 또는 표시 이름"/><select value={newRole} onChange={(event) => setNewRole(event.target.value as CaseMemberRole)}><option value="CHAT_OPERATOR">상담 담당자</option><option value="REVIEWER">검토자</option><option value="VIEWER">열람자</option></select><button type="submit" disabled={busy || !newName.trim()}>추가</button></div></form>
      </div>
    </aside>
  </div>;
};
