import { afterEach, describe, expect, it, vi } from 'vitest';
import { errorMessage, request } from './client';

afterEach(() => { vi.unstubAllGlobals(); });

describe('analysis provider error messages', () => {
  it('explains that provider connectivity failed separately from API server health', () => {
    expect(errorMessage({
      detail: {
        code: 'AI_PROVIDER_UNAVAILABLE',
        message: 'AI 서버에서 외부 AI 서비스에 연결하지 못했습니다.',
      },
    }, 503)).toContain('AI 서버에는 연결됐지만 외부 AI 제공자(OpenAI API)에 연결하지 못했습니다.');
  });

  it('keeps authentication and quota failures distinct from connection failures', () => {
    expect(errorMessage({ detail: { code: 'OPENAI_AUTHENTICATION_FAILED' } }, 401))
      .toContain('AI 연결 인증에 실패했습니다.');
    expect(errorMessage({ detail: { code: 'OPENAI_QUOTA_EXHAUSTED' } }, 429))
      .toContain('AI 사용 한도에 도달했습니다.');
  });
});

describe('API timeout', () => {
  it('shows a retryable Korean error when the server does not respond', async () => {
    const timeout = new Error('The operation was aborted due to timeout');
    timeout.name = 'TimeoutError';
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(timeout));

    await expect(request('/api/cases')).rejects.toThrow('서버 응답 시간이 초과되었습니다.');
  });
});
