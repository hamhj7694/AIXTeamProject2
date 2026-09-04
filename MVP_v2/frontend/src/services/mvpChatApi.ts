import { notifyApiMutation } from './caseSync';
import { generalApiErrorMessage, generalApiRequest as request, generalApiUrl } from './generalApiClient';

export type MessageChannel = 'TEAM' | 'CUSTOMER' | 'AI_INTERNAL';
export type MessageAudience = 'BANK_INTERNAL' | 'CUSTOMER';
export type MemberRole = 'CASE_OWNER' | 'CHAT_OPERATOR' | 'REVIEWER' | 'VIEWER';
export type PresenceState = 'VIEWING' | 'TYPING' | 'AWAY' | 'OFFLINE';

export interface MessageAttachment {
  attachment_id: string;
  case_id: string;
  original_name: string;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  uploaded_by: string;
  status: 'UPLOADED' | 'LINKED';
  visibility: 'BANK_INTERNAL' | 'CUSTOMER' | 'AI_PRIVATE';
  ai_readable: boolean;
  download_url: string;
  created_at: string;
}

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
  attachments: MessageAttachment[];
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

export interface VerificationTaskSummary {
  verification_task_id: string;
  claim: string;
  target: string;
  status: string;
  result_summary?: string | null;
  evidence_url?: string | null;
  verified_by?: string | null;
  rag_source?: string | null;
  customer_visible?: boolean;
  updated_at?: string;
}

export interface CaseBundleV2 {
  case: Record<string, unknown>;
  recent_messages: MvpMessage[];
  recent_events: MvpEvent[];
  verification_tasks: VerificationTaskSummary[];
  /** Backend가 고객 공개를 최종 승인한 최소 정보만 담는다. 내부 근거/RAG/확인자 정보는 포함하지 않는다. */
  customer_verification_results?: Array<{
    verification_task_id: string;
    target: string;
    result_summary: string;
    published_at?: string | null;
  }>;
  /** AI가 현재 Case에 맞춰 생성한 질문 카드. 아직 생성되지 않았으면 빈 배열이다. */
  questions?: CustomerQuestion[];
}

export interface CustomerQuestionCandidate {
  question_id: string;
  target_field: string;
  question_text: string;
  reason: string;
  priority: 'P0' | 'P1' | 'P2';
  options?: string[];
  customer_explanation?: string;
  answer_mode?: 'SINGLE_CHOICE' | 'TEXT' | 'CHOICE_OR_TEXT';
  allow_free_text?: boolean;
}

export interface CaseSupportSnapshot {
  case_id: string;
  available: boolean;
  case_brief: { summary: string; incident_type: string; risk_level: string; risk_score: number; next_checks: string[] } | null;
  recommended_questions: CustomerQuestionCandidate[];
  unresolved_items: Array<{ target_field: string; description: string; priority: 'P0' | 'P1' | 'P2' }>;
  warnings: string[];
}

export interface CustomerQuestion extends CustomerQuestionCandidate {
  case_id: string;
  source?: 'BANK_SELECTED' | 'CUSTOMER_AGENT';
  status: 'PENDING' | 'ASKED' | 'ANSWERED' | 'SKIPPED';
  sequence: number;
  requested_by: string | null;
  asked_at: string | null;
  answered_at: string | null;
  answer_message_id?: string | null;
  answer_text?: string | null;
  options?: string[];
}
export interface AiWorkCardProposal {
  card_type: 'FACT_REVIEW' | 'QUESTION_PLAN' | 'VERIFICATION_REQUEST' | 'BANK_ACTION' | 'CUSTOMER_NOTICE' | 'CASE_TRANSITION';
  title: string;
  summary: string;
  context_sources: string[];
  rationale: string[];
  next_action: string;
  questions: CustomerQuestionCandidate[];
  suggested_claim: string | null;
  suggested_target: string | null;
  suggested_action_type: string | null;
  suggested_action_note: string | null;
  suggested_notice: string | null;
  suggested_transition: string | null;
  warnings: string[];
  model_mode: string;
}
export interface CaseFact { fact_id: string; case_id: string; field: string; value: string; source: 'AI_EXTRACTED' | 'HUMAN_CONFIRMED' | 'VERIFIED' | 'UNRESOLVED'; status: 'PROPOSED' | 'CONFIRMED' | 'UNRESOLVED'; confidence: number; evidence_message_id: string | null; source_question_id?: string | null; confirmed_by: string | null; confirmed_at: string | null; created_at: string; }
export interface PersonalNote { note_id: string; case_id: string; author_id: string; content: string; visibility: 'PRIVATE_TO_AUTHOR'; created_at: string; updated_at: string; }

