import { apiUrl, readUploadError, request } from './client';
import type {
  CustomerProgressItem, ProgressStep, UpdateCustomerProgress,
  AiInvocationResult, AnalyzeCaseResponse, Attachment, CaseAction, CaseBundle, CaseFact, CaseMember, CaseMessage, CasePresence, CaseWorkCard, InitialReport,
  CaseSupportSnapshot, CustomerQuestion, MessageChannel, MessageVisibility,
  PersonalNote, QuestionCandidate, StructuredQuestionAnswer, StoredCase, VerificationTask, WorkCardType, BankStaff,
} from './types';
import { generateUuid } from '../uuid';

export const CURRENT_BANK_USER = {
  user_id: 'mvp-v3-bank-operator',
  display_name: '기능 체험자',
  role: 'CHAT_OPERATOR',
} as const;

export const CURRENT_BANK_USER_STATUS = '기능 체험용 고정' as const;
export const CURRENT_BANK_USER_ROLE_LABEL = '기능 체험자' as const;

export const displayBankUserName = (userId: string, fallback: string) => (
  userId === CURRENT_BANK_USER.user_id ? CURRENT_BANK_USER.display_name : fallback
);

export const CURRENT_CUSTOMER_USER = {
  user_id: 'mvp-v3-customer',
  display_name: '고객',
  role: 'CUSTOMER',
} as const;

