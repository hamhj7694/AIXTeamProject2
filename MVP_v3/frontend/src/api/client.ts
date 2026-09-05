import { presentResponse, userText } from '../userText';
const baseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

export const apiUrl = (path: string) => `${baseUrl}${path}`;

export const errorMessage = (payload: unknown, status: number) => {
  const codes: Record<string, string> = {
    CASE_NOT_FOUND: '사건을 찾을 수 없습니다. 목록을 새로고침해 주세요.',
    VERSION_CONFLICT: '다른 담당자가 먼저 내용을 변경했습니다. 최신 정보를 다시 불러와 주세요.',
    CUSTOMER_QUESTION_NOT_FOUND: '응답 대기 중인 질문을 찾을 수 없습니다. 최신 내용을 확인해 주세요.',
    CUSTOMER_ANSWER_CONFLICT: '이미 다른 답변이 저장된 질문입니다. 최신 내용을 확인해 주세요.',
    VERIFICATION_NOT_FOUND: '기관 확인 기록을 찾을 수 없습니다.',
    FINAL_REPORT_NOT_FOUND: '아직 생성된 최종 보고서가 없습니다.',
    ADMIN_AUTH_FAILED: '관리자 비밀번호가 올바르지 않습니다.',
    ADMIN_AUTH_NOT_CONFIGURED: '관리자 암호 설정이 필요합니다.',
    OPENAI_AUTHENTICATION_FAILED: 'AI 연결 인증에 실패했습니다. 관리자에게 API 키 설정 확인을 요청해 주세요.',
    OPENAI_QUOTA_EXHAUSTED: 'AI 사용 한도에 도달했습니다. 관리자에게 사용량 확인을 요청해 주세요.',
    AI_FINAL_REPORT_FAILED: 'AI 최종 보고서 생성에 실패했습니다. 연결 상태 확인 후 다시 시도해 주세요.',
  };
  if (payload && typeof payload === 'object') {
    const body = payload as { error?: { code?: unknown; message?: unknown }; detail?: unknown };
    const detail = body.error ?? (body.detail && typeof body.detail === 'object' && !Array.isArray(body.detail) ? body.detail as { code?: unknown; message?: unknown } : undefined);
    if (typeof detail?.code === 'string' && codes[detail.code]) return codes[detail.code];
    const message = detail?.message ?? body.detail;
    if (typeof message === 'string' && /[가-힣]/.test(message)) return userText(message);
    if (Array.isArray(body.detail)) {
      const fieldLabels: Record<string, string> = { status: '처리 상태', note: '체크리스트 내용', updated_by: '수정 담당자' };
      const reasons = body.detail.flatMap((item) => {
        if (!item || typeof item !== 'object') return [];
        const issue = item as { loc?: unknown[]; msg?: unknown };
        const field = String(issue.loc?.[issue.loc.length - 1] ?? '입력값');
        const label = fieldLabels[field] ?? '입력값';
        return [`${label}의 형식이나 허용된 값을 확인해 주세요.`];
      });
      if (reasons.length) return `입력값이 서버 규칙에 맞지 않습니다. ${reasons.join(' ')}`;
    }
  }
  if (status === 404) return '요청한 Case 또는 기능을 찾을 수 없습니다.';
  if (status === 401) return 'AI 서버 인증에 실패했습니다. 관리자에게 연결 설정을 확인해 달라고 요청해 주세요.';
  if (status === 403) return '요청을 수행할 권한 또는 관리자 암호를 확인해 주세요.';
  if (status === 429) return 'AI 사용 한도에 도달해 현재 답변을 생성할 수 없습니다. 잠시 후 다시 시도해 주세요.';
  if (status === 409) return '다른 담당자가 먼저 내용을 변경했습니다. 최신 정보를 다시 불러와 주세요.';
  if (status === 422) return '입력값이 현재 서버 규칙에 맞지 않습니다. General API가 최신 코드인지 확인해 주세요.';
  if (status === 503) return '서버 연결 또는 처리에 실패했습니다. 잠시 후 다시 시도해 주세요.';
  return `요청을 처리하지 못했습니다. (${status})`;
};

export const request = async <T>(path: string, init?: RequestInit): Promise<T> => {
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  let response: Response;
  try {
    response = await fetch(apiUrl(path), { ...init, headers });
  } catch {
    throw new Error('서버에 연결할 수 없습니다. 네트워크와 서버 실행 상태를 확인해 주세요.');
  }
  if (response.status === 204) return undefined as T;
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new Error(errorMessage(payload, response.status));
  return presentResponse(payload) as T;
};

export const readUploadError = async (response: Response) => {
  const payload: unknown = await response.json().catch(() => null);
  return errorMessage(payload, response.status);
};
