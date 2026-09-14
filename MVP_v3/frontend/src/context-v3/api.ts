import { request } from '../api/client';
import { CURRENT_BANK_USER } from '../api/cases';
import type { ContextPanelV3 } from './types';

export const loadContextPanelV3 = (caseId: string, signal?: AbortSignal) => request<ContextPanelV3>(
  `/api/cases/${encodeURIComponent(caseId)}/context-v2/panel?view=bank&actor_user_id=${encodeURIComponent(CURRENT_BANK_USER.user_id)}`,
  { signal },
);

export const reviewContextFact = (caseId: string, factId: string, version: number, decision: 'CONFIRM' | 'REJECT', reason: string, supersedesFactId?: string) => request(
  `/api/cases/${encodeURIComponent(caseId)}/context-v2/facts/${encodeURIComponent(factId)}/review?actor_user_id=${encodeURIComponent(CURRENT_BANK_USER.user_id)}`,
  { method: 'PATCH', body: JSON.stringify({ expected_version: version, decision, reason, ...(supersedesFactId ? { supersedes_fact_id: supersedesFactId } : {}) }) },
);

export const createContextFact = (caseId: string, input: { client_request_id: string; semantic_key: string; display_label: string; value: Record<string, unknown>; display_value: string; visibility?: 'BANK_INTERNAL' | 'CUSTOMER_SHARED' }) => request(
  `/api/cases/${encodeURIComponent(caseId)}/context-v2/facts?actor_user_id=${encodeURIComponent(CURRENT_BANK_USER.user_id)}`,
  { method: 'POST', body: JSON.stringify({ ...input, evidence_refs: [], visibility: input.visibility ?? 'BANK_INTERNAL' }) },
);

export const reviewContextSuggestion = (caseId: string, suggestionId: string, version: number, decision: 'ACCEPT' | 'DISMISS', reason?: string) => request(
  `/api/cases/${encodeURIComponent(caseId)}/context-v2/suggestions/${encodeURIComponent(suggestionId)}/review?actor_user_id=${encodeURIComponent(CURRENT_BANK_USER.user_id)}`,
  { method: 'PATCH', body: JSON.stringify({ expected_version: version, decision, ...(reason ? { reason } : {}) }) },
);

export const updateContextTask = (caseId: string, taskId: string, version: number, status: 'TODO' | 'IN_PROGRESS' | 'BLOCKED') => request(
  `/api/cases/${encodeURIComponent(caseId)}/context-v2/tasks/${encodeURIComponent(taskId)}?actor_user_id=${encodeURIComponent(CURRENT_BANK_USER.user_id)}`,
  { method: 'PATCH', body: JSON.stringify({ expected_version: version, status }) },
);

export const completeContextTask = (caseId: string, taskId: string, version: number, resultSummary: string) => request(
  `/api/cases/${encodeURIComponent(caseId)}/context-v2/tasks/${encodeURIComponent(taskId)}/complete?actor_user_id=${encodeURIComponent(CURRENT_BANK_USER.user_id)}`,
  { method: 'POST', body: JSON.stringify({ expected_version: version, result_summary: resultSummary }) },
);

export const cancelContextTask = (caseId: string, taskId: string, version: number, reason: string) => request(
  `/api/cases/${encodeURIComponent(caseId)}/context-v2/tasks/${encodeURIComponent(taskId)}/cancel?actor_user_id=${encodeURIComponent(CURRENT_BANK_USER.user_id)}`,
  { method: 'POST', body: JSON.stringify({ expected_version: version, reason }) },
);

export const createContextTask = (caseId: string, clientRequestId: string, title: string, description: string) => request(
  `/api/cases/${encodeURIComponent(caseId)}/context-v2/tasks?actor_user_id=${encodeURIComponent(CURRENT_BANK_USER.user_id)}`,
  { method: 'POST', body: JSON.stringify({ client_request_id: clientRequestId, task_type: 'OTHER', title, description, priority: 'NORMAL' }) },
);

export type SummaryDisplayOverride = { section: string; semantic_key: string; item_version: number; staff_text?: string | null; deleted_by?: string | null };
export const loadSummaryDisplayOverride = (caseId: string) => request<SummaryDisplayOverride[]>(
  `/api/cases/${encodeURIComponent(caseId)}/context-display?actor_user_id=${encodeURIComponent(CURRENT_BANK_USER.user_id)}`,
);
export const saveSummaryDisplayOverride = (caseId: string, expectedVersion: number, text: string) => request<SummaryDisplayOverride>(
  `/api/cases/${encodeURIComponent(caseId)}/context-display/SUMMARY?actor_user_id=${encodeURIComponent(CURRENT_BANK_USER.user_id)}`,
  { method: 'PATCH', body: JSON.stringify({ expected_version: expectedVersion, operation: 'EDIT', text }) },
);
export const resetSummaryDisplayOverride = (caseId: string, expectedVersion: number) => request<SummaryDisplayOverride>(
  `/api/cases/${encodeURIComponent(caseId)}/context-display/SUMMARY?actor_user_id=${encodeURIComponent(CURRENT_BANK_USER.user_id)}`,
  { method: 'PATCH', body: JSON.stringify({ expected_version: expectedVersion, operation: 'RESET' }) },
);
