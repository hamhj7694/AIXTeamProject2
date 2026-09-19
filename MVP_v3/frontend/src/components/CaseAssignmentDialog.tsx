import React, { useEffect, useMemo, useState } from 'react';
import { Check, Loader2, Users, X } from 'lucide-react';
import { casesApi, CURRENT_BANK_USER, CURRENT_BANK_USER_ROLE_LABEL, CURRENT_BANK_USER_STATUS } from '../api/cases';
import type { BankStaff, BankStaffColor, CaseAssignmentRole, CaseMember, CaseMemberRole } from '../api/types';

interface Props { caseId: string; onAssigned: () => Promise<void>; onSkip: () => void; initialRecommendation?: boolean }
type Assignment = {
  user_id: string;
  display_name: string;
  role: CaseAssignmentRole;
  role_label: string;
  position_title: string | null;
  status_text: string;
  status_color_key: BankStaffColor;
  assignment_eligible: boolean;
  isSelf?: boolean;
  isRecommended?: boolean;
  recommendationRole?: CaseAssignmentRole;
  recommendationReason?: string;
};
type NameSort = 'ASC' | 'DESC';
type Recommendation = { isRecommended: true; recommendationRole: CaseAssignmentRole; recommendationReason: string };

const roleOptions: Array<{ value: CaseAssignmentRole; label: string; permission: CaseMemberRole }> = [
  { value: 'SUPERVISOR', label: '사건 총괄', permission: 'CASE_OWNER' },
  { value: 'MONITORING', label: '모니터링', permission: 'REVIEWER' },
  { value: 'CONSULTATION', label: '상담·대응', permission: 'CHAT_OPERATOR' },
  { value: 'VIEWER', label: '기타 열람자', permission: 'VIEWER' },
  { value: 'HANDOVER_PENDING', label: '인수인계 대기자', permission: 'VIEWER' },
];
const roleForMember = (member: CaseMember): CaseAssignmentRole => member.assignment_role ?? (member.role === 'CASE_OWNER' ? 'SUPERVISOR' : member.role === 'REVIEWER' ? 'MONITORING' : member.role === 'CHAT_OPERATOR' ? 'CONSULTATION' : 'HANDOVER_PENDING');
const roleLabel = (role: CaseAssignmentRole) => roleOptions.find((item) => item.value === role)?.label ?? '인수인계 대기자';
const recommendationConfigs: Array<{ role: CaseAssignmentRole; keywords: string[] }> = [
  { role: 'SUPERVISOR', keywords: ['금융사기 대응', '사고 조사', '고객 보호', '총괄', '책임'] },
  { role: 'MONITORING', keywords: ['fds', '모니터링', '보안'] },
  { role: 'CONSULTATION', keywords: ['고객 상담', '상담', '대응', '고객 보호', '금융사기 대응'] },
];
const activeStatuses = new Set(['근무 중', '업무 중', '회의 중', '교대 대기 중']);
const positionKeywords = ['본부장', '센터장', '실장', '팀장', '부장', '차장', '과장', '대리', '주임', '사원'];
const normalizedText = (value: string | null | undefined) => (value || '').trim().toLowerCase();
const positionRank = (title: string | null) => {
  const index = positionKeywords.findIndex((keyword) => normalizedText(title).includes(keyword.toLowerCase()));
  return index < 0 ? 0 : positionKeywords.length - index;
};
const statusRank = (person: Assignment) => activeStatuses.has(person.status_text.trim()) ? 2 : person.assignment_eligible ? 1 : 0;

const staffAssignment = (item: BankStaff): Assignment => {
  const userId = item.is_self || item.linked_user_id === CURRENT_BANK_USER.user_id ? CURRENT_BANK_USER.user_id : item.linked_user_id || item.staff_id;
  const isSelf = userId === CURRENT_BANK_USER.user_id;
  return {
  user_id: userId,
  display_name: isSelf ? CURRENT_BANK_USER.display_name : item.display_name,
  role: 'HANDOVER_PENDING',
  role_label: isSelf ? CURRENT_BANK_USER_ROLE_LABEL : item.role_label,
  position_title: item.position_title || null,
  status_text: isSelf ? CURRENT_BANK_USER_STATUS : item.status_text,
  status_color_key: isSelf ? 'GREEN' : item.status_color_key,
  assignment_eligible: isSelf ? true : item.assignment_eligible,
  };
};