export const mvpChatApi = {
  getBundle: (caseId: string, view: 'customer' | 'bank'): Promise<CaseBundleV2> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/bundle?view=${view}`),
  listMessages: (caseId: string, channel?: MessageChannel, view: 'bank' | 'customer' = 'bank'): Promise<MvpMessage[]> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/messages?${channel ? `channel=${channel}&` : ''}view=${view}`),
  createMessage: (caseId: string, input: Pick<MvpMessage, 'actor_type' | 'actor_user_id' | 'actor_display_name' | 'actor_role' | 'content' | 'channel' | 'audience' | 'visibility' | 'message_kind'> & { mentions?: string[]; attachment_ids?: string[] }): Promise<MvpMessage> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/messages`, {
      method: 'POST',
      body: JSON.stringify({ ...input, mentions: input.mentions ?? [], client_request_id: crypto.randomUUID() }),
    }),
  startCustomerEmergency: (caseId: string, actor = { user_id: 'mvp-v2-customer', display_name: '고객' }): Promise<MvpMessage> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/customer-emergency`, {
      method: 'POST', body: JSON.stringify({ actor_user_id: actor.user_id, actor_display_name: actor.display_name }),
    }),
  uploadAttachment: async (caseId: string, file: File, uploadedBy: string, visibility: MessageAttachment['visibility']): Promise<MessageAttachment> => {
    const path = `/api/cases/${encodeURIComponent(caseId)}/attachments?file_name=${encodeURIComponent(file.name)}&uploaded_by=${encodeURIComponent(uploadedBy)}&visibility=${encodeURIComponent(visibility)}`;
    const response = await fetch(generalApiUrl(path), { method: 'POST', headers: { 'Content-Type': file.type || 'application/octet-stream' }, body: file });
    const payload = await response.json().catch(() => null);
    if (!response.ok) throw new Error(generalApiErrorMessage(payload, response.status));
    notifyApiMutation(path, { method: 'POST' }, payload);
    return payload as MessageAttachment;
  },
  attachmentContentUrl: (attachment: MessageAttachment, view: 'bank' | 'customer'): string => {
    const path = attachment.download_url.replace(/\?view=(bank|customer)$/, `?view=${view}`);
    return generalApiUrl(path);
  },
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
      attachments: [],
      created_at: result.created_at,
    })),
  invokeCustomerAgent: (caseId: string, prompt: string, replyToMessageId: string, requester = { user_id: 'mvp-v2-customer', display_name: '고객' }): Promise<MvpMessage> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/ai/customer-replies`, {
      method: 'POST',
      body: JSON.stringify({ prompt, requester_user_id: requester.user_id, requester_display_name: requester.display_name, reply_to_message_id: replyToMessageId, client_request_id: crypto.randomUUID() }),
    }),
  generateAiWorkCard: (caseId: string, cardType: AiWorkCardProposal['card_type']): Promise<AiWorkCardProposal> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/ai/work-cards`, { method: 'POST', body: JSON.stringify({ card_type: cardType }) }),
  shareAiMessage: (caseId: string, messageId: string, sharedBy = { user_id: 'mvp-v2-current-user', display_name: '현재 사용자' }): Promise<MvpMessage> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/ai/messages/${encodeURIComponent(messageId)}/share`, { method: 'POST', body: JSON.stringify({ shared_by_user_id: sharedBy.user_id, shared_by_display_name: sharedBy.display_name }) }),
  listCustomerQuestionCandidates: (caseId: string): Promise<CustomerQuestionCandidate[]> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/customer-question-candidates`),
  getCaseSupportSnapshot: (caseId: string): Promise<CaseSupportSnapshot> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/ai/case-support`),
  listCustomerQuestions: (caseId: string, view: 'bank' | 'customer' = 'bank'): Promise<CustomerQuestion[]> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/customer-questions?view=${view}`),
  queueCustomerQuestions: (caseId: string, questions: CustomerQuestionCandidate[], requestedBy: string): Promise<CustomerQuestion[]> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/customer-questions`, { method: 'POST', body: JSON.stringify({ questions, requested_by: requestedBy }) }),
  ensureAiCustomerQuestions: (caseId: string): Promise<CustomerQuestion[]> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/ai/customer-questions/ensure`, { method: 'POST' }),
  answerCustomerQuestion: (caseId: string, questionId: string, rawAnswer: string, actor = { user_id: 'mvp-v2-customer', display_name: '고객' }): Promise<CustomerQuestion> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/customer-questions/${encodeURIComponent(questionId)}/answer`, { method: 'POST', body: JSON.stringify({ raw_answer: rawAnswer, actor_user_id: actor.user_id, actor_display_name: actor.display_name }) }),
  listCaseFacts: (caseId: string): Promise<CaseFact[]> => request(`/api/cases/${encodeURIComponent(caseId)}/facts`),
  confirmCaseFact: (caseId: string, factId: string, confirmedBy: string): Promise<CaseFact> => request(`/api/cases/${encodeURIComponent(caseId)}/facts/${encodeURIComponent(factId)}/confirm`, { method: 'POST', body: JSON.stringify({ confirmed_by: confirmedBy }) }),
  listPersonalNotes: (caseId: string, authorId: string): Promise<PersonalNote[]> => request(`/api/cases/${encodeURIComponent(caseId)}/personal-notes?author_id=${encodeURIComponent(authorId)}`),
  createPersonalNote: (caseId: string, authorId: string, content: string): Promise<PersonalNote> => request(`/api/cases/${encodeURIComponent(caseId)}/personal-notes`, { method: 'POST', body: JSON.stringify({ author_id: authorId, content }) }),
  updatePersonalNote: (caseId: string, noteId: string, authorId: string, content: string): Promise<PersonalNote> => request(`/api/cases/${encodeURIComponent(caseId)}/personal-notes/${encodeURIComponent(noteId)}`, { method: 'PATCH', body: JSON.stringify({ author_id: authorId, content }) }),
  deletePersonalNote: (caseId: string, noteId: string, authorId: string): Promise<void> => request(`/api/cases/${encodeURIComponent(caseId)}/personal-notes/${encodeURIComponent(noteId)}?author_id=${encodeURIComponent(authorId)}`, { method: 'DELETE' }),
};
