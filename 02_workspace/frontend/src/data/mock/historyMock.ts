import { ConsultationHistory } from '../../types';
import { generateId } from '../../utils/helpers';

/**
 * Mock 상담 기록 데이터
 */
export const MOCK_CONSULTATION_HISTORY: ConsultationHistory[] = [
  {
    id: generateId(),
    title: '은행 직원 사칭 상담 - 계좌 보안',
    scenario: 'bank_impersonation',
    status: 'completed',
    riskLevel: 'high',
    summary: '은행 직원을 사칭한 전화를 받고 송금을 요구받은 상황',
    completedActions: ['전화 종료', '은행 직접 확인', '신고'],
    startedAt: Date.now() - 86400000 * 7, // 7일 전
    completedAt: Date.now() - 86400000 * 7 + 3600000, // 1시간 후 완료
  },
  {
    id: generateId(),
    title: '문자 링크 의심 상담',
    scenario: 'phishing_link',
    status: 'completed',
    riskLevel: 'medium',
    summary: '낯선 번호에서 보낸 문자에 포함된 링크를 클릭해야 하는 상황',
    completedActions: ['링크 클릭 거절', '발신처 확인'],
    startedAt: Date.now() - 86400000 * 3, // 3일 전
    completedAt: Date.now() - 86400000 * 3 + 1800000, // 30분 후 완료
  },
  {
    id: generateId(),
    title: '앱 설치 요청 상담',
    scenario: 'malicious_app',
    status: 'completed',
    riskLevel: 'high',
    summary: '금융 서비스라고 가장한 앱 설치를 요구받은 상황',
    completedActions: ['앱 설치 거절', '계좌 보안 확인'],
    startedAt: Date.now() - 86400000 * 1, // 1일 전
    completedAt: Date.now() - 86400000 * 1 + 2400000, // 40분 후 완료
  },
];

/**
 * Mock 상담 기록 조회
 */
export const getConsultationHistories = (): ConsultationHistory[] => {
  return MOCK_CONSULTATION_HISTORY;
};

/**
 * Mock 상담 기록 상세 조회
 */
export const getConsultationHistory = (id: string): ConsultationHistory | null => {
  return MOCK_CONSULTATION_HISTORY.find(h => h.id === id) || null;
};
