import React, { useEffect, useMemo, useState } from 'react';
import { AlertCircle, Pencil, Plus, RefreshCw, Trash2, X } from 'lucide-react';
import { casesApi } from '../api/cases';
import type { BankStaff, BankStaffColor } from '../api/types';

interface Props { onClose: () => void }
type Draft = Omit<BankStaff, 'staff_id' | 'is_self' | 'created_at' | 'updated_at'>;
type View = 'list' | 'form';
type NameSort = 'ASC' | 'DESC';
const emptyDraft: Draft = { display_name: '', assignment_role: 'CONSULTATION', role_label: '고객 상담 담당자', position_title: '', status_text: '근무 중', status_color_key: 'GREEN', assignment_eligible: true, linked_user_id: null };
const rolePresets = ['FDS 모니터링 담당자', '고객 상담 담당자', '금융사기 대응 담당자', '사고 조사 담당자', '고객 보호 담당자', '보안 담당자'];
const positionPresets = ['사원', '주임', '대리', '과장', '차장', '부장', '팀장', '실장'];
const statusPresets = ['근무 중', '업무 중', '회의 중', '자리 비움', '휴가 중', '부재중', '교대 대기 중', '퇴근', '기타'];
const CUSTOM_OPTION = '__CUSTOM__';
const statusColorFor = (status: string): BankStaffColor => {
  const normalized = status.trim();
  if (normalized === '근무 중') return 'GREEN';
  if (normalized === '업무 중' || normalized === '회의 중') return 'BLUE';
  if (normalized === '자리 비움' || normalized === '휴가 중') return 'ORANGE';
  if (normalized === '부재중' || normalized === '교대 대기 중') return 'RED';
  return 'GRAY';
};
const assignmentEligibleForStatus = (status: string): boolean | null => {
  if (['근무 중', '업무 중', '회의 중', '교대 대기 중'].includes(status)) return true;
  if (['자리 비움', '휴가 중', '부재중', '퇴근'].includes(status)) return false;
  return null;
};
export const BankStaffManager: React.FC<Props> = ({ onClose }) => {
  const [items, setItems] = useState<BankStaff[]>([]);
  const [draft, setDraft] = useState<Draft>({ ...emptyDraft });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [positionCustom, setPositionCustom] = useState(false);
  const [roleCustom, setRoleCustom] = useState(false);
  const [view, setView] = useState<View>('list');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [nameSort, setNameSort] = useState<NameSort>('ASC');
  const [roleFilter, setRoleFilter] = useState('ALL');
  const load = async () => { setLoading(true); setError(''); try { setItems(await casesApi.listBankStaff()); } catch { setError('은행 담당자 목록을 불러오지 못했습니다.'); } finally { setLoading(false); } };
  useEffect(() => { void load(); }, []);
  const roleOptions = useMemo(() => Array.from(new Set(items.map((item) => item.role_label.trim()).filter(Boolean))).sort((left, right) => left.localeCompare(right, 'ko-KR')), [items]);
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const matched = items.filter((item) => {
      if (roleFilter !== 'ALL' && item.role_label !== roleFilter) return false;
      if (!needle) return true;
      const assignmentSearch = item.assignment_eligible
        ? 'case 배정 가능 배정 가능 가능'
        : 'case 배정 불가능 배정 제외 불가능 제외';
      return `${item.display_name} ${item.role_label} ${item.position_title || ''} ${item.status_text} ${assignmentSearch}`.toLowerCase().includes(needle);
    });
    return matched.sort((left, right) => {
      const compared = left.display_name.localeCompare(right.display_name, 'ko-KR', { sensitivity: 'base' });
      return nameSort === 'ASC' ? compared || left.staff_id.localeCompare(right.staff_id) : -compared || -left.staff_id.localeCompare(right.staff_id);
    });
  }, [items, nameSort, query, roleFilter]);
  const reset = () => { setDraft({ ...emptyDraft }); setEditingId(null); setPositionCustom(false); setRoleCustom(false); setView('list'); };
  const beginCreate = () => { setDraft({ ...emptyDraft }); setEditingId(null); setPositionCustom(false); setRoleCustom(false); setError(''); setView('form'); };
  const beginEdit = (item: BankStaff) => { setEditingId(item.staff_id); setPositionCustom(Boolean(item.position_title && !positionPresets.includes(item.position_title))); setRoleCustom(Boolean(item.role_label && !rolePresets.includes(item.role_label))); setDraft({ display_name: item.display_name, assignment_role: item.assignment_role, role_label: item.role_label, position_title: item.position_title || '', status_text: item.status_text, status_color_key: statusColorFor(item.status_text), assignment_eligible: item.assignment_eligible, linked_user_id: item.linked_user_id || null }); setError(''); setView('form'); };
  const updateDraft = <K extends keyof Draft>(key: K, value: Draft[K]) => setDraft((current) => ({ ...current, [key]: value }));
  const save = async (event: React.FormEvent) => { event.preventDefault(); if (!draft.display_name.trim() || !draft.role_label.trim()) return; setSaving(true); setError(''); try { const normalized = { ...draft, display_name: draft.display_name.trim(), role_label: draft.role_label.trim(), position_title: draft.position_title?.trim() || null, status_text: draft.status_text.trim() || '근무 중' }; const saved = editingId ? await casesApi.updateBankStaff(editingId, normalized) : await casesApi.createBankStaff(normalized); setItems((current) => editingId ? current.map((item) => item.staff_id === saved.staff_id ? saved : item) : [...current, saved]); reset(); } catch { setError('은행 담당자 정보를 저장하지 못했습니다.'); } finally { setSaving(false); } };
  const remove = async (item: BankStaff) => { if (!window.confirm(`${item.display_name} 담당자를 삭제할까요?`)) return; setSaving(true); setError(''); try { await casesApi.deleteBankStaff(item.staff_id); setItems((current) => current.filter((row) => row.staff_id !== item.staff_id)); if (editingId === item.staff_id) reset(); } catch { setError('은행 담당자를 삭제하지 못했습니다.'); } finally { setSaving(false); } };

  return <div className="bank-staff-overlay" role="presentation"><section className="bank-staff-dialog" role="dialog" aria-modal="true" aria-labelledby="bank-staff-title">
    <header className="bank-staff-header"><div><p className="eyebrow">BANK STAFF DIRECTORY</p><h2 id="bank-staff-title">은행 담당자 관리</h2><small>Case와 무관하게 은행 전체 담당자를 등록하고 관리합니다.</small></div><button type="button" className="icon-button" onClick={onClose} aria-label="닫기"><X size={18}/></button></header>
    {view === 'list' ? <>
      <div className="bank-staff-toolbar"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="이름·역할·직위·상태·배정 가능 여부 검색"/><button type="button" onClick={() => void load()} disabled={loading}><RefreshCw size={14}/>새로고침</button></div>
      <div className="bank-staff-list-heading"><div><strong>은행 담당자</strong><span>{filtered.length === items.length ? items.length : `${filtered.length}/${items.length}`}명</span></div><button type="button" className="primary" onClick={beginCreate}><Plus size={15}/>담당자 추가</button></div>
      <div className="bank-staff-filter-row"><label htmlFor="bank-staff-role-filter">직책<select id="bank-staff-role-filter" value={roleFilter} onChange={(event) => setRoleFilter(event.target.value)}><option value="ALL">전체 직책</option>{roleOptions.map((role) => <option key={role} value={role}>{role}</option>)}</select></label><label htmlFor="bank-staff-name-sort">이름 정렬<select id="bank-staff-name-sort" value={nameSort} onChange={(event) => setNameSort(event.target.value as NameSort)}><option value="ASC">가나다순</option><option value="DESC">가나다 역순</option></select></label></div>
      {error && <p className="bank-staff-error" role="alert"><AlertCircle size={14}/><span>{error}</span><button type="button" onClick={() => void load()}>다시 시도</button></p>}
      <div className="bank-staff-list" aria-live="polite">{loading && <p className="bank-staff-empty">은행 담당자 목록을 불러오는 중입니다…</p>}{!loading && filtered.length === 0 && <p className="bank-staff-empty">{query || roleFilter !== 'ALL' ? '조건에 맞는 담당자가 없습니다.' : '등록된 은행 담당자가 없습니다.'}<br/><button type="button" onClick={beginCreate}>첫 담당자 등록</button></p>}{!loading && filtered.map((item) => <article className="bank-staff-card" key={item.staff_id}>
        <div className="bank-staff-card-main"><div className="bank-staff-card-line"><span className="bank-staff-status" data-color={item.status_color_key}>{item.status_text}</span><strong>{item.display_name}</strong>{item.is_self && <span className="bank-staff-self">본인</span>}<span className="bank-staff-role-text">{item.role_label}</span>{item.position_title && <span className="bank-staff-position-text">{item.position_title}</span>}<span className={item.assignment_eligible ? 'assignment-on' : 'assignment-off'}>{item.assignment_eligible ? 'Case 배정 가능' : '배정 제외'}</span></div></div>
        <div className="bank-staff-card-actions"><button type="button" onClick={() => beginEdit(item)} aria-label={`${item.display_name} 수정`}><Pencil size={13}/>수정</button><button type="button" className="danger" onClick={() => void remove(item)} disabled={saving} aria-label={`${item.display_name} 삭제`}><Trash2 size={13}/>삭제</button></div>
    </article>)}</div>
    </> : <form className="bank-staff-form" onSubmit={save}>
      <div className="bank-staff-form-heading"><div><button type="button" className="bank-staff-back" onClick={reset}>‹ 목록</button><h3>{editingId ? '담당자 수정' : '담당자 등록'}</h3><p>Case 배정과 운영에 사용할 담당자 정보를 입력하세요.</p></div></div>
      {error && <p className="bank-staff-error" role="alert"><AlertCircle size={14}/><span>{error}</span></p>}
      <label>이름 *<input required value={draft.display_name} maxLength={100} onChange={(event) => updateDraft('display_name', event.target.value)} placeholder="이름을 작성해 주세요" autoFocus/></label>
      <label>표시 직책 *<select value={roleCustom ? CUSTOM_OPTION : draft.role_label} onChange={(event) => { const custom = event.target.value === CUSTOM_OPTION; setRoleCustom(custom); updateDraft('role_label', custom ? '' : event.target.value); }}><option value="">선택해 주세요</option>{rolePresets.map((item) => <option key={item} value={item}>{item}</option>)}<option value={CUSTOM_OPTION}>직접 입력</option></select>{roleCustom && <input required value={draft.role_label} maxLength={100} onChange={(event) => updateDraft('role_label', event.target.value)} placeholder="직접 입력"/>}</label>
      <label>직위<select value={positionCustom ? CUSTOM_OPTION : (draft.position_title || '')} onChange={(event) => { const custom = event.target.value === CUSTOM_OPTION; setPositionCustom(custom); updateDraft('position_title', custom ? '' : event.target.value); }}><option value="">선택 안 함</option>{positionPresets.map((item) => <option key={item} value={item}>{item}</option>)}<option value={CUSTOM_OPTION}>직접 입력</option></select>{positionCustom && <input value={draft.position_title || ''} maxLength={100} onChange={(event) => updateDraft('position_title', event.target.value)} placeholder="직접 입력"/>}</label>
      <label>현재 상태<select value={statusPresets.includes(draft.status_text) ? draft.status_text : CUSTOM_OPTION} onChange={(event) => { const value = event.target.value === CUSTOM_OPTION ? '' : event.target.value; updateDraft('status_text', value); updateDraft('status_color_key', statusColorFor(value)); const eligible = assignmentEligibleForStatus(value); if (eligible !== null) updateDraft('assignment_eligible', eligible); }}>{statusPresets.map((item) => <option key={item} value={item}>{item}</option>)}<option value={CUSTOM_OPTION}>직접 입력</option></select>{(!statusPresets.includes(draft.status_text)) && <input value={draft.status_text} maxLength={80} onChange={(event) => { updateDraft('status_text', event.target.value); updateDraft('status_color_key', statusColorFor(event.target.value)); }} placeholder="직접 입력"/>}</label>
      <label className="bank-staff-check"><input type="checkbox" checked={draft.assignment_eligible} onChange={(event) => updateDraft('assignment_eligible', event.target.checked)}/><span><strong>Case 배정 가능</strong><small>새 사건을 이 담당자에게 배정할 수 있습니다.</small></span></label>
      <footer><button type="button" onClick={reset}>취소</button><button type="submit" className="primary" disabled={saving || !draft.display_name.trim() || !draft.role_label.trim()}>{saving ? '저장 중…' : editingId ? '수정 저장' : '담당자 등록'}</button></footer>
    </form>}
  </section></div>;
};
