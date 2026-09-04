import type { CaseBundle, CaseMessage, CustomerQuestion, CustomerVerificationResult } from '../api/types';
import { recoveryStepFromMessage, type RecoveryStep } from './recovery';

export type CustomerTimelineKind = 'MESSAGE' | 'QUESTION' | 'ANSWER' | 'VERIFICATION' | 'RECOVERY_STEP';

export interface CustomerTimelineEntry {
  id: string;
  kind: CustomerTimelineKind;
  occurredAt: string;
  sequence: number;
  data: CaseMessage | CustomerQuestion | CustomerVerificationResult | { message: CaseMessage; step: RecoveryStep };
}

const validDate = (value?: string | null, fallback = '') => value && Number.isFinite(Date.parse(value)) ? value : fallback;

export const buildCustomerTimeline = (bundle: CaseBundle): CustomerTimelineEntry[] => {
  const entries: CustomerTimelineEntry[] = [];
  const messages = (bundle.recent_messages ?? []).filter((message) => message.visibility === 'CUSTOMER');
  const questions = bundle.questions ?? [];
  const questionTexts = new Set(questions.map((question) => question.question_text.trim()));
  const answerMessageIds = new Set(questions.map((question) => question.answer_message_id).filter((value): value is string => Boolean(value)));
  let sequence = 0;

  for (const message of messages) {
    const questionMessage = message.actor_type === 'CUSTOMER_AGENT' && questionTexts.has(message.content.trim());
    if (questionMessage || answerMessageIds.has(message.message_id)) continue;
    const step = recoveryStepFromMessage(message.content);
    if (step) {
      entries.push({ id: `recovery-${message.message_id}`, kind: 'RECOVERY_STEP', occurredAt: message.created_at, sequence: sequence++, data: { message, step } });
    } else {
      entries.push({ id: `customer-message-${message.message_id}`, kind: 'MESSAGE', occurredAt: message.created_at, sequence: sequence++, data: message });
    }
  }

  for (const question of questions) {
    const matchingMessage = messages.find((message) => message.actor_type === 'CUSTOMER_AGENT' && message.content.trim() === question.question_text.trim());
    const fallback = String(bundle.case.updated_at ?? bundle.case.created_at ?? new Date(0).toISOString());
    if (question.status === 'ASKED') {
      entries.push({ id: `customer-question-${question.question_id}`, kind: 'QUESTION', occurredAt: validDate(question.asked_at, matchingMessage?.created_at ?? fallback), sequence: sequence++, data: question });
    }
    if (question.status === 'ANSWERED' && question.answer_text) {
      entries.push({ id: `customer-answer-${question.question_id}`, kind: 'ANSWER', occurredAt: validDate(question.answered_at, fallback), sequence: sequence++, data: question });
    }
  }

  for (const result of bundle.customer_verification_results ?? []) {
    entries.push({ id: `customer-verification-${result.verification_task_id}`, kind: 'VERIFICATION', occurredAt: validDate(result.published_at, String(bundle.case.updated_at ?? new Date(0).toISOString())), sequence: sequence++, data: result });
  }

  return entries.sort((left, right) => {
    const delta = Date.parse(left.occurredAt) - Date.parse(right.occurredAt);
    return (Number.isFinite(delta) ? delta : 0) || left.sequence - right.sequence;
  });
};
