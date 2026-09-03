import type { CustomerQuestion } from '../../../services/mvpChatApi';

export interface CustomerVerificationResult {
  verification_task_id: string;
  target: string;
  result_summary: string;
  published_at?: string | null;
}

export type CustomerCardDescriptor =
  | { card_id: string; card_type: 'QUESTION'; payload: { question: CustomerQuestion } }
  | { card_id: string; card_type: 'ANSWER_RECEIPT'; payload: { question: CustomerQuestion; answer: string } }
  | { card_id: string; card_type: 'VERIFICATION_RESULT'; payload: { result: CustomerVerificationResult } }
  | { card_id: string; card_type: 'RECOVERY_STEP'; payload: { stepId: string } };
