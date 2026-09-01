export type Risk = 'NORMAL' | 'LOW' | 'HIGH';
export type CaseStatus = '확인중' | '해결 완료' | '후속조치';

export interface VerificationQuestion {
  id: number;
  question: string;
}

export interface CaseRecord {
  id: string;
  type: string;
  risk: Risk;
  status: CaseStatus;
  amount?: string;
  transferred: boolean;
  summary: string;
  createdAt: string;
  updatedAt: string;
}

export interface CaseDetail extends CaseRecord {
  victimStatus: string;
  aiInitialBrief: string;
  bankInfo: string;
  consumerInfo: string;
  verificationBrief: string;
  verificationQuestions: VerificationQuestion[];
}

export const CASE_DETAILS: Record<string, CaseDetail> = {
  'VP-099': {
    id: 'VP-099', type: 'UI 스크롤 테스트 사건', risk: 'HIGH', status: '확인중', transferred: false,
    summary: '긴 근거 목록과 조사 체크리스트의 독립 스크롤 동작을 확인하기 위한 테스트 Case입니다.', createdAt: '오늘 10:00', updatedAt: '10:05', victimStatus: '확인 중',
    aiInitialBrief: '수사기관 사칭과 긴급 송금 요구 정황을 기준으로 UI 스크롤 동작을 점검하는 테스트 Case입니다.', bankInfo: '담당자 ROOM의 근거 분석과 조사 체크리스트 UI 검증을 위한 Mock 데이터입니다.', consumerInfo: '실제 고객 정보가 아닌 UI 테스트용 Mock Case입니다.',
    verificationBrief: '스크롤 테스트용 Case의 최소 검증 정보입니다.',
    verificationQuestions: [
      { id: 1, question: '현재 송금 여부를 확인했습니까?' },
      { id: 2, question: '상대방이 주장한 기관을 별도로 확인했습니까?' },
      { id: 3, question: '개인정보 제공 범위를 확인했습니까?' },
    ],
  },
  'VP-014': {
    id: 'VP-014', type: '검찰 사칭', risk: 'HIGH', status: '확인중', amount: '5,000,000원', transferred: false,
    summary: '검찰을 사칭하며 안전계좌 명목의 송금을 요구했습니다.', createdAt: '오늘 09:34', updatedAt: '09:42', victimStatus: '송금 전',
    aiInitialBrief: '검찰을 사칭하며 안전계좌 명목으로 500만원 송금을 요구한 정황이 확인되었습니다.', bankInfo: '신규 수취인 거래와 긴급 송금 요구가 확인되어 담당자 확인이 필요합니다.', consumerInfo: '확인 전까지 송금하지 말고 공식 대표번호로 사실관계를 확인하세요.',
    verificationBrief: '검찰 사칭 정황, 안전계좌 명목 송금 요구, 피해자에게 특정 금액을 요구한 사실을 확인합니다.',
    verificationQuestions: [
      { id: 1, question: '현재 피해자에게 500만원을 요청한 사실이 있습니까?' },
      { id: 2, question: '검찰을 사칭한 사실이 있습니까?' },
      { id: 3, question: '안전계좌로 송금을 요구한 사실이 있습니까?' },
    ],
  },
  'VP-013': {
    id: 'VP-013', type: '은행 사칭', risk: 'LOW', status: '해결 완료', transferred: false,
    summary: '은행 직원을 사칭한 대출 안내 문자였습니다.', createdAt: '오늘 09:30', updatedAt: '09:34', victimStatus: '송금 전',
    aiInitialBrief: '은행 직원을 사칭한 대출 안내 문자로 확인되어 추가 송금 없이 종료된 Case입니다.', bankInfo: '이상 거래가 확인되지 않았고, 고객에게 공식 채널 확인을 안내했습니다.', consumerInfo: '대출 관련 연락은 은행 공식 앱과 대표번호를 통해 확인하세요.',
    verificationBrief: '은행 사칭 및 대출 안내 사실을 확인하고, 고객이 송금하지 않았는지 확인합니다.',
    verificationQuestions: [
      { id: 1, question: '은행 직원을 사칭한 사실이 있습니까?' },
      { id: 2, question: '대출을 이유로 개인정보를 요청한 사실이 있습니까?' },
      { id: 3, question: '송금 또는 수수료 납부를 요구한 사실이 있습니까?' },
    ],
  },
  'VP-012': {
    id: 'VP-012', type: '경찰 사칭', risk: 'NORMAL', status: '해결 완료', transferred: false,
    summary: '공식 대표번호를 통해 사실관계를 확인했습니다.', createdAt: '어제 21:32', updatedAt: '어제 21:45', victimStatus: '송금 전',
    aiInitialBrief: '경찰 사칭 가능성을 확인했지만 공식 대표번호 확인 후 정상 상담으로 종결되었습니다.', bankInfo: '거래 이상 징후는 확인되지 않았습니다.', consumerInfo: '의심되는 연락은 종료하고 직접 확인하는 절차를 이용하세요.',
    verificationBrief: '경찰 사칭 여부와 실제 송금 요구가 있었는지를 확인합니다.',
    verificationQuestions: [
      { id: 1, question: '경찰을 사칭한 사실이 있습니까?' },
      { id: 2, question: '사건 확인을 이유로 개인정보를 요청한 사실이 있습니까?' },
      { id: 3, question: '금전 또는 계좌 정보를 요구한 사실이 있습니까?' },
    ],
  },
};

export const MOCK_CASES: CaseRecord[] = Object.values(CASE_DETAILS).map(({ victimStatus: _victimStatus, aiInitialBrief: _brief, bankInfo: _bank, consumerInfo: _consumer, verificationBrief: _verification, verificationQuestions: _questions, ...record }) => record);
export const getCase = (id: string): CaseDetail => CASE_DETAILS[id] ?? CASE_DETAILS['VP-014'];
export const timeline = [['09:42', '고객이 “아직 송금하지 않았다”고 응답', 'customer'], ['09:40', 'Bank Agent가 FDS Alert 확인', 'bank'], ['09:38', 'Verification 요청 생성', 'verify'], ['09:34', 'AI 통화 텍스트 분석으로 Case 생성', 'system']] as const;
