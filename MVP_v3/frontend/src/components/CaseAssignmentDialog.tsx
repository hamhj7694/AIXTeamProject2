import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Check, Loader2, Users, X } from 'lucide-react';
import { casesApi, CURRENT_BANK_USER, CURRENT_BANK_USER_ROLE_LABEL, CURRENT_BANK_USER_STATUS } from '../api/cases';
import type { BankStaff, BankStaffColor, CaseAssignmentRole, CaseMember } from '../api/types';

type Mode = 'initial' | 'edit';
interface Props { caseId: string; mode?: Mode; onAssigned?: () => Promise<void>; onSaved?: () => Promise<void>; onClose?: () => void; initialRecommendation?: boolean }
type Assignment = { user_id: string; display_name: string; role: CaseAssignmentRole; role_label: string; position_title: string | null; status_text: string; status_color_key: BankStaffColor; assignment_eligible: boolean; isSelf?: boolean };
type NameSort = 'ASC' | 'DESC';
type Recommendation = { recommendationRole: CaseAssignmentRole };

const roleOptions: Array<{ value: CaseAssignmentRole; label: string }> = [
  { value: 'SUPERVISOR', label: '사건 총괄' }, { value: 'MONITORING', label: '모니터링' },
  { value: 'CONSULTATION', label: '상담·대응' }, { value: 'VIEWER', label: '기타 열람자' }, { value: 'HANDOVER_PENDING', label: '인수인계 대기자' },
];
const roleForMember = (member: CaseMember): CaseAssignmentRole => member.assignment_role ?? 'HANDOVER_PENDING';
const initialSelfAssignmentRole = (mode: Mode): CaseAssignmentRole => mode === 'initial' ? 'SUPERVISOR' : 'HANDOVER_PENDING';
const roleLabel = (role: CaseAssignmentRole) => roleOptions.find((item) => item.value === role)?.label ?? '인수인계 대기자';
const recommendationConfigs: Array<{ role: CaseAssignmentRole; keywords: string[] }> = [
  // Auto-assigned roles run before the informational supervisor candidate.
  // This prevents a high-ranking FDS or 상담 specialist from being consumed
  // by the non-auto supervisor recommendation.
  { role: 'MONITORING', keywords: ['fds', '모니터링', '보안'] },
  { role: 'CONSULTATION', keywords: ['고객 상담', '상담', '대응', '고객 보호', '금융사기 대응'] },
  { role: 'SUPERVISOR', keywords: ['금융사기 대응', '사고 조사', '고객 보호', '총괄', '책임'] },
];
const activeStatuses = new Set(['근무 중', '업무 중', '회의 중', '교대 대기 중']);
const positionKeywords = ['본부장', '센터장', '실장', '팀장', '부장', '차장', '과장', '대리', '주임', '사원'];
const normalizedText = (value: string | null | undefined) => (value || '').trim().toLowerCase();
const positionRank = (title: string | null) => { const index = positionKeywords.findIndex((keyword) => normalizedText(title).includes(keyword.toLowerCase())); return index < 0 ? 0 : positionKeywords.length - index; };
const statusRank = (person: Assignment) => activeStatuses.has(person.status_text.trim()) ? 2 : person.assignment_eligible ? 1 : 0;

const staffAssignment = (item: BankStaff): Assignment => {
  const userId = item.is_self || item.linked_user_id === CURRENT_BANK_USER.user_id ? CURRENT_BANK_USER.user_id : item.linked_user_id || item.staff_id;
  const isSelf = userId === CURRENT_BANK_USER.user_id;
  return { user_id: userId, display_name: isSelf ? CURRENT_BANK_USER.display_name : item.display_name, role: 'HANDOVER_PENDING', role_label: isSelf ? CURRENT_BANK_USER_ROLE_LABEL : item.role_label, position_title: item.position_title || null, status_text: isSelf ? CURRENT_BANK_USER_STATUS : item.status_text, status_color_key: isSelf ? 'BLACK' : item.status_color_key, assignment_eligible: isSelf || item.assignment_eligible, isSelf };
};

