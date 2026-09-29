import { casesApi } from './api/cases';
import type { AnalyzeCaseResponse } from './api/types';
import { publishAnalysisNotification } from './components/NotificationCenter';

type Pending = Promise<AnalyzeCaseResponse>;
const pending = new Map<string, Pending>();
const BACKGROUND_ANALYSIS_POLLS = 90;
const BACKGROUND_ANALYSIS_POLL_MS = 4_000;
export const analysisPendingEventName = 'csr:analysis-pending-changed';
export const getPendingAnalysisCount = () => pending.size;
const notifyPendingAnalysisChanged = () => {
  if (typeof window !== 'undefined') window.dispatchEvent(new CustomEvent(analysisPendingEventName));
};

const delay = (milliseconds: number) => new Promise<void>((resolve) => window.setTimeout(resolve, milliseconds));

const monitorBackgroundAnalysis = async (caseId: string) => {
  for (let attempt = 0; attempt < BACKGROUND_ANALYSIS_POLLS; attempt += 1) {
    await delay(BACKGROUND_ANALYSIS_POLL_MS);
    let caseItem;
    try { caseItem = await casesApi.get(caseId); }
    catch { continue; }
    if (caseItem.analysis_status === 'IN_PROGRESS') continue;
    if (caseItem.analysis_status === 'COMPLETED') {
      publishAnalysisNotification({
        title: '전체 통화 분석 완료',
        message: `Case ${caseId}의 전체 통화 분석 결과가 반영되었습니다.`,
        tone: 'success',
      });
    } else if (caseItem.analysis_status === 'NO_CASE') {
      publishAnalysisNotification({
        title: '전체 분석 완료 · Case 기준 미해당',
        message: `Case ${caseId}의 전체 분석 결과는 생성 기준에 해당하지 않았습니다. 초기 분석 기록은 보존되어 있습니다.`,
        tone: 'info',
      });
    } else {
      publishAnalysisNotification({
        title: '전체 통화 분석 실패',
        message: `Case ${caseId}는 생성됐지만 전체 분석 결과 반영에 실패했습니다. Case 상태와 서버 연결을 확인해 주세요.`,
        tone: 'error',
      });
    }
    return;
  }
  publishAnalysisNotification({
    title: '전체 통화 분석 상태 확인 지연',
    message: `Case ${caseId}의 분석이 아직 진행 중이거나 서버 응답을 확인하지 못했습니다. Case 목록에서 상태를 확인해 주세요.`,
    tone: 'info',
  });
};

/** Keeps an in-flight analysis alive when the analysis panel unmounts during SPA navigation. */
export const startBackgroundAnalysis = (text: string, requestId: string, backgroundCompletion = false): Pending => {
  const existing = pending.get(requestId);
  if (existing) return existing;
  const request = casesApi.analyze(text, requestId, backgroundCompletion).then((response) => {
    const subject = (response.initial_brief || '통화 분석 요청').replace(/\s+/g, ' ').trim().slice(0, 90);
    if (response.disposition === 'CASE_CREATED' && response.case_id) {
      publishAnalysisNotification({ title: response.analysis_status === 'IN_PROGRESS' ? '잠정 Case가 생성되었습니다' : '새 Case가 생성되었습니다', message: response.analysis_status === 'IN_PROGRESS' ? `Case ${response.case_id}가 먼저 생성되었으며, 전체 통화 분석 결과가 백그라운드에서 반영됩니다.` : `‘${subject}’ 관련 분석에서 보이스피싱 의심으로 판정되어 Case ${response.case_id}가 생성되었습니다.`, tone: 'success' });
      if (response.analysis_status === 'IN_PROGRESS') void monitorBackgroundAnalysis(response.case_id);
    } else if (response.disposition === 'NO_CASE') {
      publishAnalysisNotification({ title: '분석 완료 · Case 미생성', message: `‘${subject}’ 관련 분석은 보이스피싱으로 판정되지 않아 Case를 생성하지 않았습니다.`, tone: 'info' });
    } else if (response.disposition === 'FAILED') {
      publishAnalysisNotification({ title: '통화 분석 실패', message: `‘${subject}’ 관련 분석을 완료하지 못했습니다. 다시 시도해 주세요.`, tone: 'error' });
    }
    return response;
  }).catch((reason: unknown) => {
    const message = reason instanceof Error && reason.message.trim()
      ? reason.message.trim()
      : '통화 분석 요청을 완료하지 못했습니다. 서버 연결 상태를 확인하고 다시 시도해 주세요.';
    publishAnalysisNotification({ title: '통화 분석 요청 실패', message, tone: 'error' });
    throw reason;
  }).finally(() => { pending.delete(requestId); notifyPendingAnalysisChanged(); });
  pending.set(requestId, request);
  notifyPendingAnalysisChanged();
  return request;
};
