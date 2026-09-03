export type MessageChannel = 'TEAM' | 'CUSTOMER' | 'AI_INTERNAL';
export type MessageAudience = 'BANK_INTERNAL' | 'CUSTOMER';
export type MemberRole = 'CASE_OWNER' | 'CHAT_OPERATOR' | 'REVIEWER' | 'VIEWER';
export type PresenceState = 'VIEWING' | 'TYPING' | 'AWAY' | 'OFFLINE';

export interface MvpMessage {
  message_id: string;
  case_id: string;
  actor_type: 'CUSTOMER' | 'BANK_STAFF' | 'CUSTOMER_AGENT' | 'BANK_AGENT' | 'VERIFICATION' | 'SYSTEM';
  actor_user_id: string;
  actor_display_name: string;
  actor_role: string | null;
  content: string;
  channel: MessageChannel;
  audience: MessageAudience;
  visibility: 'BANK_INTERNAL' | 'CUSTOMER' | 'AI_PRIVATE';
  message_kind: 'CHAT' | 'AI_REQUEST' | 'AI_RESPONSE' | 'SYSTEM_EVENT';
  private_owner_user_id: string | null;
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
  recent_messages: MvpMessage[];
  recent_events: MvpEvent[];
  verification_tasks: Array<{ verification_task_id: string; claim: string; target: string; status: string }>;
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
  listMessages: (caseId: string, channel?: MessageChannel, view: 'bank' | 'customer' = 'bank'): Promise<MvpMessage[]> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/messages?${channel ? `channel=${channel}&` : ''}view=${view}`),
  createMessage: (caseId: string, input: Pick<MvpMessage, 'actor_type' | 'actor_user_id' | 'actor_display_name' | 'actor_role' | 'content' | 'channel' | 'audience' | 'visibility' | 'message_kind'> & { mentions?: string[] }): Promise<MvpMessage> =>
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
  invokeCopilot: (caseId: string, prompt: string, channel: 'TEAM' | 'AI_INTERNAL', requester = { user_id: 'mvp-v2-current-user', display_name: '현재 사용자' }): Promise<MvpMessage> =>
    request<{ message_id: string; content: string; channel: 'TEAM' | 'AI_INTERNAL'; created_at: string }>(`/api/cases/${encodeURIComponent(caseId)}/ai/invocations`, {
      method: 'POST', body: JSON.stringify({ prompt, channel, requester_user_id: requester.user_id, requester_display_name: requester.display_name, client_request_id: crypto.randomUUID() }),
    }).then((result) => ({
      message_id: result.message_id,
      case_id: caseId,
      actor_type: 'BANK_AGENT',
      actor_user_id: 'case-copilot',
      actor_display_name: 'CaseCopilot',
      actor_role: 'BANK_AGENT',
      content: result.content,
      channel: result.channel,
      audience: 'BANK_INTERNAL',
      visibility: result.channel === 'TEAM' ? 'BANK_INTERNAL' : 'AI_PRIVATE',
      message_kind: 'AI_RESPONSE',
      private_owner_user_id: result.channel === 'TEAM' ? null : requester.user_id,
      mentions: ['CaseCopilot'],
      reply_to_message_id: null,
      created_at: result.created_at,
    })),
  shareAiMessage: (caseId: string, messageId: string, sharedBy = { user_id: 'mvp-v2-current-user', display_name: '현재 사용자' }): Promise<MvpMessage> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/ai/messages/${encodeURIComponent(messageId)}/share`, { method: 'POST', body: JSON.stringify({ shared_by_user_id: sharedBy.user_id, shared_by_display_name: sharedBy.display_name }) }),
};
