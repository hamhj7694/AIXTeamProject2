/**
 * 개선된 상담 흐름
 * 구조: 정보수집 → 브리핑 → 위험도평가 → 조치계획 → 완료
 */

import { Message, RiskSignal, SituationInfo } from '../../types';
import { generateId, getCurrentTimestamp } from '../../utils/helpers';

export type ConsultationStep = 
  | 'initial'           // 초기 상황 선택
  | 'details'           // 상세 정보 수집
  | 'briefing'          // 상황 브리핑
  | 'risk_assessment'   // 위험도 평가
  | 'action_plan'       // 행동 계획
  | 'completion';       // 완료

/**
 * 초기 상황 선택지
 */
export const INITIAL_CHOICES = [
  { id: 'call', label: '전화가 왔어요', value: 'call_received' },
  { id: 'message', label: '문자를 받았어요', value: 'message_received' },
  { id: 'money', label: '송금을 요구받았어요', value: 'money_requested' },
  { id: 'info', label: '개인정보를 요구받았어요', value: 'info_requested' },
  { id: 'app', label: '앱을 설치했어요', value: 'app_installed' },
  { id: 'unsure', label: '잘 모르겠어요', value: 'not_sure' },
];

/**
 * 각 초기 선택 후 다음 질문 매핑
 */
export const NEXT_QUESTIONS: Record<string, { message: string; choices: any[] }> = {
  call_received: {
    message: '전화를 받으신 거군요. 누가 전화를 거셨어요?',
    choices: [
      { id: 'bank', label: '은행 직원이라고 했어요', value: 'bank' },
      { id: 'police', label: '경찰/검찰이라고 했어요', value: 'police' },
      { id: 'unknown', label: '누구인지 알 수 없어요', value: 'unknown' },
    ],
  },
  message_received: {
    message: '문자를 받으신 거군요. 누가 보낸 문자였어요?',
    choices: [
      { id: 'bank', label: '은행이라고 했어요', value: 'bank' },
      { id: 'delivery', label: '배송사라고 했어요', value: 'delivery' },
      { id: 'unknown', label: '출처가 불명확해요', value: 'unknown' },
    ],
  },
  money_requested: {
    message: '송금을 요구받으셨군요. 지금 얼마를 달라고 했어요?',
    choices: [
      { id: 'amount', label: '구체적인 금액을 말씀해주세요', value: 'custom' },
    ],
  },
  info_requested: {
    message: '개인정보를 요구받으셨군요. 어떤 정보를 달라고 했어요?',
    choices: [
      { id: 'phone', label: '휴대폰 번호', value: 'phone' },
      { id: 'id', label: '주민등록번호', value: 'id' },
      { id: 'bank', label: '계좌정보/비밀번호', value: 'bank_info' },
      { id: 'multiple', label: '여러 개를 요구했어요', value: 'multiple' },
    ],
  },
  app_installed: {
    message: '앱을 설치하셨군요. 어떤 앱이라고 했어요?',
    choices: [
      { id: 'bank', label: '은행 앱이라고 했어요', value: 'bank_app' },
      { id: 'security', label: '보안/백신 앱이라고 했어요', value: 'security_app' },
      { id: 'gov', label: '공식기관 앱이라고 했어요', value: 'gov_app' },
      { id: 'unknown', label: '뭐라고 했는지 모르겠어요', value: 'unknown_app' },
    ],
  },
};

/**
 * 심각도별 위험 신호 자동 분류
 */
export const classifyRiskLevel = (signals: RiskSignal[]): 'critical' | 'high' | 'medium' | 'low' => {
  const criticalSignals = signals.filter(s => s.severity === 'high').length;
  
  if (criticalSignals >= 3) return 'critical';
  if (criticalSignals >= 2) return 'high';
  if (criticalSignals >= 1) return 'medium';
  return 'low';
};

/**
 * 위험도에 따른 권장 조치
 */
export const getActionsByRiskLevel = (level: 'critical' | 'high' | 'medium' | 'low'): string[] => {
  const actions = {
    critical: [
      '⛔ 지금 바로 모든 행동을 멈추세요',
      '📞 은행에 즉시 전화 (24시간): 해당 은행 고객센터',
      '🚨 경찰 신고: 112 (사이버 사기)',
      '📋 금융감시원 신고: 1332',
      '💳 의심 거래 있으면 계좌 정지 요청',
      '📱 설치한 앱 즉시 삭제',
    ],
    high: [
      '🛑 지금 행동하지 마세요 - 먼저 확인하세요',
      '☎️ 은행/기관에 공식 번호로 직접 확인',
      '👨‍👩‍👧 가족이나 친구와 상의해보세요',
      '📞 경찰 신고 고려: 112',
      '💡 안전 안내 탭에서 더 자세한 정보 확인',
    ],
    medium: [
      '⚠️ 신중하게 대응하세요',
      '✅ 공식 기관 번호로 확인 필수',
      '📌 개인정보 절대 공개 금지',
      '📱 의심 앱은 설치하지 마세요',
    ],
    low: [
      'ℹ️ 일단 안전한 상황입니다',
      '🔍 계속 의심스러운 점이 있으면 신고하세요',
      '💡 항상 신중함이 최고의 방어입니다',
    ],
  };

  return actions[level];
};

/**
 * 브리핑 메시지 생성
 */
export const generateBriefing = (situations: SituationInfo[]): string => {
  if (!situations || situations.length === 0) {
    return '상담을 정리했습니다.';
  }

  let briefing = '지금까지 말씀해주신 상황:\n\n';
  
  situations.forEach((sit, idx) => {
    briefing += `${idx + 1}. ${sit.description}\n`;
  });

  return briefing;
};

/**
 * 위험 신호 요약
 */
export const summarizeRiskSignals = (signals: RiskSignal[]): string => {
  if (!signals || signals.length === 0) {
    return '위험 신호가 감지되지 않았습니다.';
  }

  let summary = '⚠️ 감지된 위험 신호:\n\n';
  const highSignals = signals.filter(s => s.severity === 'high');
  const mediumSignals = signals.filter(s => s.severity === 'medium');

  if (highSignals.length > 0) {
    summary += '🔴 높은 위험:\n';
    highSignals.forEach(sig => {
      summary += `• ${sig.signal}\n`;
    });
  }

  if (mediumSignals.length > 0) {
    summary += '\n🟡 중간 위험:\n';
    mediumSignals.forEach(sig => {
      summary += `• ${sig.signal}\n`;
    });
  }

  return summary;
};

/**
 * 상담 완료 메시지
 */
export const getCompletionMessage = (): string => {
  return `상담을 완료했습니다.

더 많은 정보는 "안전 안내" 탭에서 확인할 수 있습니다.

긴급 연락처:
📞 경찰청: 112
📞 금융감시원: 1332
📞 정보통신신문고: 1336

혹시 피해가 발생하셨다면 즉시 신고해주세요.`;
};
