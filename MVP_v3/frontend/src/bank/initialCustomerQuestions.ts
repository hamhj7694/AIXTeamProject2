import type { CustomerQuestion, QuestionCandidate } from '../api/types';

export type HeldInitialQuestion = { question_id: string; question?: QuestionCandidate };

const holdKey = (caseId: string) => `csr:initial-question-holds:${caseId}`;
const initialKey = (caseId: string) => `csr:initial-questions:${caseId}`;

const isQuestionCandidate = (value: unknown): value is QuestionCandidate => {
  if (!value || typeof value !== 'object') return false;
  const item = value as Partial<QuestionCandidate>;
  return typeof item.question_id === 'string' && typeof item.target_field === 'string'
    && typeof item.question_text === 'string' && typeof item.priority === 'string';
};

export const readInitialQuestions = (caseId: string): QuestionCandidate[] | null => {
  try {
    const value: unknown = JSON.parse(window.localStorage.getItem(initialKey(caseId)) || 'null');
    return Array.isArray(value) && value.every(isQuestionCandidate) ? value : null;
  } catch { return null; }
};

export const writeInitialQuestions = (caseId: string, questions: QuestionCandidate[]) => {
  try { window.localStorage.setItem(initialKey(caseId), JSON.stringify(questions)); } catch { /* storage is optional */ }
};

export const questionTargetKey = (value: string) => ({
  PERSONAL_INFO: 'personal_information_exposure', PERSONAL_INFO_SHARED: 'personal_information_exposure', PERSONAL_INFORMATION: 'personal_information_exposure',
  AUTHENTICATION_INFO: 'authentication_information_exposure', AUTH_INFO: 'authentication_information_exposure', AUTH_INFO_SHARED: 'authentication_information_exposure',
  VICTIM_TRANSFER_STATUS: 'transfer_status',
}[value.trim().toUpperCase()] ?? value.trim().toLowerCase());

export const readInitialQuestionHolds = (caseId: string): HeldInitialQuestion[] => {
  try {
    const value: unknown = JSON.parse(window.localStorage.getItem(holdKey(caseId)) || '[]');
    if (!Array.isArray(value)) return [];
    return value.flatMap((item): HeldInitialQuestion[] => {
      if (typeof item === 'string') return [{ question_id: item }]; // Existing ID-only holds.
      if (!item || typeof item !== 'object') return [];
      const record = item as { question_id?: unknown; question?: unknown };
      if (typeof record.question_id !== 'string') return [];
      const question = record.question;
      return [{ question_id: record.question_id, ...(isQuestionCandidate(question) && question.question_id === record.question_id ? { question } : {}) }];
    });
  } catch { return []; }
};

export const writeInitialQuestionHolds = (caseId: string, holds: HeldInitialQuestion[]) => {
  try { window.localStorage.setItem(holdKey(caseId), JSON.stringify(holds)); } catch { /* storage is optional */ }
};

const queuedTargets = (questions: CustomerQuestion[]) => new Set(questions.map((question) => questionTargetKey(question.target_field)));

export const pendingInitialQuestions = (candidates: QuestionCandidate[], holds: HeldInitialQuestion[], questions: CustomerQuestion[]) => {
  const heldIds = new Set(holds.map((item) => item.question_id));
  const heldTargets = new Set(holds.flatMap((item) => item.question ? [questionTargetKey(item.question.target_field)] : []));
  const handledTargets = queuedTargets(questions);
  return candidates.filter((candidate) => !heldIds.has(candidate.question_id)
    && !heldTargets.has(questionTargetKey(candidate.target_field))
    && !handledTargets.has(questionTargetKey(candidate.target_field)));
};

export const heldQuestionDrafts = (holds: HeldInitialQuestion[], candidates: QuestionCandidate[], questions: CustomerQuestion[]) => {
  const handledTargets = queuedTargets(questions);
  const seenTargets = new Set<string>();
  return holds.flatMap((hold) => {
    const question = hold.question ?? candidates.find((item) => item.question_id === hold.question_id);
    if (!question) return [];
    const target = questionTargetKey(question.target_field);
    if (handledTargets.has(target) || seenTargets.has(target)) return [];
    seenTargets.add(target);
    return [question];
  });
};

export const customerQuestionDispatchPayload = (created: CustomerQuestion[], createdAt = new Date().toISOString()) => ({
  card_type: 'CUSTOMER_QUESTION_DISPATCH', title: '고객 확인 질문 발송',
  created_at: createdAt, external_send: true,
  items: created.map((item) => ({
    question_id: item.question_id, question_text: item.question_text,
    sequence: item.sequence, status: item.status, asked_at: item.asked_at,
  })),
});
