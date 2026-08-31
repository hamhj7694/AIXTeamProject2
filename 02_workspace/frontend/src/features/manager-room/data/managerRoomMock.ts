import {
  ManagerRoomCase,
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

// 실제 LLM 호출 없이 담당자의 요청 키워드에 맞는 조사 보조 문구만 반환한다.
export const createManagerRoomMockResponse = (request: string): string => {
  const normalizedRequest = request.toLowerCase();

  if (
    normalizedRequest.includes('위험') ||
    normalizedRequest.includes('근거')
  ) {
    return '현재 Mock 근거에서는 기관 사칭, 자금 검증 명목의 송금 요구, 긴급성 표현을 우선 확인할 수 있습니다. 최종 판단 전 원본 Evidence를 확인해 주세요.';
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

  return '현재 사건 Brief와 Mock 근거를 기준으로 조사 항목을 정리했습니다. 원본 Evidence와 고객 설명을 함께 확인한 뒤 담당자가 최종 판단해 주세요.';
};