const buildRecommendations = (staffList: BankStaff[]) => {
  const candidates = staffList.map(staffAssignment).filter((person) => !person.isSelf && person.assignment_eligible);
  const used = new Set<string>([CURRENT_BANK_USER.user_id]);
  const recommendations: Record<string, Recommendation> = {};
  const selected: Array<{ person: Assignment; recommendation: Recommendation }> = [];
  const missingRoles: CaseAssignmentRole[] = [];
  for (const config of recommendationConfigs) {
    const available = candidates.filter((person) => !used.has(person.user_id));
    if (!available.length) { if (config.role !== 'SUPERVISOR') missingRoles.push(config.role); continue; }
    const related = available.filter((person) => config.keywords.some((keyword) => normalizedText(`${person.role_label} ${person.position_title}`).includes(keyword.toLowerCase())));
    const pool = related.length ? related : available;
    const randomTieBreak = new Map(pool.map((person) => [person.user_id, Math.random()]));
    const ranked = [...pool].sort((left, right) => {
      const relatedDifference = Number(related.includes(right)) - Number(related.includes(left));
      if (relatedDifference) return relatedDifference;
      const statusDifference = statusRank(right) - statusRank(left);
      if (statusDifference) return statusDifference;
      const positionDifference = positionRank(right.position_title) - positionRank(left.position_title);
      if (positionDifference && (config.role === 'SUPERVISOR' || config.role === 'MONITORING')) return positionDifference;
      return (randomTieBreak.get(left.user_id) || 0) - (randomTieBreak.get(right.user_id) || 0);
    });
    const person = ranked[0];
    const isRelated = related.includes(person);
    const recommendation: Recommendation = {
      isRecommended: true,
      recommendationRole: config.role,
      recommendationReason: isRelated ? `관련 직책 우선 · ${person.role_label}` : '관련 직책 없음 · 배정 가능 상태·직위 기준 추천',
    };
    recommendations[person.user_id] = recommendation;
    used.add(person.user_id);
    if (config.role !== 'SUPERVISOR') selected.push({ person, recommendation });
  }
  if (!recommendations || !selected.length) {
    recommendationConfigs.filter((config) => config.role !== 'SUPERVISOR').forEach((config) => { if (!selected.some((item) => item.recommendation.recommendationRole === config.role)) missingRoles.push(config.role); });
  }
  return { recommendations, selected, missingRoles: Array.from(new Set(missingRoles)) };
};

