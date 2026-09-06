import { request } from './client';
import { CURRENT_BANK_USER } from './cases';

export type ContextFact = { fact_id: string; semantic_key: string; display_label: string; display_value: string; source_kind: string; status: string; version: number; confirmed_at: string | null };
export type ContextGap = { gap_id: string; semantic_key: string; title: string; reason: string; status: string; version: number };
export type ContextGapHistory = { entity_id: string; entity_version: number; operation: 'EDIT' | 'SET_DISMISSED' | 'SET_RESOLVED'; actor_user_id: string; before?: ContextGap | null; after: ContextGap; created_at: string };
export type ContextSuggestion = { suggestion_id: string; title: string; rationale: string; status: string; version: number; dismissal_reason?: string };
export type ContextTask = { task_id: string; title: string; description: string; status: string; version: number; result_summary?: string; cancellation_reason?: string };
export type ContextDecision = { decision_id: string; title: string; rationale: string; created_at: string; supersedes_decision_id: string | null };
export type LegacyContextItem = { id: string; title: string; status: string; value?: string; confirmed_at?: string };
export type LegacyContextGap = LegacyContextItem & { semantic_key: string; reason: string; version: number };
export type PermissionsMode = 'MVP_OPEN' | 'ROLE_BASED';
export interface ContextWorkspaceData {
  case_id: string;
  context_revision: number;
  permissions_mode: PermissionsMode;
  can_write: boolean;
  can_review: boolean;
  can_review_suggestions: boolean;
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
  legacy_facts: LegacyContextItem[];
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
