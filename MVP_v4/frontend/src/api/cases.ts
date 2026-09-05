import { createUuid } from '../shared/uuid.ts';
import type { CaseDelta } from '../shared/caseDelta.ts';

export interface CaseListItem {
  id: string;
  case_number: string;
  status: 'TRIAGE' | 'ACTIVE' | 'CLOSED';
  mode: 'PREVENT' | 'RECOVERY';
  loss_status: string;
  revision: number;
  version: number;
  updated_at: string;
  created_at: string;
  title: string;
  summary: string;
  deleted_at: string | null;
  latest_event_type: string | null;
  risk_score: number | null;
  risk_classification: string | null;
}

export interface CaseEvent {
  id: string;
  case_id: string;
  event_type: string;
  entity_type: string;
  entity_id: string | null;
  actor_role: string;
  actor_id: string | null;
  visibility: 'CUSTOMER' | 'BANK_INTERNAL';
  case_revision: number;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface WorkspaceCase {
  id: string;
  status: string;
  mode: string;
  loss_status: string;
  primary_assignee_id: string | null;
  revision: number;
  fingerprint: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface ContextFeature {
  id: string;
  case_id: string;
  source_event_id: string;
  schema_version: string;
  feature_fingerprint: string;
  payload: Record<string, unknown>;
  received_at: string;
  version: number;
}

export interface CaseFact { id: string; field_key: string; value: unknown; status: string; visibility: string; version: number; }
export interface CaseVerification { id: string; claim: string; status: string; result_summary: string | null; customer_visible: boolean; visibility: string; version: number; }

export interface BankCaseWorkspace {
  case: WorkspaceCase;
  participants: Array<Record<string, unknown>>;
  events: CaseEvent[];
  context_features: ContextFeature[];
  facts: CaseFact[];
  verifications: CaseVerification[];
  tasks: CaseTask[];
  suggestions: TaskSuggestion[];
}

export interface CaseTask { id: string; case_id: string; title: string; status: 'TODO' | 'IN_PROGRESS' | 'BLOCKED' | 'COMPLETED' | 'CANCELLED'; result: string | null; cancel_reason: string | null; version: number; updated_at: string; }
export interface TaskSuggestion { id: string; case_id: string; proposal: Record<string, unknown>; source_revision: number; status: string; version: number; updated_at: string; }

export async function readJson(path: string, signal?: AbortSignal, body?: unknown): Promise<unknown> {
  const response = await fetch(path, {
    signal,
    credentials: 'same-origin',
    method: body === undefined ? 'GET' : 'POST',
    headers: { 'X-Request-ID': createUuid(), ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const code = typeof body === 'object' && body !== null && 'detail' in body &&
      typeof body.detail === 'object' && body.detail !== null && 'code' in body.detail ? String(body.detail.code) : null;
    throw new Error(code ?? `HTTP_${response.status}`);
  }
  return response.json();
}

function object(value: unknown): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) throw new Error('CASE_API_INVALID_RESPONSE');
  return value as Record<string, unknown>;
}

export async function getCaseList(signal?: AbortSignal, deleted = false): Promise<CaseListItem[]> {
  const value = await readJson(`/api/v4/cases?deleted=${deleted}`, signal);
  if (!Array.isArray(value) || value.some((item) => typeof object(item).id !== 'string')) throw new Error('CASE_API_INVALID_RESPONSE');
  return value as CaseListItem[];
}

export async function getBankCaseWorkspace(caseId: string, signal?: AbortSignal): Promise<BankCaseWorkspace> {
  const value = object(await readJson(`/api/v4/cases/${encodeURIComponent(caseId)}/workspace`, signal));
  if (!('case' in value) || !('events' in value) || !Array.isArray(value.events) ||
      !('context_features' in value) || !Array.isArray(value.context_features) ||
      !('facts' in value) || !Array.isArray(value.facts) || !('verifications' in value) || !Array.isArray(value.verifications)) {
    throw new Error('CASE_API_INVALID_RESPONSE');
  }
  return value as unknown as BankCaseWorkspace;
}

export async function getCaseDelta(caseId: string, revision: number, fingerprint: string, signal?: AbortSignal): Promise<CaseDelta> {
  const query = new URLSearchParams({ known_revision: String(revision), known_fingerprint: fingerprint });
  const value = object(await readJson(`/api/v4/cases/${encodeURIComponent(caseId)}/delta?${query.toString()}`, signal));
  if (typeof value.revision !== 'number' || typeof value.fingerprint !== 'string' || typeof value.unchanged !== 'boolean' ||
      !Array.isArray(value.upserts) || !Array.isArray(value.deleted_entity_ids)) throw new Error('CASE_API_INVALID_RESPONSE');
  return value as unknown as CaseDelta;
}
