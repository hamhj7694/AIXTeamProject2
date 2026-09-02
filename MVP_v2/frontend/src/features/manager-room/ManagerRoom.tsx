import React, { useEffect, useState } from 'react';
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
import { caseWorkflowApi } from '../../services/caseWorkflowApi';
import { useCaseEventRefresh } from '../case-state/useCaseEventRefresh';
import {
  isManagerRoomView,
  ManagerRoomChecklistItem,
  ManagerRoomCase,
  ManagerRoomCustomerMessage,
  ManagerRoomFinalReport,
  ManagerRoomMemoItem,
  ManagerRoomView,
  ManagerRoomProgressMock,
  ManagerRoomWorkspaceMock,
} from './types';

const emptyWorkspace: ManagerRoomWorkspaceMock = { brief: '', riskEvidence: [], counterEvidence: [], unknowns: [], recommendedQuestion: '추가 확인이 필요합니다.', initialMessages: [] };
const emptyProgress: ManagerRoomProgressMock = { currentStage: 'Case 데이터 조회 중', currentFocus: '실제 Case 정보를 불러오고 있습니다.', nextStage: '추가 확인', events: [], checklist: [] };

export const ManagerRoom: React.FC = () => {
  const { caseId = 'UNKNOWN-CASE' } = useParams<{ caseId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [workspace, setWorkspace] = useState<ManagerRoomWorkspaceMock>(emptyWorkspace);
  const [progress, setProgress] = useState<ManagerRoomProgressMock>(emptyProgress);
  const [caseInfo, setCaseInfo] = useState<ManagerRoomCase>({ caseId, title: 'Case 데이터를 불러오는 중', risk: 'LOW', status: '확인 중', dataSource: 'General API' });
  const [loadError, setLoadError] = useState('');
  const [customerMessages, setCustomerMessages] = useState<
    ManagerRoomCustomerMessage[]
  >([]);
  const [actorTypes, setActorTypes] = useState<string[]>([]);
  const [eventCursor, setEventCursor] = useState<string | null>(null);
  const [refreshNonce, setRefreshNonce] = useState(0);
  const [checklistItems, setChecklistItems] = useState<
    ManagerRoomChecklistItem[]
  >([]);
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
  const [bankVoiceSessionId, setBankVoiceSessionId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoadError('');
    caseWorkflowApi.getBundle(caseId, 'bank').then((bundle) => {
      if (!active) return;
      const data = bundle.case as { case_id?: string; risk?: string; status?: string; initial_brief?: string; diagnosis?: { context?: { incident_type?: string }; evidence?: Array<{ text?: string }> } };
      const risk = data.risk === 'HIGH' ? 'HIGH' : 'LOW';
      const evidence = data.diagnosis?.evidence?.map((item) => item.text).filter((item): item is string => Boolean(item)) ?? [];
      setCaseInfo({ caseId: String(data.case_id ?? caseId), title: data.diagnosis?.context?.incident_type || 'Fraud Case', risk, status: String(data.status ?? 'TRIAGE'), dataSource: 'General API' });
      setWorkspace({ brief: String(data.initial_brief ?? ''), riskEvidence: evidence, counterEvidence: [], unknowns: bundle.verification_tasks.filter((item) => item.status !== 'COMPLETED').map((item) => item.claim), recommendedQuestion: '추가 확인이 필요합니다.', initialMessages: [] });
      setProgress({ currentStage: String(data.status ?? 'TRIAGE'), currentFocus: String(data.initial_brief ?? ''), nextStage: bundle.verification_tasks.length ? 'Verification 확인' : '추가 확인 대기', events: bundle.recent_events.map((event) => ({ id: String(event.event_id), phase: 'current', title: event.event_type, description: event.actor_type, label: event.occurred_at, isKey: true })), checklist: bundle.verification_tasks.map((item) => ({ id: item.verification_task_id, label: item.claim, completed: item.status === 'COMPLETED' })) });
      setChecklistItems(bundle.verification_tasks.map((item) => ({ id: item.verification_task_id, label: item.claim, completed: item.status === 'COMPLETED' })));
      setCustomerMessages(bundle.recent_messages.map((message) => ({ id: message.message_id, role: message.actor_type === 'CUSTOMER' ? 'customer' : message.actor_type === 'BANK_STAFF' ? 'manager' : 'system', content: message.content })));
      setActorTypes(Array.from(new Set([
        ...bundle.recent_messages.map((message) => message.actor_type),
        ...bundle.recent_actions.map((action) => action.actor_type),
      ])));
      setEventCursor(bundle.cursor);
      setBankVoiceSessionId(bundle.voice_session?.session_id ?? null);
    }).catch((reason) => { if (active) setLoadError(reason instanceof Error ? reason.message : 'Case 데이터를 불러오지 못했습니다.'); });
    return () => { active = false; };
  }, [caseId, refreshNonce]);

  useCaseEventRefresh({
    caseId,
    cursor: eventCursor,
    onEvents: (events) => {
      setEventCursor(String(events[events.length - 1].event_id));
      setRefreshNonce((current) => current + 1);
    },
  });

  const createBankMessage = async (content: string) => {
    const message = await caseWorkflowApi.createMessage(caseId, content, 'BANK_STAFF');
    setCustomerMessages((current) => [...current, {
      id: message.message_id,
      role: 'manager',
      content: message.content,
    }]);
    setActorTypes((current) => current.includes('BANK_STAFF') ? current : [...current, 'BANK_STAFF']);
  };

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
    void caseWorkflowApi.createMessage(caseId, content, 'SYSTEM');
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
    void caseWorkflowApi.createVoiceSession(caseId, ['BANK_STAFF', 'CUSTOMER']).then((session) => {
      setBankVoiceSessionId(session.session_id);
      return caseWorkflowApi.updateVoiceSession(caseId, session.session_id, 'ACTIVE');
    });
    void caseWorkflowApi.startTakeover(caseId, '음성 통화 상담을 위해 담당자가 참여했습니다.');
    appendCallEvent('담당자가 고객과 음성 통화를 시작했습니다.');
  };

  const closeCustomerCall = () => {
    if (bankCallActive) {
      if (bankVoiceSessionId) void caseWorkflowApi.updateVoiceSession(caseId, bankVoiceSessionId, 'ENDED');
      void caseWorkflowApi.resumeAi(caseId, '음성 통화 종료 후 AI 상담을 재개합니다.');
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
      null
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
        <ManagerAssigneeOverview actorTypes={actorTypes} />
        <ManagerRoomNavigation
          currentView={currentView}
          onViewChange={handleViewChange}
        />

        <div className="py-4">
          {currentView === 'workspace' ? (
            <AiWorkspace
              workspace={workspace}
              customerMessages={customerMessages}
              onCustomerMessagesChange={setCustomerMessages}
              onCreateBankMessage={createBankMessage}
            />
          ) : currentView === 'progress' ? (
            <CaseProgress
              progress={progress}
              checklistItems={checklistItems}
              onChecklistItemsChange={setChecklistItems}
              memos={caseMemos}
              onMemosChange={setCaseMemos}
            />
          ) : currentView === 'evidence' ? (
            <EvidenceView evidence={workspace.riskEvidence} />
          ) : (
            <FinalReport caseInfo={caseInfo} report={finalReport} />
          )}
        </div>
      </div>
      {loadError && <div className="fixed bottom-4 right-4 rounded-lg bg-rose-50 px-4 py-3 text-sm font-bold text-rose-700 shadow">{loadError}</div>}
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
