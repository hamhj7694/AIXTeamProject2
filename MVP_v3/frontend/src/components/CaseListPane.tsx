import React, { useEffect, useMemo, useState } from 'react';
import { AlertCircle, ArrowDown, ArrowUp, Loader2, Pencil, Search, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import type { StoredCase } from '../api/types';
import { compareCases, type CaseSortField, type SortDirection } from '../caseSort';
import { caseState, caseStateLabel, caseStateTone, incidentTitle, relativeTime, statusLabel } from '../presentation';
import { isNewCase, markCaseOpened, newCaseStateEventName } from '../newCaseState';
import { analysisPendingEventName, getPendingAnalysisCount } from '../analysisQueue';

interface Props {
  cases: StoredCase[];
  selectedCaseId?: string;
  loading: boolean;
  error: string;
  mobileOpen: boolean;
  onCloseMobile: () => void;
  onRetry: () => void;
  trashCount: number;
  onOpenTrash: () => void;
  onSelectCase: () => void;
  onRenameCase: (caseId: string, caseName: string, expectedVersion: number) => Promise<void>;
}

export const CaseListPane: React.FC<Props> = ({ cases, selectedCaseId, loading, error, mobileOpen, onCloseMobile, onRetry, trashCount, onOpenTrash, onSelectCase, onRenameCase }) => {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [stateFilter, setStateFilter] = useState<'ALL' | 'LOSS' | 'SUSPECTED' | 'RESOLVED'>('ALL');
  const [status, setStatus] = useState<'ALL' | 'ACTIVE' | 'CLOSED'>('ALL');
  const [sortField, setSortField] = useState<CaseSortField>('UPDATED_AT');
  const [sortDirection, setSortDirection] = useState<SortDirection>('DESC');
  const [editingCaseId, setEditingCaseId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [renameBusy, setRenameBusy] = useState(false);
  const [renameError, setRenameError] = useState('');
  const [newCaseIds, setNewCaseIds] = useState<Set<string>>(() => new Set(cases.filter((item) => isNewCase(item.case_id)).map((item) => item.case_id)));
  React.useEffect(() => { setNewCaseIds(new Set(cases.filter((item) => isNewCase(item.case_id)).map((item) => item.case_id))); }, [cases]);
  React.useEffect(() => { const sync = () => setNewCaseIds(new Set(cases.filter((item) => isNewCase(item.case_id)).map((item) => item.case_id))); window.addEventListener(newCaseStateEventName, sync); return () => window.removeEventListener(newCaseStateEventName, sync); }, [cases]);
  const [pendingAnalysisCount, setPendingAnalysisCount] = useState(getPendingAnalysisCount);
  useEffect(() => {
    const syncPendingAnalysis = () => setPendingAnalysisCount(getPendingAnalysisCount());
    window.addEventListener(analysisPendingEventName, syncPendingAnalysis);
    syncPendingAnalysis();
    return () => window.removeEventListener(analysisPendingEventName, syncPendingAnalysis);
  }, []);
  const rows = useMemo(() => [...cases]
    .filter((item) => stateFilter === 'ALL' || caseState(item) === stateFilter)
    .filter((item) => status === 'ALL'
      || (status === 'ACTIVE' && item.status !== 'CLOSED' && item.mode !== 'CLOSED')
      || (status === 'CLOSED' && (item.status === 'CLOSED' || item.mode === 'CLOSED')))
    .filter((item) => `${item.case_id} ${incidentTitle(item)} ${item.initial_brief}`.toLowerCase().includes(query.trim().toLowerCase()))
    .sort((a, b) => compareCases(a, b, sortField, sortDirection)), [cases, query, stateFilter, status, sortField, sortDirection]);
  const openCase = (caseId: string) => { markCaseOpened(caseId); setNewCaseIds((current) => { const next = new Set(current); next.delete(caseId); return next; }); onSelectCase(); navigate(`/cases/${caseId}`); onCloseMobile(); };
  const startRename = (item: StoredCase) => { setEditingCaseId(item.case_id); setRenameValue(incidentTitle(item)); setRenameError(''); };
  const cancelRename = () => { if (renameBusy) return; setEditingCaseId(null); setRenameValue(''); setRenameError(''); };
  const saveRename = async (item: StoredCase) => {
    const nextName = renameValue.trim();
    if (!nextName) { setRenameError('사건 이름을 입력해 주세요.'); return; }
    setRenameBusy(true); setRenameError('');
    try { await onRenameCase(item.case_id, nextName, item.version); setEditingCaseId(null); setRenameValue(''); }
    catch (reason) { setRenameError(reason instanceof Error ? reason.message : '사건 이름을 변경하지 못했습니다.'); }
    finally { setRenameBusy(false); }
  };
  const renderCaseItem = (item: StoredCase) => {
    const editing = editingCaseId === item.case_id;
    const caseContent = <>
      <strong>{incidentTitle(item)}</strong>
      <span className="case-item-bottom"><span className="case-item-status">{statusLabel(item.status, item.mode)}</span><time className="case-item-created-time" title={new Date(item.created_at).toLocaleString('ko-KR')}>생성 {relativeTime(item.created_at)}</time><time className="case-item-updated-time" title={new Date(item.updated_at).toLocaleString('ko-KR')}>수정 {relativeTime(item.updated_at)}</time></span>
    </>;
    const selectFromCard = (event: React.MouseEvent<HTMLDivElement>) => {
      // The rename control is intentionally an exception: clicking it must not
      // navigate away from the inline editor.
      if ((event.target as HTMLElement).closest('button, form, input')) return;
      openCase(item.case_id);
    };
    const selectFromKeyboard = (event: React.KeyboardEvent<HTMLDivElement>) => {
      if (event.target !== event.currentTarget || (event.key !== 'Enter' && event.key !== ' ')) return;
      event.preventDefault();
      openCase(item.case_id);
    };
    return <div key={item.case_id} className={`case-list-item ${selectedCaseId === item.case_id ? 'selected' : ''}`} role="button" tabIndex={0} aria-current={selectedCaseId === item.case_id ? 'page' : undefined} aria-disabled={editing || undefined} onClick={selectFromCard} onKeyDown={selectFromKeyboard}>
      {editing ? <form className="case-item-rename" onSubmit={(event) => { event.preventDefault(); void saveRename(item); }}>
        <span className="case-item-top"><b>{item.case_id}</b><span className={`risk-pill ${caseStateTone(caseState(item))}`}>{caseStateLabel(caseState(item))}</span></span>
        <label className="sr-only" htmlFor={`case-name-${item.case_id}`}>사건 이름</label><input id={`case-name-${item.case_id}`} value={renameValue} maxLength={200} autoFocus onChange={(event) => { setRenameValue(event.target.value); setRenameError(''); }}/>
        <span className="case-item-bottom"><span>{statusLabel(item.status, item.mode)}</span><time className="case-item-created-time" title={new Date(item.created_at).toLocaleString('ko-KR')}>생성 {relativeTime(item.created_at)}</time><time className="case-item-updated-time" title={new Date(item.updated_at).toLocaleString('ko-KR')}>수정 {relativeTime(item.updated_at)}</time></span>
        {renameError && <span className="case-item-rename-error" role="alert">{renameError}</span>}
        <span className="case-item-rename-actions"><button type="button" onClick={cancelRename} disabled={renameBusy}>취소</button><button type="submit" disabled={renameBusy || !renameValue.trim()}>저장</button></span>
      </form> : <>
        <span className="case-item-top"><button type="button" className="case-item-id-open" onClick={() => openCase(item.case_id)}><b>{item.case_id}</b></button><span className="case-item-top-actions"><span className={`risk-pill ${caseStateTone(caseState(item))}`}>{caseStateLabel(caseState(item))}</span><button type="button" className="case-item-edit" onClick={() => startRename(item)} aria-label={`${incidentTitle(item)} 사건 이름 수정`} title="사건 이름 수정"><Pencil size={14}/></button></span></span>
        <button type="button" className="case-list-item-open" onClick={() => openCase(item.case_id)}>{caseContent}</button>{newCaseIds.has(item.case_id) && <span className="case-new-badge">새 Case</span>}
      </>}
    </div>;
  };

  return <aside className={`case-list-pane ${mobileOpen ? 'is-open' : ''}`} aria-label="현재 대응 사건 목록">
    <div className="pane-heading">
      <div><p className="eyebrow">SHARED CASE</p><h2>현재 대응 사건</h2></div>
    </div>
    <div className="case-list-controls">
      <label className="search-field"><Search size={15}/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="사건 검색" aria-label="사건 검색"/></label>
      <div className="risk-filter" aria-label="사건 상태 필터">
        {(['ALL', 'LOSS', 'SUSPECTED', 'RESOLVED'] as const).map((value) => <button key={value} className={stateFilter === value ? 'active' : ''} onClick={() => setStateFilter(value)}>{value === 'ALL' ? '전체' : caseStateLabel(value)}</button>)}
      </div>
      <div className="case-list-control-row"><label className="status-filter"><span>업무 상태</span><select value={status} onChange={(event) => setStatus(event.target.value as typeof status)}><option value="ALL">전체 상태</option><option value="ACTIVE">진행 중</option><option value="CLOSED">해결 및 종료</option></select></label><div className="case-sort-controls"><label htmlFor="case-sort-field">정렬</label><select id="case-sort-field" value={sortField} onChange={(event) => setSortField(event.target.value as CaseSortField)}><option value="CASE_ID">ID 순서</option><option value="UPDATED_AT">최신 업데이트 시간</option></select><button type="button" onClick={() => setSortDirection((value) => value === 'ASC' ? 'DESC' : 'ASC')} aria-label={`현재 ${sortDirection === 'ASC' ? '오름차순' : '내림차순'}, 정렬 방향 변경`} title="정렬 방향 변경">{sortDirection === 'ASC' ? <ArrowUp size={13}/> : <ArrowDown size={13}/>}<span>{sortDirection === 'ASC' ? '오름차순' : '내림차순'}</span></button></div></div>
    </div>
    <div className="case-list-scroll">
      <div className="case-list-table-header" aria-hidden="true"><span>사건 ID</span><span>사건</span><span>업무 상태</span><span>최초 생성</span><span>최근 업데이트</span><span>상태·편집</span></div>
      {pendingAnalysisCount > 0 && <div className="case-analysis-pending-notice" role="status" aria-live="polite"><Loader2 size={16} className="spin"/><span><strong>분석 중인 케이스가 있습니다.</strong><small>{pendingAnalysisCount}건의 분석이 진행 중이며, 분석 결과에 따라 Case Room이 생성되거나 생성되지 않습니다.</small></span></div>}
      {loading && Array.from({ length: 5 }).map((_, index) => <div className="case-skeleton" key={index}/>) }
      {!loading && error && <div className="pane-state error"><AlertCircle size={20}/><strong>사건을 불러오지 못했습니다.</strong><span>{error}</span><button onClick={onRetry}>다시 시도</button></div>}
      {!loading && !error && rows.length === 0 && <div className="pane-state"><strong>현재 대응 중인 사건이 없습니다.</strong><span>위험 이벤트가 Case로 생성되면 여기에 표시됩니다.</span></div>}
      {!loading && !error && rows.map(renderCaseItem)}
    </div>
    <button type="button" className="trash-open-button" onClick={() => { onOpenTrash(); onCloseMobile(); }}><Trash2 size={15}/><span>휴지통</span><b>{trashCount}</b></button>
  </aside>;
};
