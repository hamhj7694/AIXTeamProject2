import {
  ManagerRoomCase,
  ManagerRoomCustomerMessage,
  ManagerRoomFdsMock,
  ManagerRoomProgressMock,
  ManagerRoomSttMock,
  ManagerRoomWorkspaceMock,
} from '../types';

// URL의 caseId만 실제 화면 흐름에서 받고, 나머지는 API 교체 전까지 사용할 가상 정보다.
export const createManagerRoomCaseMock = (
  caseId: string
): ManagerRoomCase => ({
  caseId,
  title: '보이스피싱 의심 사건',
  risk: 'HIGH',
  status: '확인 중',
  dataSource: 'MVP Mock',
});

export const managerRoomWorkspaceMock: ManagerRoomWorkspaceMock = {
  brief:
    '검찰 수사를 사칭한 상대방이 고객에게 자금 검증을 이유로 송금을 요구한 것으로 보입니다. 통화 내용에서 기관 사칭과 긴급 송금 요구가 확인되며, 실제 수취인과 고객의 관계는 아직 확인되지 않았습니다.',
  riskEvidence: [
    '수사기관을 사칭한 발화가 존재함',
    '자금 검증을 이유로 송금을 요구함',
    '즉시 행동을 요구하는 긴급성 표현이 확인됨',
  ],
  counterEvidence: [
    '고객이 아직 실제 송금을 완료하지 않음',
    '고객이 일부 상황에 의문을 표현함',
  ],
  unknowns: [
    '수취인과 고객의 실제 관계',
    '송금 목적에 대한 고객 본인의 설명',
    '상대방이 안내한 기관·연락처의 진위',
  ],
  recommendedQuestion:
    '이번 송금의 수취인은 고객님이 기존에 알고 있던 사람인가요?',
  initialMessages: [
    {
      id: 'workspace-message-1',
      role: 'assistant',
      content:
        '현재 사건에서 가장 먼저 확인할 항목은 고객과 수취인의 관계입니다.',
    },
    {
      id: 'workspace-message-2',
      role: 'manager',
      content: '송금 목적에서 추가로 확인할 내용을 정리해줘.',
    },
    {
      id: 'workspace-message-3',
      role: 'assistant',
      content:
        '송금 목적이 고객 본인의 기존 거래인지, 상대방의 지시에 의해 새롭게 발생한 거래인지 확인하는 것이 좋습니다.',
    },
  ],
};

export const managerRoomCustomerMessagesMock: ManagerRoomCustomerMessage[] = [
  {
    id: 'customer-consultation-message-1',
    role: 'manager',
    content: '고객님, 현재 송금 목적과 수취인 관계를 확인하고 있습니다.',
  },
  {
    id: 'customer-consultation-message-2',
    role: 'customer',
    content:
      '수사기관에서 자금 확인이 필요하다고 해서 안내받은 계좌로 송금하려고 했습니다.',
  },
];

// 실제 LLM 호출 없이 담당자의 요청 키워드에 맞는 조사 보조 문구만 반환한다.
export const createManagerRoomMockResponse = (request: string): string => {
  const normalizedRequest = request.toLowerCase();

  if (
    normalizedRequest.includes('위험') ||
    normalizedRequest.includes('근거')
  ) {
    return '현재 Mock 근거에서는 기관 사칭, 자금 검증 명목의 송금 요구, 긴급성 표현을 우선 확인할 수 있습니다. 최종 판단 전 근거 확인 화면에서 자료를 확인해 주세요.';
  }

  if (normalizedRequest.includes('질문')) {
    return '고객에게 수취인을 기존에 알고 있었는지, 송금 요구를 누구에게 어떤 이유로 받았는지 차례로 확인해 보세요.';
  }

  if (
    normalizedRequest.includes('확인') ||
    normalizedRequest.includes('미확인')
  ) {
    return '수취인과 고객의 관계, 고객이 이해한 송금 목적, 상대방이 제시한 기관과 연락처의 진위를 추가로 확인하는 것이 좋습니다.';
  }

  return '현재 사건 Brief와 Mock 근거를 기준으로 조사 항목을 정리했습니다. 근거 자료와 고객 설명을 함께 확인한 뒤 담당자가 최종 판단해 주세요.';
};

export const managerRoomFdsMock: ManagerRoomFdsMock = {
  signalStatus: '고위험 거래 신호 확인',
  managerStatus: '담당자 추가 확인 필요',
  summary:
    '현재 Case 생성의 기반이 된 MVP Mock FDS 위험 신호입니다. 이 신호는 추가 검토가 필요하다는 의미이며 최종 판단 결과가 아닙니다.',
  unavailableDetails: [
    '계좌번호',
    '금융기관명',
    '거래 금액',
    '거래 시각',
    'FDS 점수 및 임계값',
    '과거 거래 이력',
  ],
  confirmationPoints: [
    'FDS 신호는 담당자 검토가 필요한 상황을 알립니다.',
    '이 신호만으로 보이스피싱 여부를 최종 판단하지 않습니다.',
  ],
};

