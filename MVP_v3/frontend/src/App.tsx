import React, { useCallback, useEffect, useState } from 'react';
import { List, ShieldCheck, Wifi } from 'lucide-react';
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { casesApi } from './api/cases';
import type { StoredCase } from './api/types';
import { TrashWorkspace } from './components/TrashWorkspace';
import { CaseRoomPage } from './pages/CaseRoomPage';
import { CustomerCaseRoomPage } from './pages/CustomerCaseRoomPage';
import { HomeDashboardPage } from './pages/HomeDashboardPage';
import { HomePage } from './pages/HomePage';

const Workspace: React.FC = () => {
  const location = useLocation();
  const selectedCaseId = location.pathname.match(/^\/cases\/([^/]+)/)?.[1];
  const [cases, setCases] = useState<StoredCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [trashedCases, setTrashedCases] = useState<StoredCase[]>([]);
  const [trashLoading, setTrashLoading] = useState(true);
  const [trashError, setTrashError] = useState('');
  const [trashOpen, setTrashOpen] = useState(false);
  const [contextOpen, setContextOpen] = useState(() => typeof window === 'undefined' || !window.matchMedia('(max-width: 1180px)').matches);
  const loadCases = useCallback(async () => {
    try { setCases(await casesApi.list()); setError(''); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Case 목록을 불러오지 못했습니다.'); }
    finally { setLoading(false); }
  }, []);
  const loadTrash = useCallback(async () => {
    try { setTrashedCases(await casesApi.listTrash()); setTrashError(''); }
    catch (reason) { setTrashError(reason instanceof Error ? reason.message : '휴지통을 불러오지 못했습니다.'); }
    finally { setTrashLoading(false); }
  }, []);
  useEffect(() => { void loadCases(); const timer = window.setInterval(() => void loadCases(), 5000); return () => window.clearInterval(timer); }, [loadCases]);
  useEffect(() => { void loadTrash(); const timer = window.setInterval(() => void loadTrash(), 30000); return () => window.clearInterval(timer); }, [loadTrash]);
  useEffect(() => {
    if (!selectedCaseId) return;
    setContextOpen(!window.matchMedia('(max-width: 1180px)').matches);
  }, [selectedCaseId]);
  const refreshLists = () => { void loadCases(); void loadTrash(); };
  const renameCase = async (caseId: string, caseName: string, expectedVersion: number) => {
    const updated = await casesApi.updateCase(caseId, expectedVersion, { case_name: caseName });
    setCases((current) => current.map((item) => item.case_id === caseId ? updated : item));
  };
  const restoreCase = async (caseId: string, password: string) => {
    await casesApi.restore(caseId, password);
    await Promise.all([loadCases(), loadTrash()]);
  };
  const purgeCase = async (caseId: string, password: string) => {
    await casesApi.purge(caseId, password);
    await loadTrash();
  };
  return <div className="app-shell">
    <header className="app-header">
      <Link className="brand" to="/"><span><ShieldCheck size={19}/></span><div><b>CSR | Case Share Room</b><small>보이스피싱 양방향 상담·대응 플랫폼</small></div></Link>
      <div className="app-header-actions">
        {selectedCaseId && <div className="active-case-header-actions">
          <Link className="customer-preview-link" to={`/customer/cases/${encodeURIComponent(selectedCaseId)}`}>고객 화면 열기</Link>
        </div>}
        <div className={`header-status ${error ? 'has-error' : ''}`}><span><Wifi size={13}/>{error ? 'General API 연결 확인 필요' : 'General API 연결'}</span>{location.pathname !== '/' && <Link className="case-board-link" to="/"><List size={14}/>사건 보드</Link>}</div>
      </div>
    </header>
    <div className="workspace-body">
      <div className="workspace-main">{trashOpen ? <TrashWorkspace cases={trashedCases} loading={trashLoading} error={trashError} onRetry={() => void loadTrash()} onClose={() => setTrashOpen(false)} onRestore={restoreCase} onPurge={purgeCase}/> : <Routes><Route path="/" element={<HomeDashboardPage cases={cases} selectedCaseId={selectedCaseId} loading={loading} error={error} trashCount={trashedCases.length} onRetry={() => void loadCases()} onOpenTrash={() => setTrashOpen(true)} onSelectCase={() => setTrashOpen(false)} onRenameCase={renameCase}/>}/><Route path="/analyze" element={<HomePage/>}/><Route path="/cases" element={<Navigate to="/" replace/>}/><Route path="/cases/:caseId" element={<CaseRoomPage caseName={cases.find((item) => item.case_id === selectedCaseId)?.case_name} onMutated={refreshLists} contextOpen={contextOpen} onContextOpenChange={setContextOpen}/>}/><Route path="*" element={<Navigate to="/" replace/>}/></Routes>}</div>
    </div>
  </div>;
};

const RootRoutes: React.FC = () => <Routes>
  <Route path="/customer/cases/:caseId" element={<CustomerCaseRoomPage/>}/>
  <Route path="/*" element={<Workspace/>}/>
</Routes>;

export default function App() { return <BrowserRouter><RootRoutes/></BrowserRouter>; }
