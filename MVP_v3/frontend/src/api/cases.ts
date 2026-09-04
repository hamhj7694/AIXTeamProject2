import { apiUrl, readUploadError, request } from './client';
import type {
  AiInvocationResult, AnalyzeCaseResponse, Attachment, CaseAction, CaseBundle, CaseFact, CaseMessage,
  CaseSupportSnapshot, CustomerQuestion, MessageChannel, MessageVisibility,
  QuestionCandidate, StoredCase, VerificationTask,
} from './types';

export const CURRENT_BANK_USER = {
  user_id: 'mvp-v3-bank-operator',
  display_name: '은행 담당자',
  role: 'CHAT_OPERATOR',
} as const;

export const CURRENT_CUSTOMER_USER = {
  user_id: 'mvp-v3-customer',
  display_name: '고객',
  role: 'CUSTOMER',
} as const;

export const casesApi = {
  list: () => request<StoredCase[]>('/api/cases'),
  analyze: (text: string) => request<AnalyzeCaseResponse>('/api/cases/analyze', {
    method: 'POST', body: JSON.stringify({ text, client_request_id: crypto.randomUUID() }),
  }),
  get: (caseId: string) => request<StoredCase>(`/api/cases/${encodeURIComponent(caseId)}`),
  bundle: (caseId: string) => request<CaseBundle>(`/api/cases/${encodeURIComponent(caseId)}/bundle?view=bank`),
  customerBundle: (caseId: string) => request<CaseBundle>(`/api/cases/${encodeURIComponent(caseId)}/bundle?view=customer`),
  support: (caseId: string) => request<CaseSupportSnapshot>(`/api/cases/${encodeURIComponent(caseId)}/ai/case-support`),
  facts: (caseId: string) => request<CaseFact[]>(`/api/cases/${encodeURIComponent(caseId)}/facts`),
  sendMessage: (caseId: string, content: string, channel: Exclude<MessageChannel, 'AI_INTERNAL'>, attachmentIds: string[] = []) => {
    const customer = channel === 'CUSTOMER';
    return request<CaseMessage>(`/api/cases/${encodeURIComponent(caseId)}/messages`, {
      method: 'POST',
      body: JSON.stringify({
        actor_type: 'BANK_STAFF', actor_user_id: CURRENT_BANK_USER.user_id,
        actor_display_name: CURRENT_BANK_USER.display_name, actor_role: CURRENT_BANK_USER.role,
        content, channel, audience: customer ? 'CUSTOMER' : 'BANK_INTERNAL',
        visibility: customer ? 'CUSTOMER' : 'BANK_INTERNAL', message_kind: 'CHAT',
        mentions: [], attachment_ids: attachmentIds, client_request_id: crypto.randomUUID(),
      }),
    });
  },
  invokeAi: (caseId: string) => request<AiInvocationResult>(`/api/cases/${encodeURIComponent(caseId)}/ai/invocations`, {
    method: 'POST',
    body: JSON.stringify({
      prompt: '현재 Shared Case 전체 맥락을 기준으로 확인된 사실, 가장 중요한 위험, 아직 확인할 정보, 다음 권장 조치를 짧게 정리해 주세요.',
      channel: 'TEAM', requester_user_id: CURRENT_BANK_USER.user_id,
      requester_display_name: CURRENT_BANK_USER.display_name, client_request_id: crypto.randomUUID(),
    }),
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
  createAction: (caseId: string, actionType: string, note: string) => request<CaseAction>(`/api/cases/${encodeURIComponent(caseId)}/actions`, {
    method: 'POST', body: JSON.stringify({ action_type: actionType, actor_type: 'BANK_STAFF', note }),
  }),
  uploadAttachment: async (caseId: string, file: File, visibility: MessageVisibility): Promise<Attachment> => {
    const path = `/api/cases/${encodeURIComponent(caseId)}/attachments?file_name=${encodeURIComponent(file.name)}&uploaded_by=${encodeURIComponent(CURRENT_BANK_USER.display_name)}&visibility=${encodeURIComponent(visibility)}`;
    const response = await fetch(apiUrl(path), {
      method: 'POST', headers: { 'Content-Type': file.type || 'application/octet-stream' }, body: file,
    });
    if (!response.ok) throw new Error(await readUploadError(response));
    return response.json() as Promise<Attachment>;
  },
  attachmentUrl: (attachment: Attachment) => apiUrl(attachment.download_url.replace(/\?view=(bank|customer)$/, '?view=bank')),
  sendCustomerMessage: (caseId: string, content: string, attachmentIds: string[] = []) => request<CaseMessage>(`/api/cases/${encodeURIComponent(caseId)}/messages`, {
    method: 'POST',
    body: JSON.stringify({
      actor_type: 'CUSTOMER', actor_user_id: CURRENT_CUSTOMER_USER.user_id,
      actor_display_name: CURRENT_CUSTOMER_USER.display_name, actor_role: CURRENT_CUSTOMER_USER.role,
      content, channel: 'CUSTOMER', audience: 'CUSTOMER', visibility: 'CUSTOMER',
      message_kind: 'CHAT', mentions: [], attachment_ids: attachmentIds,
      client_request_id: crypto.randomUUID(),
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
  ensureCustomerQuestions: (caseId: string) => request<CustomerQuestion[]>(`/api/cases/${encodeURIComponent(caseId)}/ai/customer-questions/ensure`, { method: 'POST' }),
  answerCustomerQuestion: (caseId: string, questionId: string, rawAnswer: string) => request<CustomerQuestion>(`/api/cases/${encodeURIComponent(caseId)}/customer-questions/${encodeURIComponent(questionId)}/answer`, {
    method: 'POST', body: JSON.stringify({
      raw_answer: rawAnswer,
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
      client_request_id: crypto.randomUUID(),
    }),
  }),
};
