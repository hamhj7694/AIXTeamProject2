/**
 * 상담 심리 상태 추정 및 동적 응답 로직
 * STOP → CHECK → ACT 프레임워크 기반
 */

export type UserPsychologyState = 'S0' | 'S1' | 'S3' | 'S4' | 'S4_ACTION' | 'S5';

export interface ConsultationContext {
  messageCount: number;
  hasCallerInfo: boolean;
  hasReasonInfo: boolean;
  hasRequestInfo: boolean;
  hasTimelineInfo: boolean;
  hasActionInfo: boolean;
  detectedRiskCount: number;
  userResponses: string[];
}

/**
 * 사용자의 심리 상태 추정
 * S0: 의심 → S1: 불안 → S3: 존중 → S4: 잠식 → S5: 피해
 */
export const estimateUserState = (context: ConsultationContext): UserPsychologyState => {
  const { messageCount, detectedRiskCount, userResponses } = context;

  // S5: 피해 발생 상태
  if (userResponses.some(r => r.includes('돈이') || r.includes('송금') || r.includes('공개'))) {
    return 'S5';
  }

  // S4_ACTION: 행동 직전 (긴급 중단 필요)
  if (context.hasActionInfo && detectedRiskCount >= 3) {
    return 'S4_ACTION';
  }

  // S4: 잠식 상태 (공감과 질문, 행동 지연)
  if (messageCount >= 5 && detectedRiskCount >= 2) {
    return 'S4';
  }

  // S3: 정보 수집 진행 중 (존중 + 검증)
  if (context.hasReasonInfo && context.hasRequestInfo) {
    return 'S3';
  }

  // S1: 불안 상태 (초기 안정 필요)
  if (messageCount >= 2) {
    return 'S1';
  }

  // S0: 의심 상태 (정보 중심)
  return 'S0';
};

/**
 * 심리 상태별 AI 톤 설정
 */
export const getToneByState = (state: UserPsychologyState) => {
  const tones = {
    S0: {
      name: '정보 중심',
      approach: 'calm_informative',
      emoji: '📋',
      description: 'Provide clear information without alarming',
    },
    S1: {
      name: '안정 중심',
      approach: 'reassuring',
      emoji: '🤝',
      description: 'Focus on reassurance and support',
    },
    S3: {
      name: '존중 + 검증',
      approach: 'respectful_verification',
      emoji: '✓',
      description: 'Validate and cross-check information',
    },
    S4: {
      name: '공감 + 질문 + 지연',
      approach: 'empathetic_questioning',
      emoji: '💬',
      description: 'Show empathy, ask questions, delay actions',
    },
    S4_ACTION: {
      name: '긴급 중단',
      approach: 'urgent_clear',
      emoji: '⛔',
      description: 'Clear, brief, action-stopping message',
    },
    S5: {
      name: '조치 중심',
      approach: 'action_oriented',
      emoji: '🚨',
      description: 'No blame, focus on immediate actions',
    },
  };

  return tones[state];
};

/**
 * 상담 단계 정의 (7가지 핵심 질문)
 */
export type ConsultationStage = 
  | 'initial_contact' // 초기: 누가 연락했나?
  | 'reason_check'    // 왜 연락했나?
  | 'request_check'   // 무엇을 요구했나?
  | 'timeline_check'  // 언제까지 해야 하나?
  | 'statement_check' // 상대방이 어떤 말을 했나?
  | 'action_check'    // 실제 행동을 했나?
  | 'current_status'  // 현재 어떤 상태인가?
  | 'briefing'        // 상황 정리
  | 'intervention'    // 행동 개입
  | 'action_plan';    // 조치 안내

/**
 * 각 단계별 질문 템플릿
 */
export const STAGE_QUESTIONS = {
  initial_contact: {
    question: '지금 누가 연락을 드렸어요?',
    options: [
      { label: '은행 직원이라고 했어요', value: 'bank' },
      { label: '경찰/검찰이라고 했어요', value: 'prosecutor' },
      { label: '택배사/통신사라고 했어요', value: 'delivery' },
      { label: '잘 모르겠어요', value: 'unknown' },
    ],
  },
  reason_check: {
    question: '그 사람이 무엇 때문에 연락했다고 했어요?',
    options: [
      { label: '계좌/금전 관련', value: 'money' },
      { label: '범죄 혐의', value: 'crime' },
      { label: '물품 배송/서비스', value: 'service' },
      { label: '명확하지 않았어요', value: 'unclear' },
    ],
  },
  request_check: {
    question: '구체적으로 뭘 요구했어요?',
    options: [
      { label: '돈을 보내라고 했어요', value: 'money_transfer' },
      { label: '개인정보를 알려달라고 했어요', value: 'personal_info' },
      { label: '앱을 설치하라고 했어요', value: 'app_install' },
      { label: '다른 것을 요구했어요', value: 'other' },
    ],
  },
  timeline_check: {
    question: '언제까지 해야 한다고 했어요?',
    options: [
      { label: '지금 바로, 오늘 중에', value: 'urgent' },
      { label: '빨리, 내일까지', value: 'soon' },
      { label: '시간 제한이 없었어요', value: 'no_rush' },
    ],
  },
  statement_check: {
    question: '상대방이 어떤 말을 가장 강하게 했어요?',
    description: '가장 기억에 남는 말이 뭐였어요?',
  },
  action_check: {
    question: '지금까지 실제로 뭘 했어요?',
    options: [
      { label: '아무것도 안 했어요', value: 'nothing' },
      { label: '일부만 했어요', value: 'partial' },
      { label: '다 했어요', value: 'all' },
    ],
  },
  current_status: {
    question: '지금 당신은 어떤 상태에요?',
    options: [
      { label: '진짜인지 의심돼요', value: 'suspicious' },
      { label: '불안하고 답답해요', value: 'anxious' },
      { label: '벌써 돈을 보냈어요', value: 'already_acted' },
      { label: '뭐 해야 할지 모르겠어요', value: 'confused' },
    ],
  },
};

