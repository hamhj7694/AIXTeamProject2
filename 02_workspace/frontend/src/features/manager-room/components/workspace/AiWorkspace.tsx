import React, { useState } from 'react';
import {
  createManagerRoomMockResponse,
  managerRoomWorkspaceMock,
} from '../../data/managerRoomMock';
import { ManagerRoomMessage } from '../../types';
import { CaseOverview } from './CaseOverview';
import { RecommendedQuestion } from './RecommendedQuestion';
import { WorkspaceChat } from './WorkspaceChat';

interface AiWorkspaceProps {
  onOpenCustomerView: () => void;
}

export const AiWorkspace: React.FC<AiWorkspaceProps> = ({
  onOpenCustomerView,
}) => {
  const [messages, setMessages] = useState<ManagerRoomMessage[]>(
    managerRoomWorkspaceMock.initialMessages
  );
  const [input, setInput] = useState('');

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

  return (
    <div className="space-y-5">
      <CaseOverview workspace={managerRoomWorkspaceMock} />
      <WorkspaceChat
        messages={messages}
        input={input}
        onInputChange={setInput}
        onSubmit={() => sendMockRequest(input)}
        onQuickRequest={sendMockRequest}
      />
      <RecommendedQuestion
        question={managerRoomWorkspaceMock.recommendedQuestion}
        onOpenCustomerView={onOpenCustomerView}
      />
    </div>
  );
};
