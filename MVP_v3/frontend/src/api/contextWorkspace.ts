import { request } from './client';
import { CURRENT_BANK_USER } from './cases';

export type ContextFact = { fact_id: string; semantic_key: string; display_label: string; display_value: string; source_kind: string; status: string; version: number; confirmed_at: string | null };
export type ContextGap = { gap_id: string; semantic_key: string; title: string; reason: string; status: string; version: number };
export type ContextSuggestion = { suggestion_id: string; title: string; rationale: string; status: string; version: number; dismissal_reason?: string };
export type ContextTask = { task_id: string; title: string; description: string; status: string; version: number; result_summary?: string; cancellation_reason?: string };
export type ContextDecision = { decision_id: string; title: string; rationale: string; created_at: string; supersedes_decision_id: string | null };
export type LegacyContextItem = { id: string; title: string; status: string; value?: string; confirmed_at?: string };
export interface ContextWorkspaceData {
  case_id: string;
  context_revision: number;
  can_write: boolean;
  can_review: boolean;
  confirmed_facts: ContextFact[];
  proposed_facts: ContextFact[];
  open_gaps: ContextGap[];
  archived_gaps: ContextGap[];
  ai_suggestions: ContextSuggestion[];
  reviewed_suggestions: ContextSuggestion[];
  active_tasks: ContextTask[];
  archived_tasks: ContextTask[];
  recent_decisions: ContextDecision[];
  legacy_facts: LegacyContextItem[];
  legacy_suggestions: LegacyContextItem[];
  legacy_gaps: LegacyContextItem[];
  legacy_records: LegacyContextItem[];
  legacy_archived_suggestions: LegacyContextItem[];
}

export const contextUrl = (caseId: string, path: string) => `/api/cases/${encodeURIComponent(caseId)}/context-v2/${path}?actor_user_id=${encodeURIComponent(CURRENT_BANK_USER.user_id)}`;
export const loadContextWorkspace = (caseId: string, signal?: AbortSignal) => request<ContextWorkspaceData>(contextUrl(caseId, 'workspace'), { signal });
export const saveContextCommand = (caseId: string, path: string, method: string, body: object) => request<unknown>(contextUrl(caseId, path), { method, body: JSON.stringify(body) });
