import React, { useMemo, useState } from 'react';
import { AlertCircle, Search, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import type { StoredCase } from '../api/types';
import { caseState, caseStateLabel, caseStateTone, incidentTitle, relativeTime, statusLabel } from '../presentation';

interface Props {
  cases: StoredCase[];
  selectedCaseId?: string;
  loading: boolean;
  error: string;
  mobileOpen: boolean;
  onCloseMobile: () => void;
  onRetry: () => void;
}

export const CaseListPane: React.FC<Props> = ({ cases, selectedCaseId, loading, error, mobileOpen, onCloseMobile, onRetry }) => {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [stateFilter, setStateFilter] = useState<'ALL' | 'LOSS' | 'SUSPECTED' | 'RESOLVED'>('ALL');
  const [status, setStatus] = useState<'ALL' | 'ACTIVE' | 'RECOVERY' | 'CLOSED'>('ALL');
  const rows = useMemo(() => [...cases]
    .filter((item) => stateFilter === 'ALL' || caseState(item) === stateFilter)
    .filter((item) => status === 'ALL'
      || (status === 'ACTIVE' && item.status !== 'CLOSED' && item.mode !== 'RECOVERY')
      || (status === 'RECOVERY' && item.mode === 'RECOVERY')
      || (status === 'CLOSED' && (item.status === 'CLOSED' || item.mode === 'CLOSED')))
    .filter((item) => `${item.case_id} ${incidentTitle(item)} ${item.initial_brief}`.toLowerCase().includes(query.trim().toLowerCase()))
    .sort((a, b) => {
      const stateOrder = { LOSS: 3, SUSPECTED: 2, RESOLVED: 1 };
      return stateOrder[caseState(b)] - stateOrder[caseState(a)] || Date.parse(b.updated_at) - Date.parse(a.updated_at);
    }), [cases, query, stateFilter, status]);
  const openCase = (caseId: string) => { navigate(`/cases/${caseId}`); onCloseMobile(); };

  return <aside className={`case-list-pane ${mobileOpen ? 'is-open' : ''}`} aria-label="현재 대응 사건 목록">
    <div className="pane-heading">
      <div><p className="eyebrow">SHARED CASE</p><h2>현재 대응 사건</h2></div>
      <button className="icon-button mobile-only" onClick={() => navigate('/')} aria-label="사건 선택 화면으로 이동"><X size={18}/></button>
    </div>
    <div className="case-list-controls">
      <label className="search-field"><Search size={15}/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="사건 검색" aria-label="사건 검색"/></label>
      <div className="risk-filter" aria-label="사건 상태 필터">
        {(['ALL', 'LOSS', 'SUSPECTED', 'RESOLVED'] as const).map((value) => <button key={value} className={stateFilter === value ? 'active' : ''} onClick={() => setStateFilter(value)}>{value === 'ALL' ? '전체' : caseStateLabel(value)}</button>)}
      </div>
      <label className="status-filter"><span>업무 상태</span><select value={status} onChange={(event) => setStatus(event.target.value as typeof status)}><option value="ALL">전체 상태</option><option value="ACTIVE">대응 중</option><option value="RECOVERY">피해구제</option><option value="CLOSED">종료</option></select></label>
    </div>
    <div className="case-list-scroll">
      {loading && Array.from({ length: 5 }).map((_, index) => <div className="case-skeleton" key={index}/>) }
      {!loading && error && <div className="pane-state error"><AlertCircle size={20}/><strong>사건을 불러오지 못했습니다.</strong><span>{error}</span><button onClick={onRetry}>다시 시도</button></div>}
      {!loading && !error && rows.length === 0 && <div className="pane-state"><strong>현재 대응 중인 사건이 없습니다.</strong><span>위험 이벤트가 Case로 생성되면 여기에 표시됩니다.</span></div>}
      {!loading && !error && rows.map((item) => <button key={item.case_id} className={`case-list-item ${selectedCaseId === item.case_id ? 'selected' : ''}`} onClick={() => openCase(item.case_id)}>
        <span className="case-item-top"><b>{item.case_id}</b><span className={`risk-pill ${caseStateTone(caseState(item))}`}>{caseStateLabel(caseState(item))}</span></span>
        <strong>{incidentTitle(item)}</strong>
        <span className="case-item-bottom"><span>{statusLabel(item.status, item.mode)}</span><time>{relativeTime(item.updated_at)}</time></span>
      </button>)}
    </div>
  </aside>;
};
