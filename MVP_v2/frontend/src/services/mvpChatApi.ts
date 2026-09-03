export type MessageChannel = 'TEAM' | 'CUSTOMER' | 'AI_INTERNAL';
export type MessageAudience = 'BANK_INTERNAL' | 'CUSTOMER';
export type MemberRole = 'CASE_OWNER' | 'CHAT_OPERATOR' | 'REVIEWER' | 'VIEWER';
export type PresenceState = 'VIEWING' | 'TYPING' | 'AWAY' | 'OFFLINE';

export interface MvpMessage {
  message_id: string;
  case_id: string;
  actor_type: 'CUSTOMER' | 'BANK_STAFF' | 'CUSTOMER_AGENT' | 'BANK_AGENT' | 'VERIFICATION' | 'SYSTEM';
  content: string;
  channel: MessageChannel;
  audience: MessageAudience;
  mentions: string[];
  reply_to_message_id: string | null;
  created_at: string;
}

export interface MvpEvent {
  event_id: number;
  case_id: string;
  event_type: string;
  actor_type: string;
  payload: Record<string, unknown>;
  occurred_at: string;
}

export interface CaseMember {
  case_id: string;
  user_id: string;
  display_name: string;
  role: MemberRole;
  status: 'ACTIVE' | 'REMOVED';
  assigned_at: string;
  updated_at: string;
}

export interface CasePresence {
  case_id: string;
  user_id: string;
  display_name: string;
  presence: PresenceState;
  channel: MessageChannel;
  last_seen_at: string;
  expires_at: string;
}

export interface CaseBundleV2 {
  case: Record<string, unknown>;
  recent_events: MvpEvent[];
  verification_tasks: Array<{ verification_task_id: string; claim: string; target: string; status: string }>;
  /** AI가 현재 Case에 맞춰 생성한 질문 카드. 아직 생성되지 않았으면 빈 배열이다. */
  questions?: Array<{
    question_id?: string;
    id?: string;
    prompt?: string;
    question?: string;
    options?: string[];
    choices?: string[];
    mode?: 'PREVENT' | 'RECOVERY' | 'ALL' | string;
  }>;
}

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

const request = async <T>(path: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(payload?.error?.message || payload?.detail?.message || '요청을 처리하지 못했습니다.');
  }
  return payload as T;
};

export const mvpChatApi = {
  getBundle: (caseId: string, view: 'customer' | 'bank'): Promise<CaseBundleV2> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/bundle?view=${view}`),
  listMessages: (caseId: string, channel: MessageChannel): Promise<MvpMessage[]> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/messages?channel=${channel}`),
  createMessage: (caseId: string, input: Pick<MvpMessage, 'actor_type' | 'content' | 'channel' | 'audience'> & { mentions?: string[] }): Promise<MvpMessage> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/messages`, {
      method: 'POST',
      body: JSON.stringify({ ...input, mentions: input.mentions ?? [], client_request_id: crypto.randomUUID() }),
    }),
  listEvents: (caseId: string, after?: number): Promise<MvpEvent[]> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/events${after === undefined ? '' : `?after=${after}`}`),
  listMembers: (caseId: string): Promise<CaseMember[]> => request(`/api/cases/${encodeURIComponent(caseId)}/members`),
  upsertMember: (caseId: string, member: Pick<CaseMember, 'user_id' | 'display_name' | 'role'>): Promise<CaseMember> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/members`, { method: 'POST', body: JSON.stringify(member) }),
  setPrimaryAssignee: (caseId: string, displayName: string | null): Promise<{ case_id: string; display_name: string | null }> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/assignee`, { method: 'PUT', body: JSON.stringify({ display_name: displayName }) }),
  listPresence: (caseId: string): Promise<CasePresence[]> => request(`/api/cases/${encodeURIComponent(caseId)}/presence`),
  heartbeat: (caseId: string, input: { user_id: string; display_name: string; presence: PresenceState; channel: MessageChannel }): Promise<CasePresence> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/presence/heartbeat`, { method: 'POST', body: JSON.stringify(input) }),
  invokeCopilot: (caseId: string, prompt: string, channel: 'TEAM' | 'AI_INTERNAL'): Promise<MvpMessage> =>
    request<{ message_id: string; content: string; created_at: string }>(`/api/cases/${encodeURIComponent(caseId)}/ai/invocations`, {
      method: 'POST', body: JSON.stringify({ prompt, channel, client_request_id: crypto.randomUUID() }),
    }).then((result: { message_id: string; content: string; created_at: string }) => ({
      message_id: result.message_id,
      case_id: caseId,
      actor_type: 'BANK_AGENT',
      content: result.content,
      channel: 'AI_INTERNAL',
      audience: 'BANK_INTERNAL',
      mentions: ['CaseCopilot'],
      reply_to_message_id: null,
      created_at: result.created_at,
    })),
};
