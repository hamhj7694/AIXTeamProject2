import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./api/cases', () => ({
  casesApi: {
    analyze: vi.fn(),
    get: vi.fn(),
  },
}));

import { casesApi } from './api/cases';
import { loadNotifications } from './components/NotificationCenter';
import { startBackgroundAnalysis } from './analysisQueue';

describe('analysis feedback notifications', () => {
  let storedValue: string;

  beforeEach(() => {
    storedValue = '[]';
    vi.stubGlobal('crypto', { randomUUID: () => 'notification-id' });
    vi.stubGlobal('window', {
      localStorage: {
        getItem: () => storedValue,
        setItem: (_key: string, value: string) => { storedValue = value; },
      },
      dispatchEvent: vi.fn(),
      setTimeout,
    });
    vi.mocked(casesApi.analyze).mockReset();
  });

  afterEach(() => { vi.unstubAllGlobals(); });

  it('publishes an alert when the analysis request rejects', async () => {
    vi.mocked(casesApi.analyze).mockRejectedValueOnce(new Error('분석 서버에 연결할 수 없습니다.'));

    await expect(startBackgroundAnalysis('비공개 통화 내용', 'request-1'))
      .rejects.toThrow('분석 서버에 연결할 수 없습니다.');

    expect(loadNotifications()).toMatchObject([{
      title: '통화 분석 요청 실패',
      message: '분석 서버에 연결할 수 없습니다.',
      tone: 'error',
      read: false,
    }]);
  });

  it('publishes an informational alert when analysis finishes without creating a Case', async () => {
    vi.mocked(casesApi.analyze).mockResolvedValueOnce({
      schema_version: 'case-analysis.v1', disposition: 'NO_CASE',
      initial_brief: '정상 금융 상담', analysis_status: 'NO_CASE',
    });

    await startBackgroundAnalysis('통화 내용', 'request-2');

    expect(loadNotifications()).toMatchObject([{
      title: '분석 완료 · Case 미생성',
      tone: 'info',
      read: false,
    }]);
  });
});
