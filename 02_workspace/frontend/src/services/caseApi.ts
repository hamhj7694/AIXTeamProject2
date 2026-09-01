import { CaseDetail, CaseRecord } from '../data/mock/caseData';

export type AnalyzeDisposition = 'CASE_CREATED' | 'NO_CASE' | 'FAILED';

export interface AnalyzeResponse {
  schema_version: string;
  disposition: AnalyzeDisposition;
  case_id: string | null;
  risk: 'NORMAL' | 'LOW' | 'HIGH' | null;
  mode: 'PREVENT' | null;
  status: 'TRIAGE' | null;
  initial_brief: string | null;
  initial_report?: { report_id: string; case_id: string; report_version: number } | null;
  error?: { code: string; message: string; retryable: boolean } | null;
}

interface StoredCaseResponse {
  case_id: string;
  risk: CaseRecord['risk'];
  mode: string;
  status: string;
  initial_brief: string;
  initial_report: { report_id: string; case_id: string; report_version: number } | null;
  diagnosis: {
    context: { summary: string; incident_type: string; claims: string[] };
    evidence: Array<{ text: string }>;
    features: Record<string, number>;
  };
  created_at: string;
  updated_at: string;
}

// 개발환경은 Vite의 same-origin /api proxy를 사용한다.
// 배포환경에서 별도 API origin이 필요할 때만 VITE_API_BASE_URL을 지정한다.
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

const request = async <T>(path: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.detail;
    const message = payload?.error?.message || detail?.error?.message || detail?.message || '서버에서 진단을 완료하지 못했습니다.';
    throw new Error(message);
  }
  return payload as T;
};

const formatDateTime = (value: string) => {
  const date = new Date(value);
  const today = new Date();
  const dateOnly = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
  const todayOnly = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime();
  const dayLabel = dateOnly === todayOnly ? '오늘' : dateOnly === todayOnly - 86400000 ? '어제' : date.toLocaleDateString('ko-KR');
  return `${dayLabel} ${date.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}`;
};

const toCaseDetail = (record: StoredCaseResponse): CaseDetail => {
  const amount = record.diagnosis.features.requested_amount_max || 0;
  const evidence = record.diagnosis.evidence.map((item) => item.text);
  return {
    id: record.case_id,
    type: record.diagnosis.context.incident_type,
    risk: record.risk,
    status: '확인중',
    amount: amount > 0 ? `${amount.toLocaleString('ko-KR')}원` : undefined,
    transferred: false,
    summary: record.diagnosis.context.summary || record.initial_brief,
    createdAt: formatDateTime(record.created_at),
    updatedAt: formatDateTime(record.updated_at),
    victimStatus: '확인 필요',
    aiInitialBrief: record.initial_brief,
    bankInfo: 'AI 진단 결과와 원문 근거를 바탕으로 담당자 확인이 필요합니다.',
    consumerInfo: '확인 전까지 송금과 정보 제공을 중단하고 공식 채널로 확인하세요.',
    verificationBrief: evidence.join(' · ') || '추가 사실 확인이 필요합니다.',
    verificationQuestions: evidence.slice(0, 3).map((text, index) => ({ id: index + 1, question: `“${text}” 내용이 사실인지 확인해 주세요.` })),
  };
};

export const caseApi = {
  list: async (): Promise<CaseRecord[]> => (await request<StoredCaseResponse[]>('/api/cases')).map(toCaseDetail),
  get: async (caseId: string): Promise<CaseDetail> =>
    toCaseDetail(await request<StoredCaseResponse>(`/api/cases/${encodeURIComponent(caseId)}`)),
  analyze: async (text: string): Promise<AnalyzeResponse> => request('/api/cases/analyze', {
    method: 'POST',
    body: JSON.stringify({ text, client_request_id: crypto.randomUUID() }),
  }),
};
