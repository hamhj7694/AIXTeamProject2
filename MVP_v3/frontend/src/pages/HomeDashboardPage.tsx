import React, { useCallback, useState } from 'react';
import { ArrowLeftRight, FileSearch, MessageSquareText, ShieldCheck } from 'lucide-react';
import type { StoredCase } from '../api/types';
import { CaseListPane } from '../components/CaseListPane';
import { TrashWorkspace } from '../components/TrashWorkspace';
import { BankStaffManager } from '../components/BankStaffManager';
import { HomePage } from './HomePage';

interface Props {
  cases: StoredCase[];
  selectedCaseId?: string;
  loading: boolean;
  error: string;
  trashCount: number;
  onRetry: () => void;
  onOpenTrash: () => void;
  onSelectCase: () => void;
  onRenameCase: (caseId: string, caseName: string, expectedVersion: number) => Promise<void>;
  onAnalysisBusyChange?: (busy: boolean) => void;
  trashOpen?: boolean;
  trashedCases?: StoredCase[];
  trashLoading?: boolean;
  trashError?: string;
  onCloseTrash?: () => void;
  onRestoreCase?: (caseId: string, password: string) => Promise<void>;
  onPurgeCase?: (caseId: string, password: string) => Promise<void>;
}

interface WelcomeProps {
  onStartAnalysis: () => void;
  onOpenBankStaff: () => void;
}

const CaseBoardWelcome: React.FC<WelcomeProps> = ({ onStartAnalysis }) => <div className="home-board-welcome">
  <div className="home-mark"><ShieldCheck size={26}/></div>
  <p className="eyebrow">CSR | Case Share Room</p>
  <h2>대응할 사건을 선택하세요.</h2>
  <p>통화 맥락, 고객 대화, 기관 확인과 대응 업무를 하나의 Shared Case에서 이어서 확인할 수 있습니다.</p>
  <div className="home-principles"><span><MessageSquareText size={17}/>대화와 업무 기록을 한 흐름으로</span><span><ArrowLeftRight size={17}/>고객 응답과 Case 맥락을 양방향으로</span></div>
  <button className="start-analysis-button" type="button" onClick={onStartAnalysis}><FileSearch size={17}/>새 통화 분석하기</button>
</div>;

const CaseBoardIntro: React.FC<WelcomeProps> = ({ onStartAnalysis, onOpenBankStaff }) => <div className="home-board-intro">
  <p className="eyebrow">CSR | Case Share Room</p>
  <h1>보이스피싱을<br />빠르게 대응하세요!</h1>
  <ul>
    <li>AI가 보이스피싱 통화의 주요 정황을 정리하고 업무를 지원합니다.</li>
    <li>은행과 고객이 빠르게 소통하며 필요한 정보를 확인하고 안내합니다.</li>
    <li>업무 관계자를 빠르게 소집해 함께 대응합니다.<small>은행 FDS 모니터링 담당자·상담 담당자·AI 협업</small></li>
  </ul>
  <button className="start-analysis-button" type="button" onClick={onStartAnalysis}><FileSearch size={16}/>새 통화 분석하기</button>
  <button className="bank-staff-open-button" type="button" onClick={onOpenBankStaff}>은행 담당자 관리</button>
</div>;

/** Root screen: the case board is the home workspace once cases exist. */
export const HomeDashboardPage: React.FC<Props> = ({ cases, selectedCaseId, loading, error, trashCount, onRetry, onOpenTrash, onSelectCase, onRenameCase, onAnalysisBusyChange, trashOpen = false, trashedCases = [], trashLoading = false, trashError = '', onCloseTrash, onRestoreCase, onPurgeCase }) => {
  const [analysisOpen, setAnalysisOpen] = useState(false);
  const [analysisBusy, setAnalysisBusy] = useState(false);
  const [bankStaffOpen, setBankStaffOpen] = useState(false);
  const setBusy = useCallback((busy: boolean) => { setAnalysisBusy(busy); onAnalysisBusyChange?.(busy); }, [onAnalysisBusyChange]);
  return <section className="home-empty home-board-page">
    <header className="home-case-board-header">
      <CaseBoardIntro onStartAnalysis={() => setAnalysisOpen(true)} onOpenBankStaff={() => setBankStaffOpen(true)}/>
      <div className="home-case-board-notice"><p>이 서비스는 단독 운영 서비스가 아닌 은행 업무 체계 혹은 은행 챗봇에 추가할 수 있는 모듈 형태로 제안합니다.</p><p>통신사 AI, ASAP 체계, 은행 FDS 체계를 통해 자동 발동되어 CASE ROOM이 생성되는 구조입니다. 추후 실제 서비스화를 위해서는 온디바이스 업체(통신사, 기기 개발사 등) 협업이 필요합니다.</p></div>
    </header>
    <div className="home-case-board-body">
      {analysisOpen ? <HomePage embedded onCloseEmbedded={() => setAnalysisOpen(false)} onAnalysisBusyChange={setBusy}/> : trashOpen && onCloseTrash && onRestoreCase && onPurgeCase ? <TrashWorkspace cases={trashedCases} loading={trashLoading} error={trashError} onRetry={onRetry} onClose={onCloseTrash} onRestore={onRestoreCase} onPurge={onPurgeCase}/> : <CaseListPane cases={cases} selectedCaseId={selectedCaseId} loading={loading} error={error} mobileOpen onCloseMobile={() => undefined} onRetry={onRetry} trashCount={trashCount} onOpenTrash={onOpenTrash} onSelectCase={onSelectCase} onRenameCase={onRenameCase}/>} 
    </div>
    <a className={`judge-guide-link home-board-guide-link ${analysisBusy ? 'is-disabled' : ''}`} href="/judge/index.html" aria-disabled={analysisBusy || undefined} onClick={(event) => { if (analysisBusy) event.preventDefault(); }}>CSR 서비스<br />자세히 살펴보기 →</a>
    {bankStaffOpen && <BankStaffManager onClose={() => setBankStaffOpen(false)}/>}</section>;
};
