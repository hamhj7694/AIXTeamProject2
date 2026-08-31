import { ConsultationSession, Message, RiskSignal, SituationInfo } from '../../types';
import { generateId, getCurrentTimestamp } from '../../utils/helpers';

/**
 * 상담 흐름 시나리오
 * 사용자의 선택에 따라 다른 AI 메시지를 반환
 */

// 은행 사칭 시나리오
export const BANK_IMPERSONATION_FLOW = {
  // 1단계: 상황 확인
  initialMessage: {
    id: generateId(),
    role: 'assistant' as const,
    type: 'text' as const,
    content: '잠시만요.\n지금 어떤 상황인지 제가 하나씩 같이 확인해드릴게요.\n혼자 판단하지 않으셔도 괜찮아요.',
    createdAt: getCurrentTimestamp(),
  },

  initialQuestion: {
    id: generateId(),
    role: 'assistant' as const,
    type: 'question' as const,
    content: '지금 어떤 상황인가요?',
    choices: [
      { id: 'call', label: '전화가 왔어요', value: 'call_received' },
      { id: 'message', label: '문자를 받았어요', value: 'message_received' },
      { id: 'money', label: '송금을 요구받았어요', value: 'money_requested' },
      { id: 'info', label: '개인정보를 요구받았어요', value: 'info_requested' },
      { id: 'app', label: '앱을 설치했어요', value: 'app_installed' },
      { id: 'unsure', label: '잘 모르겠어요', value: 'not_sure' },
    ],
    createdAt: getCurrentTimestamp(),
  },

  // 전화 수신 → 상대방 정보
  afterCallReceived: {
    id: generateId(),
    role: 'assistant' as const,
    type: 'question' as const,
    content: '전화를 받으신 거군요. 누가 전화를 거셨어요?',
    choices: [
      { id: 'bank', label: '은행 직원이라고 했어요', value: 'bank_claimed' },
      { id: 'prosecutor', label: '검찰, 경찰이라고 했어요', value: 'prosecutor_claimed' },
      { id: 'company', label: '회사나 기관이라고 했어요', value: 'company_claimed' },
      { id: 'personal', label: '가족이나 친구라고 했어요', value: 'personal_claimed' },
      { id: 'unsure2', label: '누구인지 잘 모르겠어요', value: 'unknown_caller' },
    ],
    createdAt: getCurrentTimestamp(),
  },

  // 은행 직원 사칭 → 이유 확인
  afterBankClaimed: {
    id: generateId(),
    role: 'assistant' as const,
    type: 'question' as const,
    content: '은행 직원이라고 하셨군요. 무엇 때문에 전화했다고 했어요?',
    choices: [
      { id: 'fraud', label: '계좌가 범죄에 이용됐다고 했어요', value: 'account_fraud_claim' },
      { id: 'loan', label: '금리 인하, 대출을 제안했어요', value: 'loan_offer' },
      { id: 'security', label: '계좌 보안 점검이라고 했어요', value: 'security_check_claim' },
      { id: 'money_move', label: '계좌 잔액을 옮겨야 한다고 했어요', value: 'money_transfer_claim' },
      { id: 'unsure3', label: '이유가 명확하지 않아요', value: 'reason_unclear' },
    ],
    createdAt: getCurrentTimestamp(),
  },

  // 송금 요구 확인
  afterFraudClaim: {
    id: generateId(),
    role: 'assistant' as const,
    type: 'question' as const,
    content: '그렇군요. 그 상황을 해결하기 위해 어떤 행동을 하라고 했어요?',
    choices: [
      { id: 'transfer', label: '다른 계좌로 송금하라고 했어요', value: 'transfer_demanded' },
      { id: 'verify', label: '비밀번호나 인증번호를 알려달라고 했어요', value: 'verify_demanded' },
      { id: 'app', label: '앱을 깔거나 설치해달라고 했어요', value: 'app_demanded' },
      { id: 'meeting', label: '어디서 만나자고 했어요', value: 'meeting_proposed' },
      { id: 'nothing', label: '아직 구체적으로 뭔가 하라고 하지 않았어요', value: 'no_action_yet' },
    ],
    createdAt: getCurrentTimestamp(),
  },

  // 송금 요구 후 위험도 상승
  afterTransferDemanded: {
    id: generateId(),
    role: 'assistant' as const,
    type: 'question' as const,
    content: '송금을 요구했군요. 언제까지 송금하라고 했어요?',
    choices: [
      { id: 'urgent', label: '지금 바로, 오늘 중에 해야 한다고 했어요', value: 'urgent_demand' },
      { id: 'soon', label: '빨리, 내일까지라고 했어요', value: 'soon_demand' },
      { id: 'normal', label: '시간 제한이 없었어요', value: 'no_time_limit' },
      { id: 'threat', label: '안 하면 큰일 난다고 협박했어요', value: 'threat' },
    ],
    createdAt: getCurrentTimestamp(),
  },

  // 브리핑
  briefing: {
    id: generateId(),
    role: 'assistant' as const,
    type: 'text' as const,
    content: '지금까지 말씀해주신 내용을 한 번 같이 볼게요.',
    createdAt: getCurrentTimestamp(),
  },

  briefingDetail: {
    id: generateId(),
    role: 'assistant' as const,
    type: 'text' as const,
    content: '현재까지 확인된 내용:\n• 은행 직원이라고 소개한 사람이 전화를 함\n• 계좌가 범죄에 이용되었다고 설명함\n• 다른 계좌로 돈을 보내라고 요구함\n• 지금 바로 송금하라고 긴급을 강조함\n\n이런 상황에서는 신중하게 확인이 필요해요.',
    createdAt: getCurrentTimestamp(),
  },

  // 행동 개입
  actionIntervention: {
    id: generateId(),
    role: 'assistant' as const,
    type: 'warning' as const,
    content: '지금은 송금을 잠시 멈춰주세요.\n\n지금까지 확인한 상황을 먼저 확인한 뒤 안전한 방법으로 처리하는 것이 좋습니다.',
    createdAt: getCurrentTimestamp(),
  },

  // 안전 확인 단계
  safetyCheckPhase: {
    id: generateId(),
    role: 'assistant' as const,
    type: 'question' as const,
    content: '지금 이 전화를 받기 직전에 무엇을 하고 있었어요?',
    choices: [
      { id: 'nothing', label: '평상시처럼 일상을 하고 있었어요', value: 'normal_activity' },
      { id: 'after_search', label: '뭔가를 검색하거나 신청한 직후였어요', value: 'after_search' },
      { id: 'unknown_reason', label: '갑자기 전화가 왔어요', value: 'sudden_call' },
    ],
    createdAt: getCurrentTimestamp(),
  },

  // 최종 권고
  finalRecommendation: {
    id: generateId(),
    role: 'assistant' as const,
    type: 'text' as const,
    content: '당신이 말씀해주신 상황에는 여러 가지 이상한 점들이 있습니다.\n\n다음과 같이 확인해주세요:\n\n1. 전화를 끊고 은행 공식 번호로 직접 전화하기\n2. 은행 앱에서 나의 계좌 상태 직접 확인하기\n3. 의심되면 즉시 신고하기',
    createdAt: getCurrentTimestamp(),
  },

  // 결과
  result: {
    situationSummary: '은행을 사칭한 피싱 의심 상황',
    riskLevel: 'high' as const,
    detectedSignals: [
      { id: '1', signal: '금융기관을 사칭', severity: 'high' as const },
      { id: '2', signal: '긴급 송금을 요구', severity: 'high' as const },
      { id: '3', signal: '계좌 문제를 이유로 금전을 요구', severity: 'high' as const },
      { id: '4', signal: '빠른 처리를 강요', severity: 'medium' as const },
    ],
    recommendedActions: [
      '즉시 전화 종료',
      '은행 공식 번호로 직접 문의',
      '계좌 상태 확인',
      '의심 거래 신고',
      '가족이나 지인에게 알리기',
    ],
  },
};

/**
 * 새 상담 세션 생성
 */
export const createNewConsultationSession = (): ConsultationSession => {
  return {
    id: generateId(),
    status: 'in_progress',
    currentStep: 'situation_check',
    userState: 'S0',
    riskLevel: 'low',
    messages: [],
    detectedSignals: [],
    situationInfo: [],
    actionPlan: [],
    completedActions: [],
    startedAt: getCurrentTimestamp(),
  };
};

/**
 * 메시지 추가 헬퍼
 */
export const createMessage = (
  role: 'assistant' | 'user' | 'system',
  content: string,
  type: Message['type'] = 'text',
  choices?: any[]
): Message => {
  return {
    id: generateId(),
    role,
    type,
    content,
    choices,
    createdAt: getCurrentTimestamp(),
  };
};

/**
 * 상황 정보 추가 헬퍼
 */
export const createSituationInfo = (description: string, category?: string): SituationInfo => {
  return {
    id: generateId(),
    description,
    category,
  };
};

/**
 * 위험 신호 추가 헬퍼
 */
export const createRiskSignal = (signal: string, severity: 'low' | 'medium' | 'high', explanation?: string): RiskSignal => {
  return {
    id: generateId(),
    signal,
    severity,
    explanation,
  };
};
