import { presentResponse, userText } from '../userText';
const baseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

export const apiUrl = (path: string) => `${baseUrl}${path}`;

const errorMessage = (payload: unknown, status: number) => {
  if (payload && typeof payload === 'object') {
    const body = payload as { error?: { message?: unknown }; detail?: string | { message?: unknown } };
    if (typeof body.error?.message === 'string') return userText(body.error.message);
    if (typeof body.detail === 'string') return userText(body.detail);
    if (body.detail && typeof body.detail === 'object' && typeof body.detail.message === 'string') return userText(body.detail.message);
  }
  if (status === 404) return '요청한 Case 또는 기능을 찾을 수 없습니다.';
  if (status === 401) return 'AI 서버 인증에 실패했습니다. 관리자에게 연결 설정을 확인해 달라고 요청해 주세요.';
  if (status === 429) return 'AI 사용 한도에 도달해 현재 답변을 생성할 수 없습니다. 잠시 후 다시 시도해 주세요.';
  if (status === 409) return '다른 담당자가 먼저 내용을 변경했습니다. 최신 정보를 다시 불러와 주세요.';
  if (status === 503) return '실제 AI 서버에 연결하지 못했습니다. 임의 답변은 생성하지 않았습니다. 잠시 후 다시 시도해 주세요.';
  return `요청을 처리하지 못했습니다. (${status})`;
};

export const request = async <T>(path: string, init?: RequestInit): Promise<T> => {
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  const response = await fetch(apiUrl(path), { ...init, headers });
  if (response.status === 204) return undefined as T;
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new Error(errorMessage(payload, response.status));
  return presentResponse(payload) as T;
};

export const readUploadError = async (response: Response) => {
  const payload: unknown = await response.json().catch(() => null);
  return errorMessage(payload, response.status);
};
