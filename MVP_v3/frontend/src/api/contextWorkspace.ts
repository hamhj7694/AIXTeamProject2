import { request } from './client';
import { CURRENT_BANK_USER } from './cases';

export type ContextEvidenceRef = {
  type: 'MESSAGE' | 'QUESTION_ANSWER' | 'BANK_TRANSACTION' | 'VERIFICATION_RESULT' | 'ATTACHMENT' | 'STRUCTURED_SIGNAL' | 'STRUCTURED_ATOM' | 'STAFF_RECORD';
  id: string;
  revision?: number | null;
  summary?: string | null;
};

export type ContextFact = {
  fact_id: string;
  case_id: string;
  semantic_key: string;
  display_label: string;
  value: Record<string, unknown>;
  display_value: string;
  source_kind: 'AI_EXTRACTION' | 'CUSTOMER_STATEMENT' | 'STAFF_OBSERVATION' | 'BANK_RECORD' | 'OFFICIAL_VERIFICATION';
  status: 'PROPOSED' | 'CONFIRMED' | 'REJECTED' | 'SUPERSEDED';
  confidence: number | null;
  evidence_refs: ContextEvidenceRef[];
  visibility: 'BANK_INTERNAL' | 'CUSTOMER_SHARED';
  confirmed_by: string | null;
  confirmed_at: string | null;
  rejection_reason: string | null;
  supersedes_fact_id: string | null;
  version: number;
  created_at: string;
  updated_at: string;
};

export type ContextGap = {
  gap_id: string;
  case_id: string;
  semantic_key: string;
  title: string;
  reason: string;
  priority: 'URGENT' | 'HIGH' | 'NORMAL';
  status: 'OPEN' | 'AWAITING_CUSTOMER' | 'AWAITING_INSTITUTION' | 'STAFF_REVIEW_REQUIRED' | 'RESOLVED' | 'DISMISSED';
  source: 'AI' | 'BANK_STAFF' | 'SYSTEM_RULE';
  evidence_refs: ContextEvidenceRef[];
  related_question_ids: string[];
  related_verification_ids: string[];
  resolution_fact_id: string | null;
  dismissal_reason: string | null;
  visibility: 'BANK_INTERNAL';
  source_revision: number;
  version: number;
  created_at: string;
  updated_at: string;
};

export type ContextGapHistory = {
  entity_id: string;
  entity_version: number;
  operation: 'EDIT' | 'SET_DISMISSED' | 'SET_RESOLVED';
  actor_user_id: string;
  before?: ContextGap | null;
  after: ContextGap;
  created_at: string;
};

export type ContextSuggestion = {
  suggestion_id: string;
  case_id: string;
  suggestion_type: 'CUSTOMER_QUESTION' | 'INSTITUTION_VERIFICATION' | 'TRANSACTION_REVIEW' | 'PROTECTIVE_ACTION' | 'DOCUMENT_REQUEST' | 'STAFF_REVIEW';
  title: string;
  rationale: string;
  priority: 'URGENT' | 'HIGH' | 'NORMAL';
  status: 'PROPOSED' | 'ACCEPTED' | 'DISMISSED' | 'EXPIRED' | 'SUPERSEDED';
  related_gap_ids: string[];
  evidence_refs: ContextEvidenceRef[];
  dedupe_key: string;
  execution_mode: 'HUMAN_REVIEW_REQUIRED' | 'AUTO_CUSTOMER_QUESTION_ALLOWED';
  source_revision: number;
  model_version: string | null;
  prompt_version: string | null;
  accepted_task_id: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  dismissal_reason: string | null;
  version: number;
  created_at: string;
  updated_at: string;
};

export type ContextTask = {
  task_id: string;
  case_id: string;
  source: 'STAFF_CREATED' | 'AI_SUGGESTION_ACCEPTED' | 'SYSTEM_REQUIRED';
  source_suggestion_id: string | null;
  task_type: 'CUSTOMER_CONTACT' | 'INSTITUTION_VERIFICATION' | 'TRANSACTION_REVIEW' | 'PROTECTIVE_ACTION' | 'DOCUMENT_REVIEW' | 'OTHER';
  title: string;
  description: string;
  priority: 'URGENT' | 'HIGH' | 'NORMAL';
  status: 'TODO' | 'IN_PROGRESS' | 'BLOCKED' | 'COMPLETED' | 'CANCELLED';
  assignee_user_id: string | null;
  due_at: string | null;
  related_gap_ids: string[];
  related_verification_ids: string[];
  result_code: string | null;
  result_summary: string | null;
  evidence_refs: ContextEvidenceRef[];
  customer_visibility: 'INTERNAL_ONLY' | 'RESULT_SHAREABLE' | 'RESULT_PUBLISHED';
  completed_by: string | null;
  completed_at: string | null;
  cancellation_reason: string | null;
  version: number;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type ContextDecision = {
  decision_id: string;
  case_id: string;
  decision_type: 'FACT_REVIEW' | 'TASK_DECISION' | 'CASE_STATUS' | 'CUSTOMER_DISCLOSURE' | 'OTHER';
  title: string;
  rationale: string;
  related_entity_type: 'FACT' | 'GAP' | 'SUGGESTION' | 'TASK' | 'VERIFICATION' | 'CASE';
  related_entity_id: string;
  visibility: 'BANK_INTERNAL' | 'CUSTOMER_SHARED';
  actor_user_id: string;
  supersedes_decision_id: string | null;
  created_at: string;
};

export type LegacyContextItem = { id: string; title: string; status: string; value?: string; confirmed_at?: string; created_at?: string };
export type LegacyContextGap = LegacyContextItem & { semantic_key: string; reason: string; version: number };
export type PermissionsMode = 'MVP_OPEN' | 'ROLE_BASED';
export interface ContextWorkspaceData {
  case_id: string;
  context_revision: number;
  permissions_mode: PermissionsMode;
  can_write: boolean;
  can_review: boolean;
  can_review_suggestions: boolean;
  context_facts: ContextFact[];
  confirmed_facts: ContextFact[];
  proposed_facts: ContextFact[];
  open_gaps: ContextGap[];
  archived_gaps: ContextGap[];
  gap_history: ContextGapHistory[];
  ai_suggestions: ContextSuggestion[];
  reviewed_suggestions: ContextSuggestion[];
  active_tasks: ContextTask[];
  archived_tasks: ContextTask[];
  recent_decisions: ContextDecision[];
  legacy_suggestions: LegacyContextItem[];
  legacy_gaps: LegacyContextGap[];
  legacy_records: LegacyContextItem[];
  legacy_archived_suggestions: LegacyContextItem[];
}

export const loadRuntimePermissionsMode = async (): Promise<PermissionsMode> => {
  try {
    const config = await request<{ permissions_mode?: unknown } | null>('/api/runtime-config');
    return config?.permissions_mode === 'MVP_OPEN' ? 'MVP_OPEN' : 'ROLE_BASED';
  } catch {
    return 'ROLE_BASED';
  }
};

export const contextUrl = (caseId: string, path: string) => `/api/cases/${encodeURIComponent(caseId)}/context-v2/${path}?actor_user_id=${encodeURIComponent(CURRENT_BANK_USER.user_id)}`;
export const loadContextWorkspace = (caseId: string, signal?: AbortSignal) => request<ContextWorkspaceData>(contextUrl(caseId, 'workspace'), { signal });
export const saveContextCommand = (caseId: string, path: string, method: string, body: object) => request<unknown>(contextUrl(caseId, path), { method, body: JSON.stringify(body) });