/**
 * 대화 맥락 기반 위험 신호 추가 (점진적)
 */
export const shouldRevealRiskSignal = (
  state: UserPsychologyState,
  messageCount: number,
  contextCompleteness: number // 0-1: 정보 수집 정도
): boolean => {
  // S0(의심): 정보만 제공, 위험신호 숨김
  if (state === 'S0') return false;

  // S1(불안): 충분한 정보 후 신호 시작
  if (state === 'S1') return messageCount >= 4 && contextCompleteness >= 0.6;

  // S3(존중): 충분한 검증 후 신호
  if (state === 'S3') return contextCompleteness >= 0.7;

  // S4(잠식): 신호 + 공감
  if (state === 'S4') return true;

  // S4_ACTION(행동직전): 즉시 명확한 신호
  if (state === 'S4_ACTION') return true;

  // S5(피해): 신호 없이 조치 중심
  return false;
};

/**
 * 상담 단계별 응답 생성
 */
export const generateConsultationResponse = (
  stage: ConsultationStage,
  userInput: string,
  userState: UserPsychologyState,
  messageCount: number
) => {
  const tone = getToneByState(userState);

  // 각 단계별 맞춤 응답
  const responses: Record<ConsultationStage, Record<UserPsychologyState, string>> = {
    initial_contact: {
      S0: `${userInput}은 알겠어요.`,
      S1: `그렇군요. 천천히 상황을 정리해보겠습니다.`,
      S3: `${userInput}이 연락했군요.`,
      S4: `불안하실 거 같아요. 함께 확인해보겠습니다.`,
      S4_ACTION: `바로 중단하세요.`,
      S5: `조치에 집중하겠습니다.`,
    },
    reason_check: {
      S0: `그렇군요.`,
      S1: `이해합니다.`,
      S3: `확인했습니다.`,
      S4: `계속 이야기해주세요.`,
      S4_ACTION: `멈추세요.`,
      S5: `조치하겠습니다.`,
    },
    request_check: {
      S0: `그렇군요.`,
      S1: `알겠습니다.`,
      S3: `확인했습니다.`,
      S4: `이해합니다.`,
      S4_ACTION: `절대 하지 마세요.`,
      S5: `조치하겠습니다.`,
    },
    timeline_check: {
      S0: `시간 제한이 있었군요.`,
      S1: `알겠습니다.`,
      S3: `확인했습니다.`,
      S4: `이해합니다.`,
      S4_ACTION: `서두르면 안 됩니다.`,
      S5: `조치하겠습니다.`,
    },
    statement_check: {
      S0: `그렇군요.`,
      S1: `알겠습니다.`,
      S3: `확인했습니다.`,
      S4: `이해합니다.`,
      S4_ACTION: `멈추세요.`,
      S5: `조치하겠습니다.`,
    },
    action_check: {
      S0: `그렇군요.`,
      S1: `알겠습니다.`,
      S3: `확인했습니다.`,
      S4: `이해합니다.`,
      S4_ACTION: `멈추세요.`,
      S5: `지금부터 조치하겠습니다.`,
    },
    current_status: {
      S0: `그렇군요.`,
      S1: `알겠습니다.`,
      S3: `확인했습니다.`,
      S4: `이해합니다.`,
      S4_ACTION: `지금 멈춰야 합니다.`,
      S5: `이제 조치가 필요합니다.`,
    },
    briefing: {
      S0: `정리하면:`,
      S1: `다시 정리해보니:`,
      S3: `이제 확인된 것:`,
      S4: `여기까지의 상황:`,
      S4_ACTION: `위험합니다:`,
      S5: `해야 할 일:`,
    },
    intervention: {
      S0: `조치:`,
      S1: `이런 경우:`,
      S3: `권장하는 방법:`,
      S4: `함께 하시죠:`,
      S4_ACTION: `지금 멈추세요:`,
      S5: `지금 하실 일:`,
    },
    action_plan: {
      S0: `다음 단계:`,
      S1: `안내:`,
      S3: `확인 방법:`,
      S4: `함께 진행:`,
      S4_ACTION: `긴급:`,
      S5: `조치 순서:`,
    },
  };

  return responses[stage]?.[userState] || '상황을 정리해보겠습니다.';
};
