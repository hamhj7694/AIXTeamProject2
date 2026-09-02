import React, { FormEvent, useEffect, useRef } from 'react';
import { Bot, Send, UserRound } from 'lucide-react';
import { Badge } from '../../../../components/ui/Badge';
import { Button } from '../../../../components/ui/Button';
import { Card } from '../../../../components/ui/Card';
import { cn } from '../../../../utils/helpers';
import { ManagerRoomMessage } from '../../types';

interface WorkspaceChatProps {
  messages: ManagerRoomMessage[];
  input: string;
  onInputChange: (value: string) => void;
  onSubmit: () => void;
  onQuickRequest: (request: string) => void;
}

const quickRequests = [
  '위험 근거',
  '미확인 정보',
  '다음 확인사항',
] as const;

export const WorkspaceChat: React.FC<WorkspaceChatProps> = ({
  messages,
  input,
  onInputChange,
  onSubmit,
  onQuickRequest,
}) => {
  const messageListRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const messageList = messageListRef.current;
    if (!messageList) return;

    // 새 요청과 Mock 응답이 추가되면 대화 영역 안에서 최신 메시지를 보여준다.
    messageList.scrollTo({
      top: messageList.scrollHeight,
      behavior: 'smooth',
    });
  }, [messages.length]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit();
  };

  return (
    <Card className="rounded-xl !border-slate-800 !bg-slate-950 p-0 shadow-sm">
      <section aria-labelledby="workspace-chat-title">
        <div className="border-b border-slate-800 p-4 sm:px-5">
          <div className="flex items-center gap-2">
            <h2 id="workspace-chat-title" className="text-base font-extrabold text-white">
              AI 업무 대화
            </h2>
            <Badge variant="default" className="!bg-slate-800 !text-slate-300">
              AI Agent 연동 대기
            </Badge>
          </div>
          <p className="mt-1 text-xs text-slate-400">
            현재 Case를 기준으로 조사할 내용을 요청하세요.
          </p>
        </div>

        <div
          ref={messageListRef}
          className="max-h-[480px] min-h-[320px] space-y-3 overflow-y-auto bg-slate-900 p-4 sm:px-5 lg:min-h-[420px]"
          aria-live="polite"
        >
          {messages.map((message) => {
            const isManager = message.role === 'manager';

            return (
              <div
                key={message.id}
                className={cn(
                  'flex items-start gap-2.5',
                  isManager && 'flex-row-reverse'
                )}
              >
                <div
                  aria-hidden="true"
                  className={cn(
                    'grid h-8 w-8 shrink-0 place-items-center rounded-full',
                    isManager
                      ? 'bg-slate-700 text-slate-200'
                      : 'bg-violet-500/20 text-violet-300'
                  )}
                >
                  {isManager ? <UserRound size={16} /> : <Bot size={16} />}
                </div>

                <div className={cn('max-w-[82%]', isManager && 'text-right')}>
                  <p className="mb-1 text-[11px] font-extrabold text-slate-300">
                    {isManager ? '담당자' : 'AI 업무 보조'}
                  </p>
                  <div
                    className={cn(
                      'whitespace-pre-wrap rounded-2xl border px-3.5 py-2.5 text-left text-sm leading-6',
                      isManager
                        ? 'rounded-tr-sm border-violet-500/50 bg-violet-600/90 text-white'
                        : 'rounded-tl-sm border-slate-700 bg-slate-800 text-slate-100 shadow-sm'
                    )}
                  >
                    {message.content}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div className="border-t border-slate-800 px-4 pt-3 sm:px-5">
          <p className="mb-2 text-xs font-bold text-slate-400">빠른 요청</p>
          <div className="flex flex-wrap gap-2" aria-label="빠른 요청">
            {quickRequests.map((request) => (
              <Button
                key={request}
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => onQuickRequest(request)}
                className="rounded-lg !border-slate-700 !bg-slate-800 !text-slate-200 hover:!bg-slate-700 focus:ring-violet-500"
              >
                {request}
              </Button>
            ))}
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-4 pt-3 sm:px-5">
          <label htmlFor="manager-workspace-request" className="sr-only">
            AI 업무 요청
          </label>
          <div className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 p-2 transition focus-within:border-violet-500 focus-within:ring-2 focus-within:ring-violet-500/30">
            <textarea
              id="manager-workspace-request"
              value={input}
              onChange={(event) => onInputChange(event.target.value)}
              rows={2}
              placeholder="예: 송금 목적에서 추가로 확인할 내용을 정리해줘."
              className="min-h-[48px] min-w-0 flex-1 resize-none border-0 bg-transparent px-2 py-1.5 text-sm leading-5 text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-0"
            />
            <button
              type="submit"
              disabled={!input.trim()}
              aria-label="업무 요청 전송"
              className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-violet-600 text-white transition hover:bg-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:ring-offset-2 focus:ring-offset-slate-950 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Send size={16} />
            </button>
          </div>
          <p className="mt-2 text-xs text-slate-400">
            담당자 요청은 Case 메시지로 저장되며, AI 응답 생성은 Agent API 연결 후 제공됩니다.
          </p>
        </form>
      </section>
    </Card>
  );
};