const buildRecommendations = (staffList: BankStaff[]) => {
  const candidates = staffList.map(staffAssignment).filter((person) => !person.isSelf && person.assignment_eligible);
  const used = new Set<string>([CURRENT_BANK_USER.user_id]); const recommendations: Record<string, Recommendation> = {}; const selected: Array<{ person: Assignment; recommendation: Recommendation }> = []; const missingRoles: CaseAssignmentRole[] = [];
  const isRelated = (person: Assignment, config: { keywords: string[] }) => config.keywords.some((keyword) => normalizedText(`${person.role_label} ${person.position_title}`).includes(keyword.toLowerCase()));
  for (const [configIndex, config] of recommendationConfigs.entries()) {
    const available = candidates.filter((person) => !used.has(person.user_id)); if (!available.length) { if (config.role !== 'SUPERVISOR') missingRoles.push(config.role); continue; }
    const related = available.filter((person) => isRelated(person, config));
    // If this role has no specialist, keep people who are specialists for a
    // later role out of the fallback pool whenever another candidate exists.
    const laterConfigs = recommendationConfigs.slice(configIndex + 1);
    const reservedForLater = new Set(available.filter((person) => laterConfigs.some((later) => isRelated(person, later))).map((person) => person.user_id));
    const fallback = available.filter((person) => !reservedForLater.has(person.user_id));
    const pool = related.length ? related : (fallback.length ? fallback : available);
    const tie = new Map(pool.map((person) => [person.user_id, Math.random()]));
    const person = [...pool].sort((left, right) => statusRank(right) - statusRank(left) || ((config.role === 'SUPERVISOR' || config.role === 'MONITORING') ? positionRank(right.position_title) - positionRank(left.position_title) : 0) || (tie.get(left.user_id)! - tie.get(right.user_id)!))[0];
    const recommendation: Recommendation = { recommendationRole: config.role };
    recommendations[person.user_id] = recommendation; used.add(person.user_id); if (config.role !== 'SUPERVISOR') selected.push({ person, recommendation });
  }
  return { recommendations, selected, missingRoles: Array.from(new Set(missingRoles)) };
};

type AssignmentSnapshot = {
  recommendations: Record<string, Recommendation>;
  missingRecommendationRoles: CaseAssignmentRole[];
  initialMemberIds: string[];
  selected: Record<string, Assignment>;
};

const buildAssignmentSnapshot = (staffList: BankStaff[], memberList: CaseMember[], mode: Mode, initialRecommendation: boolean): AssignmentSnapshot => {
  const recommendationResult = mode === 'initial' && initialRecommendation
    ? buildRecommendations(staffList)
    : { recommendations: {}, selected: [], missingRoles: [] as CaseAssignmentRole[] };
  const byUserId = new Map(staffList.map((item) => {
    const person = staffAssignment(item);
    return [person.user_id, person];
  }));
  const selected: Record<string, Assignment> = {};
  memberList.forEach((member) => {
    const metadata = byUserId.get(member.user_id);
    const isSelf = member.user_id === CURRENT_BANK_USER.user_id;
    selected[member.user_id] = {
      ...(metadata ?? {
        user_id: member.user_id,
        display_name: isSelf ? CURRENT_BANK_USER.display_name : member.display_name,
        role_label: isSelf ? CURRENT_BANK_USER_ROLE_LABEL : '직원 정보 없음',
        position_title: null,
        status_text: isSelf ? CURRENT_BANK_USER_STATUS : '직원 정보 없음',
        status_color_key: isSelf ? 'BLACK' as BankStaffColor : 'GRAY' as BankStaffColor,
        assignment_eligible: true,
        role: 'HANDOVER_PENDING' as CaseAssignmentRole,
      }),
      user_id: member.user_id,
      display_name: isSelf ? CURRENT_BANK_USER.display_name : member.display_name,
      // The initial flow deliberately promotes the demo identity to the first
      // supervisor. Edit mode must preserve the server assignment instead.
      role: mode === 'initial' && isSelf ? 'SUPERVISOR' : roleForMember(member),
      isSelf,
    };
  });
  if (!selected[CURRENT_BANK_USER.user_id]) {
    selected[CURRENT_BANK_USER.user_id] = {
      user_id: CURRENT_BANK_USER.user_id,
      display_name: CURRENT_BANK_USER.display_name,
      role: initialSelfAssignmentRole(mode),
      role_label: CURRENT_BANK_USER_ROLE_LABEL,
      position_title: null,
      status_text: CURRENT_BANK_USER_STATUS,
      status_color_key: 'BLACK',
      assignment_eligible: true,
      isSelf: true,
    };
  }
  recommendationResult.selected.forEach(({ person, recommendation }) => {
    if (!selected[person.user_id]) {
      selected[person.user_id] = {
        ...person,
        role: recommendation.recommendationRole,
      };
    }
  });
  return {
    recommendations: recommendationResult.recommendations,
    missingRecommendationRoles: recommendationResult.missingRoles,
    initialMemberIds: memberList.map((member) => member.user_id),
    selected,
  };
};

