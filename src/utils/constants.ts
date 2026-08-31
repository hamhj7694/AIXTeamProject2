// UI 텍스트 상수
export const UI_TEXT = {
  HEADER_TITLE: '안전 상담',
  PROGRESS_STEP_1: '상황 확인',
  PROGRESS_STEP_2: '위험 확인',
  PROGRESS_STEP_3: '조치 안내',
  PROGRESS_STEP_4: '완료',
  
  INITIAL_MESSAGE: '잠시만요.\n지금 어떤 상황인지 제가 하나씩 같이 확인해드릴게요.\n혼자 판단하지 않으셔도 괜찮아요.',
  INITIAL_QUESTION: '지금 어떤 상황인가요?',
  
  SITUATION_CARD_TITLE: '현재 상황',
  RISK_SIGNAL_CARD_TITLE: '확인된 위험 신호',
  BRIEFING_CARD_TITLE: '지금까지 확인한 내용',
  ACTION_CARD_TITLE: '지금 해야 할 행동',
  
  EDIT_BUTTON: '내용 수정',
  CONTINUE_BUTTON: '계속 확인하기',
  COMPLETE_BUTTON: '완료',
  
  ACTION_INTERVENTION_TITLE: '잠시만요.',
  ACTION_INTERVENTION_SUBTITLE: '지금은 송금을 잠시 멈춰주세요.',
  ACTION_INTERVENTION_DESC: '지금까지 확인한 상황을 먼저 확인한 뒤\n안전한 방법으로 처리하는 것이 좋습니다.',
  ACTION_STOP_BUTTON: '송금 잠시 멈추기',
  
  ALREADY_DAMAGED_MSG: '괜찮아요.\n지금부터 추가 피해를 막기 위한 조치를 안내해드릴게요.',
  
  PLACEHOLDER_INPUT: '내용을 입력해주세요',
  
  HISTORY_TITLE: '상담 기록',
  SAFETY_GUIDE_TITLE: '안전 안내',
  RESPONSE_GUIDE_TITLE: '상황별 대응',
};

// 상담 단계별 텍스트
export const STEP_TEXT = {
  situation_check: '상황 확인',
  risk_signal_check: '위험 확인',
  persuasion: '확인 및 설득',
  immediate_action: '긴급 행동',
  action_confirmation: '행동 완료 확인',
  next_action: '다음 행동',
  result: '상담 결과',
};

// 초기 선택지
export const INITIAL_CHOICES = [
  {
    id: 'call-received',
    label: '전화가 왔어요',
    value: 'call_received',
  },
  {
    id: 'message-received',
    label: '문자를 받았어요',
    value: 'message_received',
  },
  {
    id: 'money-request',
    label: '송금을 요구받았어요',
    value: 'money_requested',
  },
  {
    id: 'info-request',
    label: '개인정보를 요구받았어요',
    value: 'info_requested',
  },
  {
    id: 'app-install',
    label: '앱을 설치했어요',
    value: 'app_installed',
  },
  {
    id: 'not-sure',
    label: '잘 모르겠어요',
    value: 'not_sure',
  },
];

// 색상 및 스타일
export const COLORS = {
  PRIMARY: '#0284c7',
  PRIMARY_DARK: '#075985',
  DANGER: '#dc2626',
  WARNING: '#d97706',
  SUCCESS: '#16a34a',
  GRAY_100: '#f3f4f6',
  GRAY_200: '#e5e7eb',
  GRAY_300: '#d1d5db',
  GRAY_600: '#4b5563',
  GRAY_900: '#111827',
};

// 진행 상태
export const PROGRESS_STAGES = [
  { id: 1, label: '상황 확인', step: 'situation_check' },
  { id: 2, label: '위험 확인', step: 'risk_signal_check' },
  { id: 3, label: '조치 안내', step: 'immediate_action' },
  { id: 4, label: '완료', step: 'result' },
];
