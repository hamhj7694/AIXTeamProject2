// 유틸리티 함수

/**
 * 고유 ID 생성
 */
export const generateId = (): string => {
  return `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

/**
 * 현재 타임스탬프 반환
 */
export const getCurrentTimestamp = (): number => {
  return Date.now();
};

/**
 * 날짜를 읽기 쉬운 형식으로 변환
 */
export const formatDate = (timestamp: number): string => {
  const date = new Date(timestamp);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  
  return `${year}년 ${month}월 ${day}일 ${hours}:${minutes}`;
};

/**
 * 상담 진행도 계산 (0-100)
 */
export const calculateProgressPercentage = (currentStep: string, totalSteps: number): number => {
  const stepIndex = {
    situation_check: 0,
    risk_signal_check: 1,
    persuasion: 2,
    immediate_action: 3,
    action_confirmation: 4,
    next_action: 5,
    result: 6,
  }[currentStep] || 0;
  
  return Math.round((stepIndex / totalSteps) * 100);
};

/**
 * 상담 위험도 계산
 */
export const calculateRiskLevel = (signals: number): 'low' | 'medium' | 'high' => {
  if (signals >= 5) return 'high';
  if (signals >= 3) return 'medium';
  return 'low';
};

/**
 * 텍스트 길이에 따라 줄 수 예상
 */
export const estimateLineCount = (text: string, maxCharsPerLine: number = 50): number => {
  return Math.ceil(text.length / maxCharsPerLine);
};

/**
 * 메시지 배열에서 마지막 AI 메시지 찾기
 */
export const getLastAssistantMessage = (messages: any[]): any | null => {
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role === 'assistant') {
      return messages[i];
    }
  }
  return null;
};

/**
 * 메시지 요약 생성
 */
export const summarizeMessages = (messages: any[]): string[] => {
  const summary: string[] = [];
  messages.forEach((msg) => {
    if (msg.role === 'user' && msg.content) {
      summary.push(msg.content);
    }
  });
  return summary;
};

/**
 * 클래스명 조합 (tailwind 유틸)
 */
export const cn = (...classes: (string | undefined | null | false)[]): string => {
  return classes
    .filter(Boolean)
    .join(' ')
    .trim();
};

/**
 * 딜레이 함수
 */
export const delay = (ms: number): Promise<void> => {
  return new Promise(resolve => setTimeout(resolve, ms));
};