export const CaseAssignmentDialog: React.FC<Props> = ({ caseId, mode = 'initial', onAssigned, onSaved, onClose, initialRecommendation = false }) => {
  const [staff, setStaff] = useState<BankStaff[]>([]); const [members, setMembers] = useState<CaseMember[]>([]); const [selected, setSelected] = useState<Record<string, Assignment>>({});
  const [loading, setLoading] = useState(true); const [saving, setSaving] = useState(false); const [error, setError] = useState(''); const [query, setQuery] = useState(''); const [nameSort, setNameSort] = useState<NameSort>('ASC'); const [roleFilter, setRoleFilter] = useState('ALL');
  const [recommendations, setRecommendations] = useState<Record<string, Recommendation>>({}); const [missingRecommendationRoles, setMissingRecommendationRoles] = useState<CaseAssignmentRole[]>([]); const [initialMemberIds, setInitialMemberIds] = useState<string[]>([]);

  const readAssignmentData = useCallback(async () => {
    const [staffList, memberList] = await Promise.all([casesApi.listBankStaff(), casesApi.members(caseId)]);
    return { staffList, memberList, snapshot: buildAssignmentSnapshot(staffList, memberList, mode, initialRecommendation) };
  }, [caseId, initialRecommendation, mode]);

  const applyAssignmentData = useCallback((data: Awaited<ReturnType<typeof readAssignmentData>>) => {
    setStaff(data.staffList);
    setMembers(data.memberList);
    setInitialMemberIds(data.snapshot.initialMemberIds);
    setRecommendations(data.snapshot.recommendations);
    setMissingRecommendationRoles(data.snapshot.missingRecommendationRoles);
    setSelected(data.snapshot.selected);
  }, [readAssignmentData]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    void readAssignmentData().then((data) => {
      if (active) applyAssignmentData(data);
    }).catch(() => {
      if (active) setError('담당자 목록을 불러오지 못했습니다. 다시 시도해 주세요.');
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [applyAssignmentData, readAssignmentData]);

  const selfAssignment = selected[CURRENT_BANK_USER.user_id] ?? { user_id: CURRENT_BANK_USER.user_id, display_name: CURRENT_BANK_USER.display_name, role: initialSelfAssignmentRole(mode), role_label: CURRENT_BANK_USER_ROLE_LABEL, position_title: null, status_text: CURRENT_BANK_USER_STATUS, status_color_key: 'BLACK' as BankStaffColor, assignment_eligible: true, isSelf: true };
  const people = useMemo(() => { const byId = new Map<string, Assignment>(); byId.set(CURRENT_BANK_USER.user_id, { ...selfAssignment, isSelf: true }); staff.forEach((item) => { const person = staffAssignment(item); byId.set(person.user_id, { ...person, ...recommendations[person.user_id], role: selected[person.user_id]?.role ?? (person.isSelf ? initialSelfAssignmentRole(mode) : 'HANDOVER_PENDING'), isSelf: person.user_id === CURRENT_BANK_USER.user_id }); }); members.forEach((member) => { if (!byId.has(member.user_id)) byId.set(member.user_id, selected[member.user_id] ?? { user_id: member.user_id, display_name: member.display_name, role: roleForMember(member), role_label: '직원 정보 없음', position_title: null, status_text: '직원 정보 없음', status_color_key: 'GRAY', assignment_eligible: true }); }); return Array.from(byId.values()); }, [members, mode, recommendations, selfAssignment, selected, staff]);
  const assignedPeople = useMemo(() => people.filter((person) => Boolean(selected[person.user_id])), [people, selected]);
  const roleFilterOptions = useMemo(() => Array.from(new Set(people.map((person) => person.role_label.trim()).filter(Boolean))).sort((left, right) => left.localeCompare(right, 'ko-KR')), [people]);
  const matches = (person: Assignment) => { const needle = query.trim().toLowerCase(); return (roleFilter === 'ALL' || person.role_label === roleFilter) && (!needle || `${person.display_name} ${person.role_label} ${person.position_title ?? ''} ${person.status_text} ${person.assignment_eligible ? 'Case 배정 가능' : '배정 제외'}`.toLowerCase().includes(needle)); };
  const sortPeople = (items: Assignment[]) => [...items].filter(matches).sort((left, right) => Number(left.assignment_eligible) - Number(right.assignment_eligible) || (nameSort === 'ASC' ? left.display_name.localeCompare(right.display_name, 'ko-KR') : right.display_name.localeCompare(left.display_name, 'ko-KR')) || left.user_id.localeCompare(right.user_id));
  const filteredPeople = useMemo(() => sortPeople(people), [people, query, roleFilter, nameSort]); const filteredAssignedPeople = useMemo(() => sortPeople(assignedPeople), [assignedPeople, query, roleFilter, nameSort]);
  const toggle = (person: Assignment) => { if (person.isSelf || (!person.assignment_eligible && !selected[person.user_id])) return; setSelected((current) => { const next = { ...current }; if (next[person.user_id]) delete next[person.user_id]; else next[person.user_id] = person; return next; }); };
  const setRole = (userId: string, role: CaseAssignmentRole) => setSelected((current) => { if (!current[userId]) return current; const next = { ...current }; if (role === 'SUPERVISOR') Object.keys(next).forEach((id) => { if (id !== userId && next[id].role === 'SUPERVISOR') next[id] = { ...next[id], role: 'HANDOVER_PENDING' }; }); next[userId] = { ...next[userId], role }; return next; });
  const recommendAssignments = () => {
    if (mode !== 'edit' || loading || !staff.length) return;
    const result = buildRecommendations(staff);
    const occupiedRoles = new Set(Object.values(selected).map((person) => person.role));
    setRecommendations(result.recommendations);
    setMissingRecommendationRoles(result.missingRoles.filter((role) => !occupiedRoles.has(role)));
    setSelected((current) => {
      const next = { ...current };
      const roles = new Set(Object.values(next).map((person) => person.role));
      const recommendedPeople = [...result.selected];
      if (!roles.has('SUPERVISOR')) {
        const supervisor = Object.entries(result.recommendations).find(([, recommendation]) => recommendation.recommendationRole === 'SUPERVISOR');
        const supervisorPerson = supervisor ? staff.map(staffAssignment).find((person) => person.user_id === supervisor[0]) : undefined;
        if (supervisorPerson) recommendedPeople.unshift({ person: supervisorPerson, recommendation: { recommendationRole: 'SUPERVISOR' } });
      }
      recommendedPeople.forEach(({ person, recommendation }) => {
        if (next[person.user_id] || roles.has(recommendation.recommendationRole)) return;
        next[person.user_id] = { ...person, role: recommendation.recommendationRole };
        roles.add(recommendation.recommendationRole);
      });
      return next;
    });
    setError('');
  };

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    const assignments = Object.values(selected);
    const supervisors = assignments.filter((item) => item.role === 'SUPERVISOR');
    if (!assignments.length) { setError('한 명 이상의 담당자를 선택해 주세요.'); return; }
    if (supervisors.length !== 1) { setError('사건 총괄을 한 명 선택해 주세요.'); return; }
    setSaving(true); setError('');
    try {
      for (const item of assignments) {
        await casesApi.upsertMember(caseId, { user_id: item.user_id, display_name: item.display_name, assignment_role: item.role });
      }
      await casesApi.setPrimaryAssignee(caseId, supervisors[0].display_name);
      if (mode === 'edit') {
        const selectedIds = new Set(assignments.map((item) => item.user_id));
        for (const userId of initialMemberIds) {
          if (userId !== CURRENT_BANK_USER.user_id && !selectedIds.has(userId)) await casesApi.removeMember(caseId, userId);
        }
        await onSaved?.();
      } else {
        await onAssigned?.();
      }
    } catch {
      setError('케이스 담당자 저장에 실패했습니다. 서버에 반영된 내용을 다시 불러왔습니다. 확인 후 재시도해 주세요.');
      try {
        const data = await readAssignmentData();
        applyAssignmentData(data);
      } catch {
        setError('케이스 담당자 저장에 실패했고 최신 담당자 목록도 불러오지 못했습니다. 다시 시도해 주세요.');
      }
    } finally {
      setSaving(false);
    }
  };
  const renderPersonDetails = (person: Assignment) => <div className="case-assignment-person-details"><div className="case-assignment-person-primary"><span className="case-assignment-status" data-color={person.isSelf ? 'BLACK' : person.status_color_key}>{person.status_text}</span><strong>{person.display_name}</strong>{person.isSelf && <em>나</em>}</div><div className="case-assignment-person-secondary"><span className="case-assignment-role-text">{person.role_label}{person.position_title ? ` · ${person.position_title}` : ''}</span><span className={person.assignment_eligible ? 'case-assignment-eligible' : 'case-assignment-ineligible'}>{person.assignment_eligible ? 'Case 배정 가능' : '배정 제외'}</span></div></div>;
  const count = (visible: Assignment[], all: Assignment[]) => visible.length === all.length ? `${all.length}명` : `${visible.length}/${all.length}명`;

  return <div className="case-assignment-overlay">
    <section className={`case-assignment-dialog ${mode === 'edit' ? 'case-assignment-edit' : ''}`} role="dialog" aria-modal="true" aria-labelledby="case-assignment-title">
      <div className="case-assignment-dialog-top"><div><div className="case-assignment-icon"><Users size={24}/></div><p className="eyebrow">CASE ASSIGNMENT</p></div>{mode === 'edit' && <button type="button" className="case-assignment-close" onClick={onClose} aria-label="담당자 관리 닫기"><X size={20}/></button>}</div>
      <div className="case-assignment-title-row"><h2 id="case-assignment-title">{mode === 'edit' ? '케이스 담당자 관리' : '케이스 담당자 배정'}</h2>{mode === 'edit' && <button type="button" className="case-assignment-recommend" onClick={recommendAssignments} disabled={loading || saving || !staff.length}>담당자 추천 배정 받기</button>}</div>
      <p className="case-assignment-description">{mode === 'edit' ? '이 케이스의 담당자와 배정 역할을 관리하세요.' : '직원을 선택해 이 케이스에서 맡을 역할을 지정하세요.'}</p>
      {loading ? <div className="case-assignment-loading"><Loader2 className="spin" size={20}/>담당자 목록을 불러오는 중입니다.</div> : <form onSubmit={save}>
        {missingRecommendationRoles.length > 0 && <p className="case-assignment-recommendation-note">자동 추천할 수 없는 역할: {missingRecommendationRoles.map(roleLabel).join(' · ')} · 담당자 추가 필요</p>}
        <div className="case-assignment-filters"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="이름·역할·직위·상태 검색" aria-label="직원 검색"/><label>직책<select value={roleFilter} onChange={(event) => setRoleFilter(event.target.value)} aria-label="직책 필터"><option value="ALL">전체 직책</option>{roleFilterOptions.map((role) => <option key={role} value={role}>{role}</option>)}</select></label><label>이름 정렬<select value={nameSort} onChange={(event) => setNameSort(event.target.value as NameSort)} aria-label="이름 정렬"><option value="ASC">가나다순</option><option value="DESC">가나다 역순</option></select></label></div>
        <div className="case-assignment-columns">
          <section className="case-assignment-column"><header><div><h3>전체 직원</h3><small>카드를 눌러 담당자를 추가하세요.</small></div><span>{count(filteredPeople, people)}</span></header><div className="case-assignment-list">{filteredPeople.length === 0 ? <div className="case-assignment-empty"><Users size={22}/><p>조건에 맞는 직원이 없습니다.</p><small>검색어나 필터를 바꿔 다시 확인해 주세요.</small></div> : filteredPeople.map((person) => { const checked = Boolean(selected[person.user_id]); const disabled = !person.isSelf && !person.assignment_eligible && !checked; return <article className={`case-assignment-person ${checked ? 'selected' : ''} ${disabled ? 'disabled' : ''}`} key={person.user_id} role="button" tabIndex={disabled ? -1 : 0} aria-pressed={checked} onClick={() => toggle(person)} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); toggle(person); } }}><label onClick={(event) => event.stopPropagation()}><input type="checkbox" checked={checked} onChange={() => toggle(person)} disabled={saving || disabled || Boolean(person.isSelf)}/><span className="case-assignment-checkmark">{checked && <Check size={13}/>}</span></label>{renderPersonDetails(person)}</article>; })}</div></section>
          <section className="case-assignment-column case-assignment-cart"><header><div><h3>배정된 담당자</h3><small>이 케이스의 담당자와 배정 역할입니다.</small></div><span>{count(filteredAssignedPeople, assignedPeople)}</span></header><div className="case-assignment-list">{assignedPeople.length === 0 ? <div className="case-assignment-empty"><Users size={22}/><p>아직 배정된 담당자가 없습니다.</p><small>왼쪽 직원 카드를 눌러 추가하세요.</small></div> : filteredAssignedPeople.length === 0 ? <div className="case-assignment-empty"><Users size={22}/><p>조건에 맞는 배정 담당자가 없습니다.</p><small>검색어나 필터를 바꿔 다시 확인해 주세요.</small></div> : filteredAssignedPeople.map((person) => <article className="case-assignment-assigned-card" key={person.user_id}>{renderPersonDetails(person)}<div className="case-assignment-assigned-controls"><label>배정 역할<select value={selected[person.user_id].role} onChange={(event) => setRole(person.user_id, event.target.value as CaseAssignmentRole)} disabled={saving} onClick={(event) => event.stopPropagation()}>{roleOptions.map((role) => <option key={role.value} value={role.value}>{role.label}</option>)}</select></label><button type="button" onClick={() => toggle(person)} disabled={saving || Boolean(person.isSelf)} aria-label={person.isSelf ? '현재 사용자는 제거할 수 없습니다' : `${person.display_name} 배정 제거`}><X size={15}/></button></div></article>)}</div></section>
        </div>
        {error && <p className="case-assignment-error">{error}</p>}<button type="submit" className="primary" disabled={saving || !assignedPeople.length}>{saving ? '저장 중…' : mode === 'edit' ? '담당자 변경 저장' : '담당자 배정 후 케이스 열기'}</button>
      </form>}
    </section>
  </div>;
};