export const casesApi = {
  listBankStaff: () => request<BankStaff[]>('/api/bank/staff'),
  createBankStaff: (staff: Omit<BankStaff, 'staff_id' | 'is_self' | 'created_at' | 'updated_at'>) => request<BankStaff>('/api/bank/staff', { method: 'POST', body: JSON.stringify(staff) }),
  updateBankStaff: (staffId: string, staff: Omit<BankStaff, 'staff_id' | 'is_self' | 'created_at' | 'updated_at'>) => request<BankStaff>(`/api/bank/staff/${encodeURIComponent(staffId)}`, { method: 'PATCH', body: JSON.stringify(staff) }),
  deleteBankStaff: (staffId: string) => request<void>(`/api/bank/staff/${encodeURIComponent(staffId)}`, { method: 'DELETE' }),
  list: () => request<StoredCase[]>('/api/cases'),
  listTrash: () => request<StoredCase[]>('/api/cases/trash'),
  updateCase: (caseId: string, expectedVersion: number, values: { case_name?: string }) => request<StoredCase>(`/api/cases/${encodeURIComponent(caseId)}`, {
    method: 'PATCH', body: JSON.stringify({ expected_version: expectedVersion, ...values }),
  }),
  trash: (caseId: string, password: string) => request<void>(`/api/cases/${encodeURIComponent(caseId)}/trash`, {
    method: 'POST', body: JSON.stringify({ password }),
  }),
  restore: (caseId: string, password: string) => request<void>(`/api/cases/${encodeURIComponent(caseId)}/restore`, {
    method: 'POST', body: JSON.stringify({ password }),
  }),
  purge: (caseId: string, password: string) => request<void>(`/api/cases/trash/${encodeURIComponent(caseId)}`, {
    method: 'DELETE', body: JSON.stringify({ password }),
  }),
  finalize: (caseId: string, expectedVersion: number, password: string, note = '') => request<InitialReport>(`/api/cases/${encodeURIComponent(caseId)}/reports/finalize`, {
    method: 'POST', body: JSON.stringify({ expected_version: expectedVersion, password, note }),
  }),
  reopen: (caseId: string, expectedVersion: number, password: string) => request<StoredCase>(`/api/cases/${encodeURIComponent(caseId)}/reopen`, {
    method: 'POST', body: JSON.stringify({ expected_version: expectedVersion, password }),
  }),
  finalReportDownloadUrl: (caseId: string, format: 'pdf' | 'docx') => apiUrl(`/api/cases/${encodeURIComponent(caseId)}/reports/final/export?format=${format}`),
  analyze: (text: string, clientRequestId: string) => request<AnalyzeCaseResponse>('/api/cases/analyze', {
    method: 'POST', body: JSON.stringify({ text, client_request_id: clientRequestId }),
  }),
  get: (caseId: string) => request<StoredCase>(`/api/cases/${encodeURIComponent(caseId)}`),
  bundle: (caseId: string) => request<CaseBundle>(`/api/cases/${encodeURIComponent(caseId)}/bundle?view=bank`),
  customerBundle: (caseId: string) => request<CaseBundle>(`/api/cases/${encodeURIComponent(caseId)}/bundle?view=customer`),
  support: (caseId: string) => request<CaseSupportSnapshot>(`/api/cases/${encodeURIComponent(caseId)}/ai/case-support`),
  facts: (caseId: string) => request<CaseFact[]>(`/api/cases/${encodeURIComponent(caseId)}/facts`),
  personalNotes: (caseId: string) => request<PersonalNote[]>(`/api/cases/${encodeURIComponent(caseId)}/personal-notes?author_id=${encodeURIComponent(CURRENT_BANK_USER.user_id)}`),
  createPersonalNote: (caseId: string, content: string) => request<PersonalNote>(`/api/cases/${encodeURIComponent(caseId)}/personal-notes`, {
    method: 'POST', body: JSON.stringify({ author_id: CURRENT_BANK_USER.user_id, content }),
  }),
  updatePersonalNote: (caseId: string, noteId: string, content: string) => request<PersonalNote>(`/api/cases/${encodeURIComponent(caseId)}/personal-notes/${encodeURIComponent(noteId)}`, {
    method: 'PATCH', body: JSON.stringify({ author_id: CURRENT_BANK_USER.user_id, content }),
  }),
  deletePersonalNote: (caseId: string, noteId: string) => request<void>(`/api/cases/${encodeURIComponent(caseId)}/personal-notes/${encodeURIComponent(noteId)}?author_id=${encodeURIComponent(CURRENT_BANK_USER.user_id)}`, { method: 'DELETE' }),
  members: (caseId: string) => request<CaseMember[]>(`/api/cases/${encodeURIComponent(caseId)}/members`),
  upsertMember: (caseId: string, member: Pick<CaseMember, 'user_id' | 'display_name' | 'role' | 'assignment_role'>) => request<CaseMember>(`/api/cases/${encodeURIComponent(caseId)}/members`, {
    method: 'POST', body: JSON.stringify(member),
  }),
  removeMember: (caseId: string, userId: string) => request<void>(`/api/cases/${encodeURIComponent(caseId)}/members/${encodeURIComponent(userId)}`, { method: 'DELETE' }),
  setPrimaryAssignee: (caseId: string, displayName: string | null) => request<{ case_id: string; display_name: string | null }>(`/api/cases/${encodeURIComponent(caseId)}/assignee`, {
    method: 'PUT', body: JSON.stringify({ display_name: displayName }),
  }),
  presence: (caseId: string) => request<CasePresence[]>(`/api/cases/${encodeURIComponent(caseId)}/presence`),
  heartbeat: (caseId: string, user: { user_id: string; display_name: string }, presence: CasePresence['presence'], channel: MessageChannel) => request<CasePresence>(`/api/cases/${encodeURIComponent(caseId)}/presence/heartbeat`, {
    method: 'POST', body: JSON.stringify({ user_id: user.user_id, display_name: user.display_name, presence, channel }),
  }),
  sendMessage: (caseId: string, content: string, channel: Exclude<MessageChannel, 'AI_INTERNAL'>, attachmentIds: string[] = [], clientRequestId: string = generateUuid()) => {
    const customer = channel === 'CUSTOMER';
    return request<CaseMessage>(`/api/cases/${encodeURIComponent(caseId)}/messages`, {
      method: 'POST',
      body: JSON.stringify({
        actor_type: 'BANK_STAFF', actor_user_id: CURRENT_BANK_USER.user_id,
        actor_display_name: CURRENT_BANK_USER.display_name, actor_role: CURRENT_BANK_USER.role,
        content, channel, audience: customer ? 'CUSTOMER' : 'BANK_INTERNAL',
        visibility: customer ? 'CUSTOMER' : 'BANK_INTERNAL', message_kind: 'CHAT',
        mentions: [], attachment_ids: attachmentIds, client_request_id: clientRequestId,
      }),
    });
  },
  invokeAi: (caseId: string, prompt = '현재 Shared Case 전체 맥락을 기준으로 확인된 사실, 가장 중요한 위험, 아직 확인할 정보, 다음 권장 조치를 짧게 정리해 주세요.', channel: 'TEAM' | 'AI_INTERNAL' = 'AI_INTERNAL', responseStyle: 'CONVERSATIONAL' | 'BRIEF' = 'CONVERSATIONAL') => request<AiInvocationResult>(`/api/cases/${encodeURIComponent(caseId)}/ai/invocations`, {
    method: 'POST',
    body: JSON.stringify({
      prompt, channel, response_style: responseStyle, requester_user_id: CURRENT_BANK_USER.user_id,
      requester_display_name: CURRENT_BANK_USER.display_name, client_request_id: generateUuid(),
    }),
  }),
  generateWorkCard: (caseId: string, cardType: WorkCardType, questionDrafts: QuestionCandidate[] = []) => request<CaseWorkCard>(`/api/cases/${encodeURIComponent(caseId)}/ai/work-cards`, {
    method: 'POST', body: JSON.stringify({ card_type: cardType, question_drafts: questionDrafts }),
  }),
  questionCandidates: (caseId: string) => request<QuestionCandidate[]>(`/api/cases/${encodeURIComponent(caseId)}/customer-question-candidates`),
  queueQuestions: (caseId: string, questions: QuestionCandidate[]) => request<CustomerQuestion[]>(`/api/cases/${encodeURIComponent(caseId)}/customer-questions`, {
    method: 'POST', body: JSON.stringify({ questions, requested_by: CURRENT_BANK_USER.display_name }),
  }),
  createVerification: (caseId: string, claim: string, target: string) => request<VerificationTask>(`/api/cases/${encodeURIComponent(caseId)}/verifications`, {
    method: 'POST', body: JSON.stringify({ claim, target }),
  }),
  updateVerification: (caseId: string, task: VerificationTask, values: Partial<VerificationTask>) => request<VerificationTask>(`/api/cases/${encodeURIComponent(caseId)}/verifications/${encodeURIComponent(task.verification_task_id)}`, {
    method: 'PATCH',
    body: JSON.stringify({
      expected_version: task.version, status: values.status ?? task.status,
      result_summary: values.result_summary ?? null, evidence_url: values.evidence_url ?? null,
      verified_by: values.verified_by ?? null, rag_source: values.rag_source ?? null,
      customer_visible: values.customer_visible ?? false,
    }),
  }),
  createAction: (caseId: string, actionType: string, note: string, title?: string | null) => request<CaseAction>(`/api/cases/${encodeURIComponent(caseId)}/actions`, {
    method: 'POST', body: JSON.stringify({ action_type: actionType, actor_type: 'BANK_STAFF', note, title: title?.trim() || null, visibility: 'BANK_INTERNAL' }),
  }),
  updateCustomerProgress: (caseId: string, step: ProgressStep, values: UpdateCustomerProgress) => request<CustomerProgressItem[]>(`/api/cases/${encodeURIComponent(caseId)}/customer-progress/${step}`, {
    method: 'PUT', body: JSON.stringify(values),
  }),
  requestProgressConfirmation: (caseId: string, step: ProgressStep) => request<CustomerProgressItem[]>(`/api/cases/${encodeURIComponent(caseId)}/customer-progress/${step}/confirmation-request`, { method: 'POST' }),
  updateAction: async (caseId: string, actionId: string, versionOrValues: number | { status?: 'REQUESTED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED'; title?: string; note?: string }, legacyValues?: { status?: 'REQUESTED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED'; title?: string; note?: string }) => {
    const values = typeof versionOrValues === 'number' ? (legacyValues ?? {}) : versionOrValues;
    const version = typeof versionOrValues === 'number'
      ? versionOrValues
      : (await request<CaseAction[]>(`/api/cases/${encodeURIComponent(caseId)}/actions?actor_user_id=${encodeURIComponent(CURRENT_BANK_USER.user_id)}`)).find((item) => item.action_id === actionId)?.version;
    if (!version) throw new Error('Action 최신 버전을 확인하지 못했습니다. 최신 Case 정보를 다시 불러와 주세요.');
    return request<CaseAction>(`/api/cases/${encodeURIComponent(caseId)}/actions/${encodeURIComponent(actionId)}`, {
      method: 'PATCH', body: JSON.stringify({ ...values, expected_version: version, updated_by: CURRENT_BANK_USER.display_name }),
    });
  },
  uploadAttachment: async (caseId: string, file: File, visibility: MessageVisibility): Promise<Attachment> => {
    const path = `/api/cases/${encodeURIComponent(caseId)}/attachments?file_name=${encodeURIComponent(file.name)}&uploaded_by=${encodeURIComponent(CURRENT_BANK_USER.display_name)}&visibility=${encodeURIComponent(visibility)}`;
    const response = await fetch(apiUrl(path), {
      method: 'POST', headers: { 'Content-Type': file.type || 'application/octet-stream' }, body: file,
    });
    if (!response.ok) throw new Error(await readUploadError(response));
    return response.json() as Promise<Attachment>;
  },
  attachmentUrl: (attachment: Attachment) => apiUrl(attachment.download_url.replace(/\?view=(bank|customer)$/, '?view=bank')),
  sendCustomerMessage: (caseId: string, content: string, attachmentIds: string[] = [], clientRequestId: string = generateUuid()) => request<CaseMessage>(`/api/cases/${encodeURIComponent(caseId)}/messages`, {
    method: 'POST',
    body: JSON.stringify({
      actor_type: 'CUSTOMER', actor_user_id: CURRENT_CUSTOMER_USER.user_id,
      actor_display_name: CURRENT_CUSTOMER_USER.display_name, actor_role: CURRENT_CUSTOMER_USER.role,
      content, channel: 'CUSTOMER', audience: 'CUSTOMER', visibility: 'CUSTOMER',
      message_kind: 'CHAT', mentions: [], attachment_ids: attachmentIds,
      client_request_id: clientRequestId,
    }),
  }),
  uploadCustomerAttachment: async (caseId: string, file: File): Promise<Attachment> => {
    const path = `/api/cases/${encodeURIComponent(caseId)}/attachments?file_name=${encodeURIComponent(file.name)}&uploaded_by=${encodeURIComponent(CURRENT_CUSTOMER_USER.display_name)}&visibility=CUSTOMER`;
    const response = await fetch(apiUrl(path), {
      method: 'POST', headers: { 'Content-Type': file.type || 'application/octet-stream' }, body: file,
    });
    if (!response.ok) throw new Error(await readUploadError(response));
    return response.json() as Promise<Attachment>;
  },
  customerAttachmentUrl: (attachment: Attachment) => apiUrl(attachment.download_url.replace(/\?view=(bank|customer)$/, '?view=customer')),
  answerCustomerQuestion: (caseId: string, questionId: string, answer: StructuredQuestionAnswer) => request<CustomerQuestion>(`/api/cases/${encodeURIComponent(caseId)}/customer-questions/${encodeURIComponent(questionId)}/answer`, {
    method: 'POST', body: JSON.stringify({
      selected_option_ids: answer.selected_option_ids,
      free_text: answer.free_text,
      question_version: answer.question_version,
      actor_user_id: CURRENT_CUSTOMER_USER.user_id,
      actor_display_name: CURRENT_CUSTOMER_USER.display_name,
    }),
  }),
  startCustomerEmergency: (caseId: string) => request<CaseMessage>(`/api/cases/${encodeURIComponent(caseId)}/customer-emergency`, {
    method: 'POST', body: JSON.stringify({
      actor_user_id: CURRENT_CUSTOMER_USER.user_id,
      actor_display_name: CURRENT_CUSTOMER_USER.display_name,
    }),
  }),
  invokeCustomerAi: (caseId: string, prompt: string, replyToMessageId: string) => request<CaseMessage>(`/api/cases/${encodeURIComponent(caseId)}/ai/customer-replies`, {
    method: 'POST', body: JSON.stringify({
      prompt,
      requester_user_id: CURRENT_CUSTOMER_USER.user_id,
      requester_display_name: CURRENT_CUSTOMER_USER.display_name,
      reply_to_message_id: replyToMessageId,
      client_request_id: generateUuid(),
    }),
  }),
};
