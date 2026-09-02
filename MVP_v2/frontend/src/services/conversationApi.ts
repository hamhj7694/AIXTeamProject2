export type MessageActor = 'CUSTOMER' | 'BANK_STAFF' | 'CUSTOMER_AGENT' | 'BANK_AGENT' | 'VERIFICATION' | 'SYSTEM';

export interface CaseMessage {
  message_id: string;
  case_id: string;
  actor_type: MessageActor;
  content: string;
  created_at: string;
}

export interface CaseDeltaEvent {
  event_id: number;
  case_id: string;
  event_type: string;
  actor_type: string;
  payload: Record<string, unknown>;
  occurred_at: string;
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

export const conversationApi = {
  listMessages: (caseId: string): Promise<CaseMessage[]> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/messages`),
  createMessage: (caseId: string, input: Pick<CaseMessage, 'actor_type' | 'content'> & { client_request_id?: string }): Promise<CaseMessage> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/messages`, { method: 'POST', body: JSON.stringify(input) }),
  listEvents: (caseId: string, after?: number): Promise<CaseDeltaEvent[]> => {
    const query = after === undefined ? '' : `?after=${encodeURIComponent(after)}`;
    return request(`/api/cases/${encodeURIComponent(caseId)}/events${query}`);
  },
};
