import type { CaseFact } from '../../../services/mvpChatApi';

export type WorkCardType =
  | 'FACT_REVIEW'
  | 'QUESTION_PLAN'
  | 'VERIFICATION_REQUEST'
  | 'BANK_ACTION'
  | 'CUSTOMER_NOTICE'
  | 'CASE_TRANSITION';

export type WorkCardStage = 'DRAFT' | 'READY' | 'SUBMITTING' | 'REGISTERED' | 'DELIVERED' | 'FAILED';

export interface WorkCardDescriptor<TPayload extends Record<string, unknown> = Record<string, unknown>> {
  card_id: string;
  card_type: WorkCardType;
  stage: WorkCardStage;
  title: string;
  payload: TPayload;
  source: 'USER_ACTION' | 'AI_PROPOSAL' | 'CASE_EVENT';
  created_at: string;
}

export interface WorkCardRenderContext {
  caseId: string;
  requestedBy: string;
  currentCase: Record<string, unknown>;
  facts: CaseFact[];
  onRefresh: () => Promise<void> | void;
  onClose: () => void;
  onOpenCard: (cardType: WorkCardType) => void;
}
