import { CURRENT_BANK_USER } from './api/cases';
import type { CaseAction, CaseBundle, CaseEvent, CaseMessage, CustomerQuestion, StoredCase, VerificationTask } from './api/types';

export type TimelineKind = 'BRIEF' | 'MESSAGE' | 'QUESTION' | 'ANSWER' | 'VERIFICATION_REQUEST' | 'VERIFICATION_RESULT' | 'ACTION' | 'EVENT';

export interface TimelineEntry {
  id: string;
  kind: TimelineKind;
  occurredAt: string;
  sequence: number;
  data: StoredCase | CaseMessage | CustomerQuestion | VerificationTask | CaseAction | CaseEvent;
}

export const buildTimeline = (caseItem: StoredCase, bundle: CaseBundle, includeTechnicalEvents: boolean): TimelineEntry[] => {
  let sequence = 0;
  const entries: TimelineEntry[] = [{ id: `brief-${caseItem.case_id}`, kind: 'BRIEF', occurredAt: caseItem.created_at, sequence: sequence++, data: caseItem }];
  const questions = bundle.questions ?? [];
  const questionTexts = new Set(questions.map((question) => question.question_text.trim()));
  const answerMessageIds = new Set(questions.map((question) => question.answer_message_id).filter((value): value is string => Boolean(value)));

  for (const message of bundle.recent_messages ?? []) {
    const duplicatedQuestion = message.actor_type === 'CUSTOMER_AGENT' && questionTexts.has(message.content.trim());
    const duplicatedAnswer = answerMessageIds.has(message.message_id) || (message.message_kind === 'SYSTEM_EVENT' && message.content.startsWith('고객 답변 접수'));
    // AI 내부 응답은 고객에게는 절대 노출하지 않되, 요청한 은행 담당자는 자신의
    // AI 요청·응답을 대화 흐름에서 확인할 수 있어야 한다.
    const privateAiMessageForAnotherUser = message.visibility === 'AI_PRIVATE'
      && message.private_owner_user_id !== CURRENT_BANK_USER.user_id;
    if (duplicatedQuestion || duplicatedAnswer || privateAiMessageForAnotherUser) continue;
    entries.push({ id: `message-${message.message_id}`, kind: 'MESSAGE', occurredAt: message.created_at, sequence: sequence++, data: message });
  }

  for (const question of questions) {
    if (question.asked_at) entries.push({ id: `question-${question.question_id}`, kind: 'QUESTION', occurredAt: question.asked_at, sequence: sequence++, data: question });
    if (question.answered_at && question.answer_text) entries.push({ id: `answer-${question.question_id}`, kind: 'ANSWER', occurredAt: question.answered_at, sequence: sequence++, data: question });
  }

  for (const task of bundle.verification_tasks ?? []) {
    entries.push({ id: `verification-request-${task.verification_task_id}`, kind: 'VERIFICATION_REQUEST', occurredAt: task.created_at, sequence: sequence++, data: task });
    if (task.updated_at !== task.created_at || task.result_summary || task.status !== 'PENDING') {
      entries.push({ id: `verification-result-${task.verification_task_id}-${task.version}`, kind: 'VERIFICATION_RESULT', occurredAt: task.updated_at, sequence: sequence++, data: task });
    }
  }

  for (const action of bundle.recent_actions ?? []) entries.push({ id: `action-${action.action_id}`, kind: 'ACTION', occurredAt: action.created_at, sequence: sequence++, data: action });
  if (includeTechnicalEvents) for (const event of bundle.recent_events ?? []) entries.push({ id: `event-${event.event_id}`, kind: 'EVENT', occurredAt: event.occurred_at, sequence: sequence++, data: event });

  return entries.sort((left, right) => {
    const leftTime = Date.parse(left.occurredAt);
    const rightTime = Date.parse(right.occurredAt);
    const delta = (Number.isFinite(leftTime) ? leftTime : 0) - (Number.isFinite(rightTime) ? rightTime : 0);
    return delta || left.sequence - right.sequence;
  });
};
