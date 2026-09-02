import { ResponseGuide } from '../../types';
import { generateId } from '../../utils/helpers';

/**
 * Mock 상황별 대응 가이드 데이터
 */
export const MOCK_RESPONSE_GUIDES: ResponseGuide[] = [
  {
    id: generateId(),
    title: '검찰·경찰 사칭',
    description: '검찰, 경찰, 국세청 등 관공서를 사칭하는 피싱 사기',
    warningSigns: [
      '범죄 연루 혐의를 이유로 처벌을 협박',
      '신원 확인을 이유로 비밀번호 요청',
      '개인정보 보호를 이유로 다른 계좌로 송금',
      '긴급함을 강조',
      '전화번호 발신 조작',
    ],
    responseSteps: [
      {
        id: '1',
        order: 1,
        title: '전화 종료',
        description: '상대방이 누구든 즉시 전화를 끊으세요.',
      },
      {
        id: '2',
        order: 2,
        title: '공식 기관에 직접 확인',
        description: '경찰청(112), 검찰청 공식 번호로 직접 전화해서 본인이 검거 대상인지 확인하세요.',
      },
      {
        id: '3',
        order: 3,
        title: '신고',
        description: '경찰청(112)에 피싱 신고를 하고 상세 내용을 알려주세요.',
      },
      {
        id: '4',
        order: 4,
        title: '관련 기관 확인',
        description: '필요하면 국세청, 검찰청 등에 직접 문의해서 당신이 검거 대상이 아님을 확인받으세요.',
      },
    ],
    emergencyContacts: [
      { name: '경찰청', phone: '112', description: '피싱, 사기 신고' },
      { name: '금융감시원', phone: '1332', description: '금융사기 신고' },
      { name: '대검찰청', phone: '1301', description: '검찰청 공식 문의' },
    ],
    relatedGuides: [],
  },
  {
    id: generateId(),
    title: '금융기관 사칭',
    description: '은행, 증권사, 보험사 등 금융기관을 사칭하는 피싱 사기',
    warningSigns: [
      '계좌 이상 거래 또는 보안 문제 이유로 접근',
      '금리 인하 또는 대출 우대 조건 제시',
      '금융 상품 추천',
      '금전 거래 요구',
      '비밀번호나 인증번호 요청',
    ],
    responseSteps: [
      {
        id: '1',
        order: 1,
        title: '전화 종료',
        description: '상대방의 말을 끝까지 듣지 말고 즉시 전화를 끊으세요.',
      },
      {
        id: '2',
        order: 2,
        title: '은행 공식 번호로 확인',
        description: '은행 카드 뒷면에 적힌 번호 또는 인터넷으로 찾은 공식 번호로 전화하세요. 절대 상대방이 알려준 번호를 사용하지 마세요.',
      },
      {
        id: '3',
        order: 3,
        title: '계좌 상태 확인',
        description: '은행 앱이나 ATM에서 당신의 계좌 정보, 거래 내역을 직접 확인하세요.',
      },
      {
        id: '4',
        order: 4,
        title: '신고',
        description: '금융감시원(1332)에 신고하고 계좌 잠금을 요청하세요.',
      },
    ],
    emergencyContacts: [
      { name: '금융감시원', phone: '1332', description: '금융사기 신고' },
      { name: '경찰청', phone: '112', description: '금융사기 신고' },
    ],
    relatedGuides: [],
  },
  {
    id: generateId(),
    title: '가족·지인 사칭',
    description: '가족이나 친구를 사칭해서 돈을 요청하는 사기',
    warningSigns: [
      '평소와 다른 번호에서 전화',
      '급한 상황을 이유로 돈을 요청',
      '비밀로 해달라는 요청',
      '구체적이지 않은 상황 설명',
      '송금을 강요',
    ],
    responseSteps: [
      {
        id: '1',
        order: 1,
        title: '상대방 신원 확인',
        description: '상대가 정말 당신이 알고 있는 사람인지 평소와 다른 번호를 사용해서 직접 전화해 확인하세요.',
      },
      {
        id: '2',
        order: 2,
        title: '가족에게 알리기',
        description: '가족 구성원들에게 즉시 연락해서 본인도 비슷한 전화를 받았는지 확인하세요.',
      },
      {
        id: '3',
        order: 3,
        title: '송금 거절',
        description: '어떤 이유로든 송금하지 마세요. 대면을 요구하거나 직접 만나서 확인하세요.',
      },
      {
        id: '4',
        order: 4,
        title: '신고',
        description: '경찰청(112)에 신고하고 피싱 사기 신고 내용을 남기세요.',
      },
    ],
    emergencyContacts: [
      { name: '경찰청', phone: '112', description: '신분증사기, 사칭 신고' },
      { name: '금융감시원', phone: '1332', description: '금융사기 신고' },
    ],
    relatedGuides: [],
  },
  {
    id: generateId(),
    title: '대출·저금리 전환 사기',
    description: '저금리 대출 또는 금리 인하를 미끼로 하는 사기',
    warningSigns: [
      '시장 금리보다 훨씬 낮은 금리 제시',
      '선입금이나 수수료 요청',
      '신용등급 개선 약속',
      '대출 심사 과정이 매우 빠름',
      '개인정보 제공 요청',
    ],
    responseSteps: [
      {
        id: '1',
        order: 1,
        title: '제안 거절',
        description: '너무 좋은 조건의 제안은 대부분 사기입니다. 거절하세요.',
      },
      {
        id: '2',
        order: 2,
        title: '은행에 직접 문의',
        description: '당신이 거래하는 은행의 공식 번호로 전화해서 대출 상담을 받으세요.',
      },
      {
        id: '3',
        order: 3,
        title: '선입금 거절',
        description: '어떤 이유로든 선입금, 수수료 선불을 요청하면 사기입니다.',
      },
      {
        id: '4',
        order: 4,
        title: '신고',
        description: '금융감시원(1332)에 신고하세요.',
      },
    ],
    emergencyContacts: [
      { name: '금융감시원', phone: '1332', description: '불법 대출 신고' },
      { name: '경찰청', phone: '112', description: '사기 신고' },
    ],
    relatedGuides: [],
  },
  {
    id: generateId(),
    title: '문자 링크 클릭 주의',
    description: '낯선 발신처의 문자에 포함된 악성 링크',
    warningSigns: [
      '출처 불명의 문자',
      '배송 조회, 금융 거래 등을 명목으로 링크 제시',
      '짧은 URL 사용',
      '긴급함을 강조',
      '개인정보 입력 페이지',
    ],
    responseSteps: [
      {
        id: '1',
        order: 1,
        title: '링크 클릭 금지',
        description: '출처 불명의 문자에 포함된 링크는 절대 클릭하지 마세요.',
      },
      {
        id: '2',
        order: 2,
        title: '발신처 확인',
        description: '배송사나 금융기관이라면 공식 홈페이지나 앱을 직접 사용해서 조회하세요.',
      },
      {
        id: '3',
        order: 3,
        title: '휴대폰 보안 확인',
        description: '클릭했다면 휴대폰 보안 소프트웨어로 검사하고 설치된 앱을 확인하세요.',
      },
      {
        id: '4',
        order: 4,
        title: '신고',
        description: '경찰청(112)에 신고하세요.',
      },
    ],
    emergencyContacts: [
      { name: '경찰청', phone: '112', description: '사이버 사기 신고' },
      { name: '방송통신심의위원회', phone: '1580-0117', description: '불건전 광고 및 사칭 신고' },
    ],
    relatedGuides: [],
  },
  {
    id: generateId(),
    title: '악성 앱 설치 주의',
    description: '금융 거래용 앱 이름으로 위장한 악성 앱',
    warningSigns: [
      '정확한 은행명과 약간 다른 앱 이름',
      '공식 앱 스토어가 아닌 곳에서의 다운로드 요청',
      '높은 권한 요청 (카메라, 주소록, 위치정보 등)',
      '로그인 후 비밀번호 재입력 요청',
      '이상한 팝업 창',
    ],
    responseSteps: [
      {
        id: '1',
        order: 1,
        title: '공식 앱 스토어에서만 설치',
        description: 'Google Play Store, Apple App Store에서만 금융 앱을 설치하세요.',
      },
      {
        id: '2',
        order: 2,
        title: '앱 이름 정확히 확인',
        description: '은행 공식 홈페이지에서 정확한 앱 이름을 확인한 후 설치하세요.',
      },
      {
        id: '3',
        order: 3,
        title: '불필요한 권한 거절',
        description: '금융 앱이 카메라, 위치정보 등 불필요한 권한을 요청하면 거절하세요.',
      },
      {
        id: '4',
        order: 4,
        title: '의심 앱 삭제',
        description: '설치 후 이상한 징후가 보이면 즉시 삭제하고 계좌를 점검하세요.',
      },
    ],
    emergencyContacts: [
      { name: '경찰청', phone: '112', description: '악성 앱 신고' },
      { name: '금융감시원', phone: '1332', description: '금융 관련 앱 신고' },
    ],
    relatedGuides: [],
  },
];

/**
 * Mock 상황별 대응 조회
 */
export const getResponseGuides = (): ResponseGuide[] => {
  return MOCK_RESPONSE_GUIDES;
};

/**
 * Mock 상황별 대응 상세 조회
 */
export const getResponseGuide = (id: string): ResponseGuide | null => {
  return MOCK_RESPONSE_GUIDES.find(g => g.id === id) || null;
};
