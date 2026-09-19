import type { CaseBundle, CaseMessage } from '../api/types';
import { buildTimeline, type TimelineEntry } from '../timeline';

export const buildConversationEntries = (
  bundle: CaseBundle,
  view: 'conversation' | 'timeline',
  channel: 'CUSTOMER' | 'TEAM',
): TimelineEntry[] => {
  const entries = buildTimeline(bundle, view === 'timeline').filter((entry) => {
    if (entry.kind === 'QUESTION' || entry.kind === 'ANSWER') return channel === 'CUSTOMER';
    if (entry.kind !== 'MESSAGE') return false;
    const message = entry.data as CaseMessage;
    return channel === 'CUSTOMER' ? message.channel === 'CUSTOMER' : message.channel !== 'CUSTOMER';
  });

  // asked_at이 없는 PENDING도 은행 ROOM에는 Queue 카드로 보여 주되,
  // 고객에게 전달된 질문처럼 보이지 않도록 별도 상태와 빈 시각을 유지한다.
  if (channel === 'CUSTOMER') {
    const pendingEntries = (bundle.questions ?? [])
      .filter((question) => question.status === 'PENDING')
      .sort((left, right) => left.sequence - right.sequence)
      .map((question, index) => ({
        id: `pending-question-${question.question_id}`,
        kind: 'QUESTION' as const,
        occurredAt: '',
        sequence: entries.length + index,
        data: question,
      }));
    entries.push(...pendingEntries);
  }
  return entries;
};
