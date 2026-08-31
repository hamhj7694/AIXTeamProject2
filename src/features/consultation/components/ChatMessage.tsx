import React from 'react';
import { Message } from '../../../types';
import { cn } from '../../../utils/helpers';

interface ChatMessageProps {
  message: Message;
  showAnimation?: boolean;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message, showAnimation = true }) => {
  const isAssistant = message.role === 'assistant';

  if (message.role === 'system') {
    return null;
  }

  const isWarning = message.type === 'warning';

  return (
    <div
      className={cn(
        'flex mb-4 message-enter',
        isAssistant ? 'justify-start' : 'justify-end'
      )}
    >
      <div
        className={cn(
          'max-w-xs md:max-w-md lg:max-w-lg px-4 py-3 rounded-2xl text-base leading-relaxed whitespace-pre-wrap border',
          isAssistant
            ? isWarning
              ? 'border-amber-200 bg-amber-50 text-amber-900 text-left shadow-sm'
              : 'border-slate-200 bg-slate-100 text-slate-800 text-left'
            : 'border-blue-600 bg-blue-600 text-white text-right'
        )}
      >
        {message.content}
      </div>
    </div>
  );
};
