import React, { useCallback, useEffect, useState } from 'react';
import { List, ShieldCheck, Wifi, X } from 'lucide-react';
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { casesApi } from './api/cases';
import type { StoredCase } from './api/types';
import { CaseListPane } from './components/CaseListPane';
import { CaseRoomPage } from './pages/CaseRoomPage';
import { CustomerCaseRoomPage } from './pages/CustomerCaseRoomPage';
import { HomePage } from './pages/HomePage';

const Workspace: React.FC = () => {
  const location = useLocation();
  const selectedCaseId = location.pathname.match(/^\/cases\/([^/]+)/)?.[1];
  const [cases, setCases] = useState<StoredCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [mobileListOpen, setMobileListOpen] = useState(false);
  const loadCases = useCallback(async () => {
    try { setCases(await casesApi.list()); setError(''); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Case 목록을 불러오지 못했습니다.'); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void loadCases(); const timer = window.setInterval(() => void loadCases(), 5000); return () => window.clearInterval(timer); }, [loadCases]);
  return <div className="app-shell">
    <header className="app-header"><div className="brand"><span><ShieldCheck size={19}/></span><div><b>CSR | Case Share Room</b><small>보이스피싱 양방향 상담·대응 플랫폼</small></div></div><div className={`header-status ${error ? 'has-error' : ''}`}><span><Wifi size={13}/>{error ? 'General API 연결 확인 필요' : 'General API 연결'}</span><button className="mobile-list-button" onClick={() => setMobileListOpen((value) => !value)}>{mobileListOpen ? <X size={17}/> : <List size={17}/>}사건 목록</button></div></header>
    <div className="workspace-body">
      <CaseListPane cases={cases} selectedCaseId={selectedCaseId} loading={loading} error={error} mobileOpen={mobileListOpen} onCloseMobile={() => setMobileListOpen(false)} onRetry={() => void loadCases()}/>
      {mobileListOpen && <button className="mobile-scrim" onClick={() => setMobileListOpen(false)} aria-label="사건 목록 닫기"/>}
      <div className="workspace-main"><Routes><Route path="/" element={<HomePage/>}/><Route path="/cases/:caseId" element={<CaseRoomPage onMutated={() => void loadCases()}/>}/><Route path="*" element={<Navigate to="/" replace/>}/></Routes></div>
    </div>
  </div>;
};

const RootRoutes: React.FC = () => <Routes>
  <Route path="/customer/cases/:caseId" element={<CustomerCaseRoomPage/>}/>
  <Route path="/*" element={<Workspace/>}/>
</Routes>;

export default function App() { return <BrowserRouter><RootRoutes/></BrowserRouter>; }
