import React, { useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { AppLayout } from '../../components/layout/AppLayout';
import { VoiceCallPopup } from '../../components/voice/VoiceCallPopup';
import {
  clearVoiceCallSnapshot,
  getVoiceCallSnapshot,
  updateVoiceCallSnapshot,
} from '../../components/voice/voiceCallPersistence';
import { CaseCloseDialog } from './components/CaseCloseDialog';
import { ManagerAssigneeOverview } from './components/ManagerAssigneeOverview';
import { ManagerRoomHeader } from './components/ManagerRoomHeader';
import { ManagerRoomNavigation } from './components/ManagerRoomNavigation';
import { EvidenceView } from './components/evidence/EvidenceView';
import { CaseProgress } from './components/progress/CaseProgress';
import { FinalReport } from './components/report/FinalReport';
import { AiWorkspace } from './components/workspace/AiWorkspace';
import {
  createManagerRoomCaseMock,
  createManagerRoomFinalReportMock,
  getManagerRoomProgressMock,
  getManagerRoomWorkspaceMock,
  managerRoomCustomerMessagesMock,
} from './data/managerRoomMock';
import {
  isManagerRoomView,
  ManagerRoomChecklistItem,
  ManagerRoomCustomerMessage,
  ManagerRoomFinalReport,
  ManagerRoomMemoItem,
  ManagerRoomView,
} from './types';

export const ManagerRoom: React.FC = () => {
  const { caseId = 'UNKNOWN-CASE' } = useParams<{ caseId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const workspaceMock = getManagerRoomWorkspaceMock(caseId);
  const progressMock = getManagerRoomProgressMock(caseId);
  const [caseInfo, setCaseInfo] = useState(() =>
    createManagerRoomCaseMock(caseId)
  );
  const [customerMessages, setCustomerMessages] = useState<
    ManagerRoomCustomerMessage[]
  >(managerRoomCustomerMessagesMock);
  const [checklistItems, setChecklistItems] = useState<
    ManagerRoomChecklistItem[]
  >(progressMock.checklist);
  const [caseMemos, setCaseMemos] = useState<ManagerRoomMemoItem[]>([]);
  const [closedAt, setClosedAt] = useState<string | null>(null);
  const [finalReport, setFinalReport] =
    useState<ManagerRoomFinalReport | null>(null);
  const [closeDialogOpen, setCloseDialogOpen] = useState(false);
  const [bankCallOpen, setBankCallOpen] = useState(
    () => getVoiceCallSnapshot('bank').open
  );
  const [bankCallActive, setBankCallActive] = useState(
    () => getVoiceCallSnapshot('bank').calling
  );

  const requestedView = searchParams.get('view');
  const currentView: ManagerRoomView = isManagerRoomView(requestedView)
    ? requestedView
    : 'workspace';
  const handleViewChange = (view: ManagerRoomView) => {
    const nextSearchParams = new URLSearchParams(searchParams);

    // 기본 화면은 query를 생략해 최초 진입 URL을 간결하게 유지한다.
    if (view === 'workspace') {
      nextSearchParams.delete('view');
    } else {
      nextSearchParams.set('view', view);
    }

    setSearchParams(nextSearchParams);
  };

  const appendCallEvent = (content: string) => {
    setCustomerMessages((currentMessages) => [
      ...currentMessages,
      {
        id: `customer-consultation-call-${Date.now()}`,
        role: 'system',
        content,
      },
    ]);
  };

  const openCustomerCall = () => {
    updateVoiceCallSnapshot('bank', { open: true });
    setBankCallOpen(true);
  };

  const handleCallStarted = () => {
    setBankCallActive(true);
    appendCallEvent('담당자가 고객과 음성 통화를 시작했습니다.');
  };

  const closeCustomerCall = () => {
    if (bankCallActive) {
      appendCallEvent('음성 통화가 종료되었습니다.');
    }

    clearVoiceCallSnapshot('bank');
    setBankCallActive(false);
    setBankCallOpen(false);
  };

  const generateFinalReport = () => {
    const reportUpdatedAt = new Date().toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
    const firstClosedAt = closedAt ?? reportUpdatedAt;

    // 최초 종료 시각은 고정하고, 이후에는 최신 조사 state로 리포트만 다시 만든다.
    setFinalReport(
      createManagerRoomFinalReportMock({
        caseInfo,
        workspace: workspaceMock,
        closedAt: firstClosedAt,
        reportUpdatedAt,
        customerMessages,
        checklistItems,
        internalMemos: caseMemos,
      })
    );

    if (!closedAt) {
      setClosedAt(firstClosedAt);
      setCaseInfo((currentCase) => ({ ...currentCase, status: '종료' }));
    }

    setCloseDialogOpen(false);
    handleViewChange('report');
  };

  return (
    <AppLayout>
      <div className="mx-auto max-w-6xl py-6 lg:ml-64 lg:py-8">
        <ManagerRoomHeader
          caseInfo={caseInfo}
          isClosed={Boolean(closedAt)}
          onCallCustomer={openCustomerCall}
          onCloseCase={() => setCloseDialogOpen(true)}
        />
        <ManagerAssigneeOverview />
        <ManagerRoomNavigation
          currentView={currentView}
          onViewChange={handleViewChange}
        />

        <div className="py-4">
          {currentView === 'workspace' ? (
            <AiWorkspace
              workspace={workspaceMock}
              customerMessages={customerMessages}
              onCustomerMessagesChange={setCustomerMessages}
            />
          ) : currentView === 'progress' ? (
            <CaseProgress
              progress={progressMock}
              checklistItems={checklistItems}
              onChecklistItemsChange={setChecklistItems}
              memos={caseMemos}
              onMemosChange={setCaseMemos}
            />
          ) : currentView === 'evidence' ? (
            <EvidenceView />
          ) : (
            <FinalReport caseInfo={caseInfo} report={finalReport} />
          )}
        </div>
      </div>
      <VoiceCallPopup
        open={bankCallOpen}
        role="bank"
        onClose={closeCustomerCall}
        onCallStarted={handleCallStarted}
      />
      <CaseCloseDialog
        open={closeDialogOpen}
        mode={closedAt ? 'refresh' : 'close'}
        onCancel={() => setCloseDialogOpen(false)}
        onConfirm={generateFinalReport}
      />
    </AppLayout>
  );
};
