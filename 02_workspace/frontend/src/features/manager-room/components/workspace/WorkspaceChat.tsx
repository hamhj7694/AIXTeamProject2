import React, { FormEvent } from 'react';
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
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit();
  };

  return (
    <Card className="rounded-xl border-slate-200 p-0 shadow-sm">
      <section aria-labelledby="workspace-chat-title">
        <div className="border-b border-slate-200 p-4 sm:px-5">
          <div className="flex items-center gap-2">
            <h2 id="workspace-chat-title" className="text-base font-extrabold text-slate-950">
              AI 업무 대화
            </h2>
            <Badge variant="default">Mock 응답</Badge>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            현재 Case를 기준으로 조사할 내용을 요청하세요.
          </p>
        </div>

        <div
          className="max-h-[340px] min-h-[220px] space-y-3 overflow-y-auto bg-slate-50 p-4 sm:px-5"
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
                      ? 'bg-slate-200 text-slate-700'
                      : 'bg-blue-100 text-blue-700'
                  )}
                >
                  {isManager ? <UserRound size={16} /> : <Bot size={16} />}
                </div>

                <div className={cn('max-w-[82%]', isManager && 'text-right')}>
                  <p className="mb-1 text-[11px] font-extrabold text-slate-500">
                    {isManager ? '담당자' : 'AI 업무 보조'}
                  </p>
                  <div
                    className={cn(
                      'whitespace-pre-wrap rounded-2xl border px-3.5 py-2.5 text-left text-sm leading-6',
                      isManager
                        ? 'rounded-tr-sm border-blue-200 bg-blue-50 text-slate-800'
                        : 'rounded-tl-sm border-slate-200 bg-white text-slate-700 shadow-sm'
                    )}
                  >
                    {message.content}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div className="border-t border-slate-200 px-4 pt-3 sm:px-5">
          <p className="mb-2 text-xs font-bold text-slate-500">빠른 요청</p>
          <div className="flex flex-wrap gap-2" aria-label="빠른 요청">
            {quickRequests.map((request) => (
              <Button
                key={request}
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => onQuickRequest(request)}
                className="rounded-lg"
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
          <div className="flex items-end gap-2 rounded-xl border border-slate-200 bg-white p-2 transition focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-100">
            <textarea
              id="manager-workspace-request"
              value={input}
              onChange={(event) => onInputChange(event.target.value)}
              rows={2}
              placeholder="예: 송금 목적에서 추가로 확인할 내용을 정리해줘."
              className="min-h-[48px] min-w-0 flex-1 resize-y border-0 bg-transparent px-2 py-1.5 text-sm leading-5 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-0"
            />
            <button
              type="submit"
              disabled={!input.trim()}
              aria-label="업무 요청 전송"
              className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-blue-600 text-white transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Send size={16} />
            </button>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            실제 LLM과 연결되지 않은 규칙 기반 MVP Mock입니다.
          </p>
        </form>
      </section>
    </Card>
  );
};
