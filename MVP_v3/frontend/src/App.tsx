import React, { useCallback, useEffect, useState } from 'react';
import { Bell, List, ShieldCheck } from 'lucide-react';
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { casesApi } from './api/cases';
import type { StoredCase } from './api/types';
import { CaseRoomPage } from './pages/CaseRoomPage';
import { CustomerCaseRoomPage } from './pages/CustomerCaseRoomPage';
import { HomeDashboardPage } from './pages/HomeDashboardPage';
import { HomePage } from './pages/HomePage';
import { loadNotifications, notificationEventName, NotificationCenter, type AppNotification } from './components/NotificationCenter';
import { caseState, caseStateTone, incidentTitle, statusLabel } from './presentation';

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
  const [analysisBusy, setAnalysisBusy] = useState(false);
  const [contextOpen, setContextOpen] = useState(() => typeof window === 'undefined' || !window.matchMedia('(max-width: 1180px)').matches);
  const [notifications, setNotifications] = useState<AppNotification[]>(loadNotifications);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const unreadCount = notifications.filter((item) => !item.read).length;
  const activeCase = selectedCaseId ? cases.find((item) => item.case_id === selectedCaseId) : undefined;
  useEffect(() => { const onNotification = () => setNotifications(loadNotifications()); window.addEventListener(notificationEventName, onNotification); return () => window.removeEventListener(notificationEventName, onNotification); }, []);
  const markNotificationsRead = () => { const next = notifications.map((item) => ({ ...item, read: true })); localStorage.setItem('csr-app-notifications-v1', JSON.stringify(next)); setNotifications(next); };
  const deleteNotification = (id: string) => { const next = notifications.filter((item) => item.id !== id); localStorage.setItem('csr-app-notifications-v1', JSON.stringify(next)); setNotifications(next); };
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
      <Link className={`brand ${analysisBusy ? 'is-disabled' : ''}`} to="/" aria-disabled={analysisBusy || undefined} onClick={(event) => { if (analysisBusy) event.preventDefault(); }}><span><ShieldCheck size={19}/></span><div><b>CSR | Case Share Room</b><small>보이스피싱 양방향 상담·대응 플랫폼</small></div></Link>
      {activeCase && <div className="app-header-case-heading" aria-label="현재 사건"><span className={`risk-dot ${caseStateTone(caseState(activeCase))}`}/><div><div className="case-title-line"><span>{activeCase.case_id}</span><h1>{incidentTitle(activeCase)}</h1></div><div className="case-header-meta"><span>{statusLabel(activeCase.status, activeCase.mode)}</span><span>주 담당자 {activeCase.primary_assignee || '미배정'}</span></div></div></div>}
      <div className="app-header-actions">
        <div className="notification-header-control"><button type="button" className="notification-button" onClick={() => { setNotificationsOpen((current) => !current); if (!notificationsOpen) markNotificationsRead(); }} aria-label="알림함 열기" aria-expanded={notificationsOpen}><Bell size={17}/>{unreadCount > 0 && <span className="notification-badge">{unreadCount > 9 ? '9+' : unreadCount}</span>}</button>{notificationsOpen && <NotificationCenter items={notifications} onReadAll={markNotificationsRead} onDelete={deleteNotification} onClose={() => setNotificationsOpen(false)}/>}</div>
        {selectedCaseId && <div className="active-case-header-actions">
          <Link className="customer-preview-link" to={`/customer/cases/${encodeURIComponent(selectedCaseId)}`}><strong>고객 화면 체험하기</strong><small> · 고객 화면을 살펴볼 수 있습니다!</small></Link>
        </div>}
        <div id="app-room-header-actions" className="app-room-header-actions" aria-label="사건 작업 메뉴" />
        <div className="header-status">{location.pathname !== '/' && <Link className="case-board-link" to="/"><List size={14}/>사건 보드</Link>}</div>
      </div>
    </header>
    <div className="workspace-body">
      <div className="workspace-main"><Routes><Route path="/" element={<HomeDashboardPage cases={cases} selectedCaseId={selectedCaseId} loading={loading} error={error} trashCount={trashedCases.length} onRetry={() => void loadCases()} onOpenTrash={() => setTrashOpen(true)} onSelectCase={() => setTrashOpen(false)} onRenameCase={renameCase} onAnalysisBusyChange={setAnalysisBusy} trashOpen={trashOpen} trashedCases={trashedCases} trashLoading={trashLoading} trashError={trashError} onCloseTrash={() => setTrashOpen(false)} onRestoreCase={restoreCase} onPurgeCase={purgeCase}/>}/><Route path="/analyze" element={<HomePage onAnalysisBusyChange={setAnalysisBusy}/>}/><Route path="/cases" element={<Navigate to="/" replace/>}/><Route path="/cases/:caseId" element={<CaseRoomPage caseName={cases.find((item) => item.case_id === selectedCaseId)?.case_name} onMutated={refreshLists} contextOpen={contextOpen} onContextOpenChange={setContextOpen}/>}/><Route path="*" element={<Navigate to="/" replace/>}/></Routes></div>
    </div>
  </div>;
};

const RootRoutes: React.FC = () => <Routes>
  <Route path="/customer/cases/:caseId" element={<CustomerCaseRoomPage/>}/>
  <Route path="/*" element={<Workspace/>}/>
</Routes>;

export default function App() { return <BrowserRouter><RootRoutes/></BrowserRouter>; }
