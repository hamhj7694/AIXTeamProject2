import React, { FormEvent, useEffect, useRef } from 'react';
import {
  PhoneCall,
  PhoneOff,
  Send,
  ShieldCheck,
  UserRound,
} from 'lucide-react';
import { Badge } from '../../../../components/ui/Badge';
import { Card } from '../../../../components/ui/Card';
import { cn } from '../../../../utils/helpers';
import { ManagerRoomCustomerMessage } from '../../types';

interface CustomerConsultationProps {
  messages: ManagerRoomCustomerMessage[];
  input: string;
  onInputChange: (value: string) => void;
  onSubmit: () => void;
}

export const CustomerConsultation: React.FC<CustomerConsultationProps> = ({
  messages,
  input,
  onInputChange,
  onSubmit,
}) => {
  const messageListRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const messageList = messageListRef.current;
    if (!messageList) return;

    // 메시지 전송과 통화 상태 이벤트 뒤 최신 상담 기록을 바로 확인한다.
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
    <Card className="rounded-xl border-slate-200 p-0 shadow-sm">
      <section aria-labelledby="customer-consultation-title">
        <div className="flex flex-col gap-3 border-b border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h3
                id="customer-consultation-title"
                className="text-base font-extrabold text-slate-950"
              >
                고객 상담
              </h3>
              <Badge variant="default">Case Message API</Badge>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              현재 Case에서 확인이 필요한 내용을 고객과 직접 확인합니다.
            </p>
          </div>

        </div>

        <div
          ref={messageListRef}
          className="max-h-[480px] min-h-[320px] space-y-3 overflow-y-auto bg-slate-50 p-4 sm:px-5 lg:min-h-[420px]"
          aria-live="polite"
        >
          {messages.map((message) => {
            if (message.role === 'system') {
              const SystemEventIcon = message.content.includes('종료')
                ? PhoneOff
                : PhoneCall;

              return (
                <div key={message.id} className="flex justify-center">
                  <p className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-[11px] font-semibold text-slate-500 shadow-sm">
                    <SystemEventIcon size={13} />
                    {message.content}
                  </p>
                </div>
              );
            }

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
                      ? 'bg-blue-100 text-blue-700'
                      : 'bg-slate-200 text-slate-700'
                  )}
                >
                  {isManager ? <ShieldCheck size={16} /> : <UserRound size={16} />}
                </div>

                <div className={cn('max-w-[82%]', isManager && 'text-right')}>
                  <p className="mb-1 text-[11px] font-extrabold text-slate-500">
                    {isManager ? '담당자' : '고객'}
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

        <form onSubmit={handleSubmit} className="border-t border-slate-200 p-4 sm:px-5">
          <label htmlFor="customer-consultation-input" className="sr-only">
            고객 상담 메시지
          </label>
          <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white p-2 transition focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-100">
            <textarea
              id="customer-consultation-input"
              value={input}
              onChange={(event) => onInputChange(event.target.value)}
              rows={2}
              placeholder="고객에게 확인할 내용을 입력하세요."
              className="min-h-[48px] min-w-0 flex-1 resize-none border-0 bg-transparent px-2 py-1.5 text-sm leading-5 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-0"
            />
            <button
              type="submit"
              disabled={!input.trim()}
              aria-label="고객 상담 메시지 전송"
              className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-blue-600 text-white transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Send size={16} />
            </button>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            입력 내용은 이 Case의 BANK_STAFF 메시지로 저장됩니다.
          </p>
        </form>
      </section>
    </Card>
  );
};
