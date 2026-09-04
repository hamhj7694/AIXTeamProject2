import { generalApiRequest as request } from './generalApiClient';

export type CaseRisk = 'NORMAL' | 'LOW' | 'HIGH';

export interface CaseRecord {
  id: string; type: string; risk: CaseRisk; status: string; amount?: string; transferred: boolean | null;
  summary: string; createdAt: string; updatedAt: string; createdAtRaw: string; updatedAtRaw: string; assignee: string | null;
}

export interface CaseDetail extends CaseRecord {
  aiInitialBrief: string;
  mode: 'PREVENT' | 'RECOVERY' | null;
  victim_transfer_status: 'UNKNOWN' | 'YES' | 'NO';
  victimStatus: string;
  bankInfo: string;
  consumerInfo: string;
  verificationBrief: string;
  verificationQuestions: Array<{ id: number; question: string }>;
}

export type AnalyzeDisposition = 'CASE_CREATED' | 'NO_CASE' | 'FAILED';
export interface AnalyzeResponse {
  schema_version: string; disposition: AnalyzeDisposition; case_id: string | null; risk: CaseRisk | null;
  mode: 'PREVENT' | 'RECOVERY' | null; status: 'TRIAGE' | null; initial_brief: string | null;
  initial_report?: { report_id: string; case_id: string; report_version: number } | null;
  error?: { code: string; message: string; retryable: boolean } | null;
}

interface StoredCaseResponse {
  case_id: string; risk: CaseRisk; mode: string; status: string; initial_brief: string; primary_assignee?: string | null; victim_transfer_status?: 'UNKNOWN' | 'YES' | 'NO'; actual_loss_amount_krw?: number | null;
  diagnosis: { context: { summary: string; incident_type: string; claims: string[] }; evidence: Array<{ text: string }>; features: Record<string, number> };
  created_at: string; updated_at: string;
}

const formatDateTime = (value: string) => new Date(value).toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false });

const toCaseDetail = (record: StoredCaseResponse): CaseDetail => {
  const amount = record.diagnosis.features.requested_amount_max || 0;
  const evidence = record.diagnosis.evidence.map((item) => item.text);
  return {
    id: record.case_id, type: record.diagnosis.context.incident_type || '의심 통화', risk: record.risk, status: record.status,
    amount: record.actual_loss_amount_krw !== null && record.actual_loss_amount_krw !== undefined ? `${record.actual_loss_amount_krw.toLocaleString('ko-KR')}원` : undefined,
    transferred: record.victim_transfer_status === 'YES' ? true : record.victim_transfer_status === 'NO' ? false : null,
    summary: record.diagnosis.context.summary || record.initial_brief,
    createdAt: formatDateTime(record.created_at), updatedAt: formatDateTime(record.updated_at),
    createdAtRaw: record.created_at, updatedAtRaw: record.updated_at, assignee: record.primary_assignee ?? null,
    aiInitialBrief: record.initial_brief,
    mode: record.mode === 'RECOVERY' ? 'RECOVERY' : record.mode === 'PREVENT' ? 'PREVENT' : null,
    victim_transfer_status: record.victim_transfer_status ?? 'UNKNOWN',
    victimStatus: '확인 필요',
    bankInfo: '담당자 확인이 필요합니다.',
    consumerInfo: '확인 전까지 송금과 개인정보 제공을 중단하세요.',
    verificationBrief: evidence.join(' · ') || '확인 가능한 분석 근거가 아직 없습니다.',
    verificationQuestions: evidence.slice(0, 3).map((text, index) => ({ id: index + 1, question: `'${text}' 내용이 사실인지 확인해 주세요.` })),
  };
};

export const caseApi = {
  list: async (): Promise<CaseRecord[]> => (await request<StoredCaseResponse[]>('/api/cases')).map(toCaseDetail),
  get: async (caseId: string): Promise<CaseDetail> => toCaseDetail(await request<StoredCaseResponse>(`/api/cases/${encodeURIComponent(caseId)}`)),
  analyze: async (text: string): Promise<AnalyzeResponse> => request('/api/cases/analyze', { method: 'POST', body: JSON.stringify({ text, client_request_id: crypto.randomUUID() }) }),
  setPrimaryAssignee: async (caseId: string, displayName: string | null): Promise<{ case_id: string; display_name: string | null }> =>
    request(`/api/cases/${encodeURIComponent(caseId)}/assignee`, { method: 'PUT', body: JSON.stringify({ display_name: displayName }) }),
  permanentlyDelete: async (caseId: string, password: string): Promise<void> => {
    await request(`/api/cases/${encodeURIComponent(caseId)}`, { method: 'DELETE', body: JSON.stringify({ password }) });
  },
  verifyAdministratorPassword: async (password: string): Promise<void> => {
    await request('/api/cases/admin/verify-password', { method: 'POST', body: JSON.stringify({ password }) });
  },
  listTrash: async (): Promise<CaseRecord[]> => (await request<StoredCaseResponse[]>('/api/cases/trash')).map(toCaseDetail),
  restoreFromTrash: async (caseId: string): Promise<void> => {
    await request(`/api/cases/${encodeURIComponent(caseId)}/restore`, { method: 'POST' });
  },
  updateOutcome: async (caseId: string, expectedVersion: number, victimTransferStatus: 'UNKNOWN' | 'YES' | 'NO', actualLossAmountKrw?: number): Promise<CaseDetail> =>
    toCaseDetail(await request<StoredCaseResponse>(`/api/cases/${encodeURIComponent(caseId)}/outcome`, { method: 'PUT', body: JSON.stringify({ expected_version: expectedVersion, victim_transfer_status: victimTransferStatus, actual_loss_amount_krw: actualLossAmountKrw ?? null }) })),
};
