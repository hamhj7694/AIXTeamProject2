import React, { useState } from 'react';
import { ArrowLeftRight, FileSearch, MessageSquareText, ShieldCheck } from 'lucide-react';
import type { StoredCase } from '../api/types';
import { CaseListPane } from '../components/CaseListPane';
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
}

interface WelcomeProps {
  onStartAnalysis: () => void;
}

const CaseBoardWelcome: React.FC<WelcomeProps> = ({ onStartAnalysis }) => <div className="home-board-welcome">
  <div className="home-mark"><ShieldCheck size={26}/></div>
  <p className="eyebrow">CSR | Case Share Room</p>
  <h2>대응할 사건을 선택하세요.</h2>
  <p>통화 맥락, 고객 대화, 기관 확인과 대응 업무를 하나의 Shared Case에서 이어서 확인할 수 있습니다.</p>
  <div className="home-principles"><span><MessageSquareText size={17}/>대화와 업무 기록을 한 흐름으로</span><span><ArrowLeftRight size={17}/>고객 응답과 Case 맥락을 양방향으로</span></div>
  <button className="start-analysis-button" type="button" onClick={onStartAnalysis}><FileSearch size={17}/>새 통화 분석하기</button>
</div>;

const CaseBoardIntro: React.FC<WelcomeProps> = ({ onStartAnalysis }) => <div className="home-board-intro">
  <p className="eyebrow">CSR | Case Share Room</p>
  <h1>보이스피싱을<br />빠르게 대응하세요!</h1>
  <ul>
    <li>보이스피싱 통화 내용과 상황을 AI가 정리합니다.</li>
    <li>업무 관계자들을 빠르게 소집해 함께 대응하세요.<small>(은행 FDS 모니터링 담당자·상담자·AI가 함께합니다)</small></li>
    <li>고객과 소통하며 추가 정보를 모으고,<br />고객에게 확실한 정보를 안내하세요.</li>
  </ul>
  <button className="start-analysis-button" type="button" onClick={onStartAnalysis}><FileSearch size={16}/>새 통화 분석하기</button>
</div>;

/** Root screen: the case board is the home workspace once cases exist. */
export const HomeDashboardPage: React.FC<Props> = ({ cases, selectedCaseId, loading, error, trashCount, onRetry, onOpenTrash, onSelectCase, onRenameCase }) => {
  const [analysisOpen, setAnalysisOpen] = useState(false);
  const showCaseList = cases.length > 0 || loading || Boolean(error);

  return <section className="home-empty home-board-page">
    <header className="home-case-board-header">
      <CaseBoardIntro onStartAnalysis={() => setAnalysisOpen(true)}/>
      <div className="home-case-board-notice"><p>이 서비스는 단독 운영 서비스가 아닌 은행 업무 체계 혹은 은행 챗봇에 추가할 수 있는 모듈 형태로 제안합니다.</p><p>통신사 AI, ASAP 체계, 은행 FDS 체계를 통해 자동 발동되어 CASE ROOM이 생성되는 구조입니다. 추후 실제 서비스화를 위해서는 온디바이스 업체(통신사, 기기 개발사 등) 협업이 필요합니다.</p></div>
    </header>
    <div className="home-case-board-body">
      {analysisOpen ? <HomePage embedded onCloseEmbedded={() => setAnalysisOpen(false)}/> : showCaseList ? <CaseListPane cases={cases} selectedCaseId={selectedCaseId} loading={loading} error={error} mobileOpen onCloseMobile={() => undefined} onRetry={onRetry} trashCount={trashCount} onOpenTrash={onOpenTrash} onSelectCase={onSelectCase} onRenameCase={onRenameCase}/> : <CaseBoardWelcome onStartAnalysis={() => setAnalysisOpen(true)}/>}
    </div>
    <a className="judge-guide-link home-board-guide-link" href="/judge/index.html">CSR 서비스<br />자세히 살펴보기 →</a>
  </section>;
};
