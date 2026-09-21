import React from 'react';
import { Sparkles } from 'lucide-react';

interface Props {
  detail?: string;
}

/** Shared in-chat state shown only while an AI response is being generated. */
export const AiThinkingBubble: React.FC<Props> = ({ detail = '현재 대화와 사건 기록을 확인하고 있습니다.' }) => (
  <article className="ai-thinking-entry" role="status" aria-live="polite">
    <span className="ai-thinking-avatar" aria-hidden="true"><Sparkles size={16}/></span>
    <div className="ai-thinking-bubble">
      <strong>AI가 생각하고 있어요</strong>
      <span>{detail}</span>
      <span className="ai-thinking-dots" aria-hidden="true"><i/><i/><i/></span>
    </div>
  </article>
);