export const CaseAssignmentDialog: React.FC<Props> = ({ caseId, onAssigned, onSkip, initialRecommendation = false }) => {
  const [staff, setStaff] = useState<BankStaff[]>([]);
  const [members, setMembers] = useState<CaseMember[]>([]);
  const [selected, setSelected] = useState<Record<string, Assignment>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [nameSort, setNameSort] = useState<NameSort>('ASC');
  const [roleFilter, setRoleFilter] = useState('ALL');
  const [recommendations, setRecommendations] = useState<Record<string, Recommendation>>({});
  const [missingRecommendationRoles, setMissingRecommendationRoles] = useState<CaseAssignmentRole[]>([]);

  useEffect(() => { void (async () => {
    try {
      const [staffList, memberList] = await Promise.all([casesApi.listBankStaff(), casesApi.members(caseId)]);
      setStaff(staffList); setMembers(memberList);
      const recommendationResult = initialRecommendation ? buildRecommendations(staffList) : { recommendations: {}, selected: [], missingRoles: [] as CaseAssignmentRole[] };
      setRecommendations(recommendationResult.recommendations); setMissingRecommendationRoles(recommendationResult.missingRoles);
      const byUserId = new Map(staffList.map((item) => { const person = staffAssignment(item); return [person.user_id, person]; }));
      const initial: Record<string, Assignment> = {};
      memberList.forEach((member) => {
        const metadata = byUserId.get(member.user_id);
        initial[member.user_id] = {
          ...(metadata ?? { user_id: member.user_id, display_name: member.user_id === CURRENT_BANK_USER.user_id ? CURRENT_BANK_USER.display_name : member.display_name, role_label: member.user_id === CURRENT_BANK_USER.user_id ? CURRENT_BANK_USER_ROLE_LABEL : '은행 담당자', position_title: null, status_text: member.user_id === CURRENT_BANK_USER.user_id ? CURRENT_BANK_USER_STATUS : '상태 확인 필요', status_color_key: member.user_id === CURRENT_BANK_USER.user_id ? 'GREEN' as BankStaffColor : 'GRAY' as BankStaffColor, assignment_eligible: true }),
          user_id: member.user_id,
          display_name: member.user_id === CURRENT_BANK_USER.user_id ? CURRENT_BANK_USER.display_name : member.display_name,
          role: member.user_id === CURRENT_BANK_USER.user_id ? 'SUPERVISOR' : roleForMember(member),
          isSelf: member.user_id === CURRENT_BANK_USER.user_id,
        };
      });
      if (!initial[CURRENT_BANK_USER.user_id]) initial[CURRENT_BANK_USER.user_id] = {
        user_id: CURRENT_BANK_USER.user_id, display_name: CURRENT_BANK_USER.display_name, role: 'SUPERVISOR', role_label: CURRENT_BANK_USER_ROLE_LABEL, position_title: null, status_text: CURRENT_BANK_USER_STATUS, status_color_key: 'GREEN', assignment_eligible: true, isSelf: true,
      };
      recommendationResult.selected.forEach(({ person, recommendation }) => {
        if (!initial[person.user_id]) initial[person.user_id] = { ...person, role: recommendation.recommendationRole, ...recommendation };
      });
      setSelected(initial);
    } catch { setError('담당자 목록을 불러오지 못했습니다. 다시 시도해 주세요.'); }
    finally { setLoading(false); }
  })(); }, [caseId, initialRecommendation]);

  const selfAssignment = selected[CURRENT_BANK_USER.user_id] ?? { user_id: CURRENT_BANK_USER.user_id, display_name: CURRENT_BANK_USER.display_name, role: 'SUPERVISOR' as CaseAssignmentRole, role_label: CURRENT_BANK_USER_ROLE_LABEL, position_title: null, status_text: CURRENT_BANK_USER_STATUS, status_color_key: 'GREEN' as BankStaffColor, assignment_eligible: true, isSelf: true };
  const people = useMemo(() => {
    const byId = new Map<string, Assignment>();
    byId.set(CURRENT_BANK_USER.user_id, { ...selfAssignment, isSelf: true });
    staff.forEach((item) => {
      const person = staffAssignment(item);
      byId.set(person.user_id, { ...person, ...recommendations[person.user_id], role: selected[person.user_id]?.role ?? 'HANDOVER_PENDING', isSelf: person.user_id === CURRENT_BANK_USER.user_id });
    });
    members.forEach((member) => {
      if (!byId.has(member.user_id)) byId.set(member.user_id, selected[member.user_id] ?? { user_id: member.user_id, display_name: member.user_id === CURRENT_BANK_USER.user_id ? CURRENT_BANK_USER.display_name : member.display_name, role: roleForMember(member), role_label: member.user_id === CURRENT_BANK_USER.user_id ? CURRENT_BANK_USER_ROLE_LABEL : '은행 담당자', position_title: null, status_text: member.user_id === CURRENT_BANK_USER.user_id ? CURRENT_BANK_USER_STATUS : '상태 확인 필요', status_color_key: member.user_id === CURRENT_BANK_USER.user_id ? 'GREEN' : 'GRAY', assignment_eligible: true });
    });
    return Array.from(byId.values());
  }, [members, recommendations, selfAssignment, selected, staff]);
  const assignedPeople = useMemo(() => people.filter((person) => Boolean(selected[person.user_id])), [people, selected]);
  const roleFilterOptions = useMemo(() => Array.from(new Set(people.map((person) => person.role_label.trim()).filter(Boolean))).sort((left, right) => left.localeCompare(right, 'ko-KR')), [people]);
  const filteredPeople = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const matched = people.filter((person) => {
      if (roleFilter !== 'ALL' && person.role_label !== roleFilter) return false;
      if (!needle) return true;
      const eligibilityText = person.assignment_eligible ? 'case 배정 가능 배정 가능 가능' : '배정 제외 배정 불가 제외';
      return `${person.display_name} ${person.role_label} ${person.position_title ?? ''} ${person.status_text} ${eligibilityText}`.toLowerCase().includes(needle);
    });
    return matched.sort((left, right) => {
      const eligibilityDifference = Number(right.assignment_eligible) - Number(left.assignment_eligible);
      if (eligibilityDifference) return eligibilityDifference;
      const compared = left.display_name.localeCompare(right.display_name, 'ko-KR', { sensitivity: 'base' });
      return nameSort === 'ASC' ? compared || left.user_id.localeCompare(right.user_id) : -compared || -left.user_id.localeCompare(right.user_id);
    });
  }, [nameSort, people, query, roleFilter]);
  const filteredAssignedPeople = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const matched = assignedPeople.filter((person) => {
      if (roleFilter !== 'ALL' && person.role_label !== roleFilter) return false;
      if (!needle) return true;
      const eligibilityText = person.assignment_eligible ? 'case 배정 가능 배정 가능 가능' : '배정 제외 배정 불가 제외';
      return `${person.display_name} ${person.role_label} ${person.position_title ?? ''} ${person.status_text} ${eligibilityText}`.toLowerCase().includes(needle);
    });
    return matched.sort((left, right) => {
      const eligibilityDifference = Number(right.assignment_eligible) - Number(left.assignment_eligible);
      if (eligibilityDifference) return eligibilityDifference;
      const compared = left.display_name.localeCompare(right.display_name, 'ko-KR', { sensitivity: 'base' });
      return nameSort === 'ASC' ? compared || left.user_id.localeCompare(right.user_id) : -compared || -left.user_id.localeCompare(right.user_id);
    });
  }, [assignedPeople, nameSort, query, roleFilter]);

  const toggle = (person: Assignment) => {
    if (person.isSelf || (!person.assignment_eligible && !selected[person.user_id])) return;
    setSelected((current) => { const next = { ...current }; if (next[person.user_id]) delete next[person.user_id]; else next[person.user_id] = person; return next; });
  };
  const setRole = (userId: string, role: CaseAssignmentRole) => setSelected((current) => {
    if (!current[userId]) return current;
    const next = { ...current };
    if (role === 'SUPERVISOR') Object.keys(next).forEach((id) => { if (id !== userId && next[id].role === 'SUPERVISOR') next[id] = { ...next[id], role: 'HANDOVER_PENDING' }; });
    next[userId] = { ...next[userId], role };
    return next;
  });
  const handlePersonKeyDown = (event: React.KeyboardEvent, person: Assignment) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); toggle(person); } };
  const assign = async (event: React.FormEvent) => {
    event.preventDefault();
    const assignments = Object.values(selected);
    if (!assignments.length) { setError('한 명 이상의 담당자를 선택해 주세요.'); return; }
    const supervisors = assignments.filter((item) => item.role === 'SUPERVISOR');
    if (supervisors.length !== 1) { setError('사건 총괄을 한 명 선택해 주세요.'); return; }
    setSaving(true); setError('');
    try {
      for (const item of assignments) {
        const option = roleOptions.find((role) => role.value === item.role)!;
        await casesApi.upsertMember(caseId, { user_id: item.user_id, display_name: item.display_name, role: option.permission, assignment_role: item.role });
      }
      await casesApi.setPrimaryAssignee(caseId, supervisors[0]?.display_name ?? null);
      await onAssigned();
    } catch { setError('케이스 담당자 배정에 실패했습니다. 입력 내용을 확인한 후 다시 시도해 주세요.'); }
    finally { setSaving(false); }
  };

  const renderPersonDetails = (person: Assignment) => <div className="case-assignment-person-details"><div className="case-assignment-person-primary"><span className="case-assignment-status" data-color={person.isSelf ? 'BLACK' : person.status_color_key}>{person.status_text}</span>{person.isRecommended && <span className="case-assignment-recommendation" title={person.recommendationReason}>{person.recommendationRole === 'SUPERVISOR' ? '총괄 후보' : '직책 기반 추천'}</span>}<strong>{person.display_name}</strong>{person.isSelf && <em>나</em>}</div><div className="case-assignment-person-secondary"><span className="case-assignment-role-text">{person.role_label}{person.position_title ? ` · ${person.position_title}` : ''}</span><span className={person.assignment_eligible ? 'case-assignment-eligible' : 'case-assignment-ineligible'}>{person.assignment_eligible ? 'Case 배정 가능' : '배정 제외'}</span></div></div>;

  return <div className="case-assignment-overlay"><section className="case-assignment-dialog" role="dialog" aria-modal="true" aria-labelledby="case-assignment-title"><div className="case-assignment-icon"><Users size={24}/></div><p className="eyebrow">CASE ASSIGNMENT</p><h2 id="case-assignment-title">케이스 담당자 배정</h2><p className="case-assignment-description">직원을 선택해 이 케이스에서 맡을 역할을 지정하세요.</p>{loading ? <div className="case-assignment-loading"><Loader2 className="spin" size={20}/>담당자 목록을 불러오는 중입니다.</div> : <form onSubmit={assign}>{missingRecommendationRoles.length > 0 && <p className="case-assignment-recommendation-note">자동 추천할 수 없는 역할: {missingRecommendationRoles.map(roleLabel).join(' · ')} · 담당자 추가 필요</p>}<div className="case-assignment-filters"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="이름·역할·직위·상태 검색" aria-label="직원 검색"/><label>직책<select value={roleFilter} onChange={(event) => setRoleFilter(event.target.value)} aria-label="직책 필터"><option value="ALL">전체 직책</option>{roleFilterOptions.map((role) => <option key={role} value={role}>{role}</option>)}</select></label><label>이름 정렬<select value={nameSort} onChange={(event) => setNameSort(event.target.value as NameSort)} aria-label="이름 정렬"><option value="ASC">가나다순</option><option value="DESC">가나다 역순</option></select></label></div><div className="case-assignment-columns"><section className="case-assignment-column"><header><div><h3>전체 직원</h3><small>카드를 눌러 담당자를 추가하세요.</small></div><span>{filteredPeople.length === people.length ? `${people.length}명` : `${filteredPeople.length}/${people.length}명`}</span></header><div className="case-assignment-list">{filteredPeople.length === 0 ? <div className="case-assignment-empty"><Users size={22}/><p>조건에 맞는 직원이 없습니다.</p><small>검색어나 필터를 바꿔 다시 확인해 주세요.</small></div> : filteredPeople.map((person) => { const checked = Boolean(selected[person.user_id]); const disabled = !person.isSelf && !person.assignment_eligible && !checked; return <article className={`case-assignment-person ${checked ? 'selected' : ''} ${disabled ? 'disabled' : ''}`} key={person.user_id} role="button" tabIndex={disabled ? -1 : 0} aria-pressed={checked} onClick={() => toggle(person)} onKeyDown={(event) => handlePersonKeyDown(event, person)}><label onClick={(event) => event.stopPropagation()}><input type="checkbox" checked={checked} onChange={() => toggle(person)} disabled={saving || disabled || Boolean(person.isSelf)}/><span className="case-assignment-checkmark">{checked && <Check size={13}/>}</span></label>{renderPersonDetails(person)}</article>; })}</div></section><section className="case-assignment-column case-assignment-cart"><header><div><h3>배정된 담당자</h3><small>이 케이스의 담당자와 역할입니다.</small></div><span>{filteredAssignedPeople.length === assignedPeople.length ? `${assignedPeople.length}명` : `${filteredAssignedPeople.length}/${assignedPeople.length}명`}</span></header><div className="case-assignment-list">{assignedPeople.length === 0 ? <div className="case-assignment-empty"><Users size={22}/><p>아직 배정된 담당자가 없습니다.</p><small>왼쪽 직원 카드를 눌러 추가하세요.</small></div> : filteredAssignedPeople.length === 0 ? <div className="case-assignment-empty"><Users size={22}/><p>조건에 맞는 배정 담당자가 없습니다.</p><small>검색어나 필터를 바꿔 다시 확인해 주세요.</small></div> : filteredAssignedPeople.map((person) => <article className="case-assignment-assigned-card" key={person.user_id}>{renderPersonDetails(person)}<div className="case-assignment-assigned-controls"><label>배정 역할<select value={selected[person.user_id].role} onChange={(event) => setRole(person.user_id, event.target.value as CaseAssignmentRole)} disabled={saving} onClick={(event) => event.stopPropagation()}>{roleOptions.map((role) => <option key={role.value} value={role.value}>{role.label}</option>)}</select></label><button type="button" onClick={() => toggle(person)} disabled={saving || Boolean(person.isSelf)} aria-label={person.isSelf ? '나 담당자는 제거할 수 없습니다' : `${person.display_name} 배정 제거`}><X size={15}/></button></div></article>)}</div></section></div>{error && <p className="case-assignment-error">{error}</p>}<button type="submit" className="primary" disabled={saving || !assignedPeople.length}>{saving ? '배정 중…' : '담당자 배정 후 케이스 열기'}</button><button type="button" className="case-assignment-skip" onClick={onSkip} disabled={saving}>나중에 배정하고 케이스 열기</button></form>}</section></div>;
};
