import type { WorkCardDescriptor, WorkCardType } from './types';

export interface WorkCardCatalogItem {
  id: WorkCardType;
  label: string;
  purpose: string;
  result: string;
  externalEffect: boolean;
}

export const BANK_WORK_CARD_CATALOG: WorkCardCatalogItem[] = [
  { id: 'FACT_REVIEW', label: '미확인 정보', purpose: 'CaseFact 후보와 미확인 값을 검토합니다.', result: '확정 Fact 또는 후속 질문', externalEffect: false },
  { id: 'QUESTION_PLAN', label: '질문 추천 받기', purpose: '이미 확인된 항목을 제외하고 고객 질문을 구성합니다.', result: '고객 질문 대기열', externalEffect: true },
  { id: 'VERIFICATION_REQUEST', label: '기관 확인 요청', purpose: '공식 채널로 확인할 검증 업무를 등록합니다.', result: '기관 검증 Task', externalEffect: false },
  { id: 'BANK_ACTION', label: '보호조치 등록', purpose: '은행 직원이 수행할 보호조치 검토 업무를 등록합니다.', result: 'BankAction 요청', externalEffect: false },
  { id: 'CUSTOMER_NOTICE', label: '고객 안내 작성', purpose: '고객에게 공개할 안전 안내를 검토 후 전송합니다.', result: '고객 채널 메시지', externalEffect: true },
  { id: 'CASE_TRANSITION', label: '상태 변경', purpose: 'Case의 현재 업무 단계를 명시적으로 변경합니다.', result: 'Case 상태·Timeline 갱신', externalEffect: false },
];

export const getBankWorkCardActions = () => BANK_WORK_CARD_CATALOG.map(({ id, label }) => ({ id, label }));

export const createDraftWorkCard = (cardType: WorkCardType): WorkCardDescriptor => {
  const item = BANK_WORK_CARD_CATALOG.find(({ id }) => id === cardType);
  return {
    card_id: crypto.randomUUID(),
    card_type: cardType,
    stage: 'DRAFT',
    title: item?.label ?? cardType,
    payload: {},
    source: 'USER_ACTION',
    created_at: new Date().toISOString(),
  };
};
