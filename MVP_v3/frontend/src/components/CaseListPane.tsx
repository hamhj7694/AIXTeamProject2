import React, { useMemo, useState } from 'react';
import { AlertCircle, Search, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import type { RiskLevel, StoredCase } from '../api/types';
import { incidentTitle, relativeTime, riskLabel, riskTone, statusLabel } from '../presentation';

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
  const [risk, setRisk] = useState<'ALL' | RiskLevel>('ALL');
  const [status, setStatus] = useState<'ALL' | 'ACTIVE' | 'RECOVERY' | 'CLOSED'>('ALL');
  const rows = useMemo(() => [...cases]
    .filter((item) => risk === 'ALL' || item.risk === risk)
    .filter((item) => status === 'ALL'
      || (status === 'ACTIVE' && item.status !== 'CLOSED' && item.mode !== 'RECOVERY')
      || (status === 'RECOVERY' && item.mode === 'RECOVERY')
      || (status === 'CLOSED' && (item.status === 'CLOSED' || item.mode === 'CLOSED')))
    .filter((item) => `${item.case_id} ${incidentTitle(item)} ${item.initial_brief}`.toLowerCase().includes(query.trim().toLowerCase()))
    .sort((a, b) => {
      const riskOrder = { HIGH: 3, LOW: 2, NORMAL: 1 };
      return riskOrder[b.risk] - riskOrder[a.risk] || Date.parse(b.updated_at) - Date.parse(a.updated_at);
    }), [cases, query, risk, status]);
  const openCase = (caseId: string) => { navigate(`/cases/${caseId}`); onCloseMobile(); };

  return <aside className={`case-list-pane ${mobileOpen ? 'is-open' : ''}`} aria-label="현재 대응 사건 목록">
    <div className="pane-heading">
      <div><p className="eyebrow">SHARED CASE</p><h2>현재 대응 사건</h2></div>
      <button className="icon-button mobile-only" onClick={onCloseMobile} aria-label="사건 목록 닫기"><X size={18}/></button>
    </div>
    <div className="case-list-controls">
      <label className="search-field"><Search size={15}/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="사건 검색" aria-label="사건 검색"/></label>
      <div className="risk-filter" aria-label="위험 단계 필터">
        {(['ALL', 'HIGH', 'LOW', 'NORMAL'] as const).map((value) => <button key={value} className={risk === value ? 'active' : ''} onClick={() => setRisk(value)}>{value === 'ALL' ? '전체' : riskLabel(value)}</button>)}
      </div>
      <label className="status-filter"><span>업무 상태</span><select value={status} onChange={(event) => setStatus(event.target.value as typeof status)}><option value="ALL">전체 상태</option><option value="ACTIVE">대응 중</option><option value="RECOVERY">피해구제</option><option value="CLOSED">종료</option></select></label>
    </div>
    <div className="case-list-scroll">
      {loading && Array.from({ length: 5 }).map((_, index) => <div className="case-skeleton" key={index}/>) }
      {!loading && error && <div className="pane-state error"><AlertCircle size={20}/><strong>사건을 불러오지 못했습니다.</strong><span>{error}</span><button onClick={onRetry}>다시 시도</button></div>}
      {!loading && !error && rows.length === 0 && <div className="pane-state"><strong>현재 대응 중인 사건이 없습니다.</strong><span>위험 이벤트가 Case로 생성되면 여기에 표시됩니다.</span></div>}
      {!loading && !error && rows.map((item) => <button key={item.case_id} className={`case-list-item ${selectedCaseId === item.case_id ? 'selected' : ''}`} onClick={() => openCase(item.case_id)}>
        <span className="case-item-top"><b>{item.case_id}</b><span className={`risk-pill ${riskTone(item.risk)}`}>{riskLabel(item.risk)}{Number.isFinite(item.risk_score) ? ` ${Math.round(item.risk_score)}` : ''}</span></span>
        <strong>{incidentTitle(item)}</strong>
        <span className="case-item-bottom"><span>{statusLabel(item.status, item.mode)}</span><time>{relativeTime(item.updated_at)}</time></span>
      </button>)}
    </div>
  </aside>;
};
