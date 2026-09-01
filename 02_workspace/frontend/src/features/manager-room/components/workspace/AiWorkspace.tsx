import React, { useState } from 'react';
import {
  createManagerRoomMockResponse,
  managerRoomCustomerMessagesMock,
  managerRoomWorkspaceMock,
} from '../../data/managerRoomMock';
import {
  ManagerRoomCustomerMessage,
  ManagerRoomMessage,
} from '../../types';
import { CaseOverview } from './CaseOverview';
import { CustomerConsultation } from './CustomerConsultation';
import { RecommendedQuestion } from './RecommendedQuestion';
import { WorkspaceChat } from './WorkspaceChat';

type ConversationView = 'ai' | 'customer';

export const AiWorkspace: React.FC = () => {
  const [messages, setMessages] = useState<ManagerRoomMessage[]>(
    managerRoomWorkspaceMock.initialMessages
  );
  const [input, setInput] = useState('');
  const [conversationView, setConversationView] =
    useState<ConversationView>('ai');
  const [customerMessages, setCustomerMessages] = useState<
    ManagerRoomCustomerMessage[]
  >(managerRoomCustomerMessagesMock);
  const [customerInput, setCustomerInput] = useState('');
  const [voiceCallActive, setVoiceCallActive] = useState(false);

  const sendMockRequest = (request: string) => {
    const trimmedRequest = request.trim();
    if (!trimmedRequest) return;

    const messageId = Date.now();
    const nextMessages: ManagerRoomMessage[] = [
      {
        id: `manager-${messageId}`,
        role: 'manager',
        content: trimmedRequest,
      },
      {
        id: `assistant-${messageId}`,
        role: 'assistant',
        content: createManagerRoomMockResponse(trimmedRequest),
      },
    ];

    setMessages((currentMessages) => [...currentMessages, ...nextMessages]);
    setInput('');
  };

  const sendCustomerMessage = () => {
    const trimmedInput = customerInput.trim();
    if (!trimmedInput) return;

    setCustomerMessages((currentMessages) => [
      ...currentMessages,
      {
        id: `customer-consultation-manager-${Date.now()}`,
        role: 'manager',
        content: trimmedInput,
      },
    ]);
    setCustomerInput('');
  };

  const useRecommendedQuestion = () => {
    const recommendedQuestion = managerRoomWorkspaceMock.recommendedQuestion;

    // 작성 중인 Draft를 지우지 않고 다음 문단에 추천 질문을 추가한다.
    setCustomerInput((currentInput) =>
      currentInput.trim()
        ? `${currentInput}\n\n${recommendedQuestion}`
        : recommendedQuestion
    );
    setConversationView('customer');
  };

  const startVoiceCall = () => {
    if (voiceCallActive) return;

    // 실제 전화 연결 없이 통화 상태와 상담 기록만 관리하는 MVP 동작이다.
    setVoiceCallActive(true);
    setCustomerMessages((currentMessages) => [
      ...currentMessages,
      {
        id: `customer-consultation-call-start-${Date.now()}`,
        role: 'system',
        content: '담당자가 고객과 음성 통화를 시작했습니다.',
      },
    ]);
  };

  const endVoiceCall = () => {
    if (!voiceCallActive) return;

    setVoiceCallActive(false);
    setCustomerMessages((currentMessages) => [
      ...currentMessages,
      {
        id: `customer-consultation-call-end-${Date.now()}`,
        role: 'system',
        content: '음성 통화가 종료되었습니다.',
      },
    ]);
  };

  return (
    <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
      <section
        aria-labelledby="case-understanding-title"
        className="min-w-0 space-y-4"
      >
        <div>
          <h2
            id="case-understanding-title"
            className="text-lg font-black text-slate-950"
          >
            사건 이해
          </h2>
        </div>

        <CaseOverview workspace={managerRoomWorkspaceMock} />
        <RecommendedQuestion
          question={managerRoomWorkspaceMock.recommendedQuestion}
          onUseInCustomerConsultation={useRecommendedQuestion}
        />
      </section>

      <section
        aria-labelledby="conversation-workspace-title"
        className="min-w-0"
      >
        <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2
              id="conversation-workspace-title"
              className="text-lg font-black text-slate-950"
            >
              대화 Workspace
            </h2>
          </div>

          <div
            role="tablist"
            aria-label="대화 Workspace 선택"
            className="inline-flex w-fit rounded-lg border border-slate-200 bg-white p-1 shadow-sm"
          >
            <button
              type="button"
              role="tab"
              aria-selected={conversationView === 'ai'}
              onClick={() => setConversationView('ai')}
              className={`rounded-md px-3 py-1.5 text-xs font-bold transition ${
                conversationView === 'ai'
                  ? 'bg-slate-950 text-white'
                  : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900'
              }`}
            >
              AI 업무 대화
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={conversationView === 'customer'}
              onClick={() => setConversationView('customer')}
              className={`rounded-md px-3 py-1.5 text-xs font-bold transition ${
                conversationView === 'customer'
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900'
              }`}
            >
              고객 상담
            </button>
          </div>
        </div>

        {conversationView === 'ai' ? (
          <WorkspaceChat
            messages={messages}
            input={input}
            onInputChange={setInput}
            onSubmit={() => sendMockRequest(input)}
            onQuickRequest={sendMockRequest}
          />
        ) : (
          <CustomerConsultation
            messages={customerMessages}
            input={customerInput}
            voiceCallActive={voiceCallActive}
            onInputChange={setCustomerInput}
            onSubmit={sendCustomerMessage}
            onStartVoiceCall={startVoiceCall}
            onEndVoiceCall={endVoiceCall}
          />
        )}
      </section>
    </div>
  );
};