export const managerRoomSttMock: ManagerRoomSttMock = {
  sourceLabel: 'MVP Mock 발췌',
  notice:
    '실제 녹취 원문이 아닌 현재 사건 맥락을 바탕으로 구성한 Mock STT 예시입니다.',
  excerpts: [
    {
      id: 'stt-mock-excerpt-1',
      speaker: '상대방',
      content:
        '수사기관 관계자라고 주장하며 자금 검증이 필요하다고 설명했습니다.',
    },
    {
      id: 'stt-mock-excerpt-2',
      speaker: '상대방',
      content:
        '검증을 위해 송금이 필요하며 즉시 진행해야 한다고 요구했습니다.',
    },
  ],
  confirmationPoints: [
    '수사기관 사칭 정황',
    '자금 검증 명목의 송금 요구',
    '긴급한 행동 요구',
    '수취인과 고객의 관계는 확인되지 않음',
  ],
};

export const managerRoomProgressMock: ManagerRoomProgressMock = {
  currentStage: '담당자 조사 진행 중',
  currentFocus: '고객과 수취인의 관계 및 송금 목적',
  nextStage: '고객 확인 → 응답 반영 → 담당자 최종 판단',
  events: [
    {
      id: 'progress-event-1',
      phase: 'past',
      title: 'FDS 고위험 거래 신호 확인',
      description:
        'MVP Mock FDS 신호를 기준으로 담당자 확인이 필요한 Case 흐름이 시작됐습니다.',
      label: '사전 탐지',
      isKey: true,
    },
    {
      id: 'progress-event-2',
      phase: 'past',
      title: 'Case 생성',
      description:
        '탐지 신호와 기본 사건 정보를 묶은 담당자 확인용 Mock Case가 생성됐습니다.',
      label: 'Case 접수',
      isKey: true,
    },
    {
      id: 'progress-event-3',
      phase: 'past',
      title: '통화·STT 근거 연결',
      description:
        '담당자가 이후 근거 확인 화면에서 확인할 수 있도록 Mock 통화·STT 자료가 연결된 상태입니다.',
      label: '근거 준비',
      isKey: true,
    },
    {
      id: 'progress-event-4',
      phase: 'past',
      title: '담당자 ROOM 진입',
      description:
        '담당자가 Case의 Brief와 조사 보조 정보를 확인하기 위해 담당자 ROOM에 진입했습니다.',
      label: '조사 시작',
      isKey: false,
    },
    {
      id: 'progress-event-5',
      phase: 'current',
      title: '담당자 사건 Brief 확인',
      description:
        '현재 Mock Brief를 바탕으로 사건 맥락과 확인이 필요한 항목을 정리하고 있습니다.',
      label: '현재',
      isKey: true,
    },
    {
      id: 'progress-event-6',
      phase: 'current',
      title: '고객 송금 목적 및 수취인 관계 조사 중',
      description:
        '송금 목적이 고객의 기존 거래인지와 수취인을 실제로 알고 있는지를 담당자가 확인하는 단계입니다.',
      label: '현재',
      isKey: true,
    },
    {
      id: 'progress-event-7',
      phase: 'next',
      title: '고객에게 필요한 사실 확인',
      description:
        '담당자가 확인 질문을 검토한 뒤 고객 상담에서 필요한 사실을 직접 확인합니다.',
      label: '예정',
      isKey: true,
    },
    {
      id: 'progress-event-8',
      phase: 'next',
      title: '고객 응답 확인',
      description:
        '고객의 설명을 근거 자료와 함께 검토해 사건 정보에 반영할 내용을 확인합니다.',
      label: '예정',
      isKey: true,
    },
    {
      id: 'progress-event-9',
      phase: 'next',
      title: '사건 정보 업데이트',
      description:
        '확인된 사실을 기준으로 담당자가 현재 Case의 조사 내용을 정리합니다.',
      label: '예정',
      isKey: false,
    },
    {
      id: 'progress-event-10',
      phase: 'next',
      title: '담당자 최종 판단 및 사건 종료',
      description:
        '근거 자료와 고객 확인 결과를 종합해 담당자가 최종 판단하고 종료 결과를 기록합니다.',
      label: '예정',
      isKey: true,
    },
  ],
  checklist: [
    {
      id: 'check-customer-identity',
      label: '고객 본인 확인',
      completed: true,
    },
    {
      id: 'check-transfer-purpose',
      label: '송금 목적 확인',
      completed: false,
    },
    {
      id: 'check-recipient-relationship',
      label: '수취인과 고객의 관계 확인',
      completed: false,
    },
  ],
};
