import { casesApi } from './api/cases';
import type { AnalyzeCaseResponse } from './api/types';
import { publishAnalysisNotification } from './components/NotificationCenter';

type Pending = Promise<AnalyzeCaseResponse>;
const pending = new Map<string, Pending>();
export const analysisPendingEventName = 'csr:analysis-pending-changed';
export const getPendingAnalysisCount = () => pending.size;
const notifyPendingAnalysisChanged = () => {
  if (typeof window !== 'undefined') window.dispatchEvent(new CustomEvent(analysisPendingEventName));
};

/** Keeps an in-flight analysis alive when the analysis panel unmounts during SPA navigation. */
export const startBackgroundAnalysis = (text: string, requestId: string): Pending => {
  const existing = pending.get(requestId);
  if (existing) return existing;
  const request = casesApi.analyze(text, requestId).then((response) => {
    const subject = (response.initial_brief || '통화 분석 요청').replace(/\s+/g, ' ').trim().slice(0, 90);
    if (response.disposition === 'CASE_CREATED' && response.case_id) {
      publishAnalysisNotification({ title: '새 Case가 생성되었습니다', message: `‘${subject}’ 관련 분석에서 보이스피싱 의심으로 판정되어 Case ${response.case_id}가 생성되었습니다.`, tone: 'success' });
    } else if (response.disposition === 'NO_CASE') {
      publishAnalysisNotification({ title: '분석 완료 · Case 미생성', message: `‘${subject}’ 관련 분석은 보이스피싱으로 판정되지 않아 Case를 생성하지 않았습니다.`, tone: 'info' });
    } else if (response.disposition === 'FAILED') {
      publishAnalysisNotification({ title: '통화 분석 실패', message: `‘${subject}’ 관련 분석을 완료하지 못했습니다. 다시 시도해 주세요.`, tone: 'info' });
    }
    return response;
  }).finally(() => { pending.delete(requestId); notifyPendingAnalysisChanged(); });
  pending.set(requestId, request);
  notifyPendingAnalysisChanged();
  return request;
};
