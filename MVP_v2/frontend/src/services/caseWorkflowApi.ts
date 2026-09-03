import { CaseDetail } from '../data/mock/caseData';

export interface WorkflowMessage {
  message_id: string;
  case_id: string;
  actor_type: 'CUSTOMER' | 'BANK_STAFF' | 'CUSTOMER_AGENT' | 'BANK_AGENT' | 'VERIFICATION' | 'SYSTEM';
  content: string;
  created_at: string;
}

export interface WorkflowEvent {
  event_id: number;
  case_id: string;
  event_type: string;
  actor_type: string;
  payload: Record<string, unknown>;
  occurred_at: string;
}

export interface VerificationTask {
  verification_task_id: string;
  case_id: string;
  claim: string;
  target: string;
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
  result_summary?: string | null;
  evidence_url?: string | null;
  verified_by?: string | null;
  rag_source?: string | null;
  customer_visible?: boolean;
}

export interface CaseAction {
  action_id: string;
  case_id: string;
  action_type: string;
  status: string;
  actor_type: string;
  note: string;
  created_at: string;
}

export interface CaseBundle {
  case: Record<string, unknown>;
  live_report: Record<string, unknown> | null;
  questions: Array<Record<string, unknown>>;
  progress_items: Array<Record<string, unknown>>;
  verification_tasks: VerificationTask[];
  recent_messages: WorkflowMessage[];
  recent_actions: CaseAction[];
  recent_events: WorkflowEvent[];
  voice_session: VoiceSession | null;
  cursor: string | null;
}

export interface CasePatchResponse {
  case_id: string;
  version: number;
  mode: string;
  status: string;
  risk: string;
  [key: string]: unknown;
}

export interface VoiceSession {
  session_id: string;
  case_id: string;
  status: 'REQUESTED' | 'ACTIVE' | 'ENDED' | 'FAILED';
  participants: string[];
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
}

export interface FinalReport {
  report_id: string;
  case_id: string;
  report_version: number;
  status: 'LIVE' | 'FINAL';
  sections: Array<Record<string, unknown>>;
  created_at: string;
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

const request = async <T>(path: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.detail;
    throw new Error(payload?.error?.message || detail?.message || '요청을 처리하지 못했습니다.');
  }
  return payload as T;
};

export const caseWorkflowApi = {
  getBundle: (caseId: string, view: 'entry' | 'customer' | 'bank'): Promise<CaseBundle> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/bundle?view=${view}`),
  createMessage: (
    caseId: string,
    content: string,
    actorType: WorkflowMessage['actor_type'] = 'CUSTOMER',
  ): Promise<WorkflowMessage> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/messages`, {
      method: 'POST', body: JSON.stringify({ actor_type: actorType, content, client_request_id: crypto.randomUUID() }),
    }),
  createVerification: (caseId: string, claim: string, target: string): Promise<VerificationTask> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/verifications`, {
      method: 'POST', body: JSON.stringify({ claim, target }),
    }),
  createAction: (caseId: string, actionType: string, note: string): Promise<CaseAction> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/actions`, {
      method: 'POST', body: JSON.stringify({ action_type: actionType, actor_type: 'BANK_STAFF', note }),
    }),
  patchCase: (caseId: string, expectedVersion: number, changes: { status?: string; mode?: string }): Promise<CasePatchResponse> =>
    request(`/api/cases/${encodeURIComponent(caseId)}`, {
      method: 'PATCH', body: JSON.stringify({ expected_version: expectedVersion, ...changes }),
    }),
  updateVerification: (caseId: string, taskId: string, expectedVersion: number, status: VerificationTask['status'], details: Pick<VerificationTask, 'result_summary' | 'evidence_url' | 'verified_by' | 'rag_source' | 'customer_visible'> = {}): Promise<VerificationTask> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/verifications/${encodeURIComponent(taskId)}`, {
      method: 'PATCH', body: JSON.stringify({ expected_version: expectedVersion, status, ...details }),
    }),
  startTakeover: (caseId: string, note: string): Promise<CaseAction> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/takeover`, { method: 'POST', body: JSON.stringify({ note }) }),
  resumeAi: (caseId: string, note: string): Promise<CaseAction> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/resume`, { method: 'POST', body: JSON.stringify({ note }) }),
  createVoiceSession: (caseId: string, participants: string[]): Promise<VoiceSession> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/voice-sessions`, { method: 'POST', body: JSON.stringify({ participants }) }),
  updateVoiceSession: (caseId: string, sessionId: string, status: 'ACTIVE' | 'ENDED' | 'FAILED'): Promise<VoiceSession> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/voice-sessions/${encodeURIComponent(sessionId)}`, { method: 'PATCH', body: JSON.stringify({ status }) }),
  finalizeReport: (caseId: string, expectedVersion: number, note: string): Promise<FinalReport> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/reports/finalize`, { method: 'POST', body: JSON.stringify({ expected_version: expectedVersion, note }) }),
  getFinalReport: (caseId: string): Promise<FinalReport> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/reports/final`),
};

export const bundleCaseId = (bundle: CaseBundle): string => String(bundle.case.case_id ?? '');

export type { CaseDetail };
