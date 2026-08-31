export type Risk = 'NORMAL' | 'LOW' | 'HIGH';
export type CaseStatus = '확인중' | '해결 완료' | '후속조치';
export interface CaseRecord { id: string; type: string; risk: Risk; status: CaseStatus; amount?: string; transferred: boolean; summary: string; updatedAt: string; createdAt: string; }
export const MOCK_CASES: CaseRecord[] = [
  { id: 'VP-014', type: '검찰 사칭', risk: 'HIGH', status: '확인중', amount: '5,000,000원', transferred: false, summary: '검찰을 사칭하며 안전계좌 명목의 송금을 요구했습니다.', createdAt: '오늘 09:34', updatedAt: '09:42' },
  { id: 'VP-013', type: '은행 사칭', risk: 'LOW', status: '해결 완료', transferred: false, summary: '은행 직원을 사칭한 대출 안내 문자였습니다.', createdAt: '오늘 09:30', updatedAt: '09:34' },
  { id: 'VP-012', type: '경찰 사칭', risk: 'NORMAL', status: '해결 완료', transferred: false, summary: '공식 대표번호를 통해 사실관계를 확인했습니다.', createdAt: '어제 21:32', updatedAt: '어제 21:45' },
];
export const getCase = (id: string) => MOCK_CASES.find((item) => item.id === id) ?? MOCK_CASES[0];
export const timeline = [
  ['09:42', '고객이 “아직 송금하지 않았다”고 응답', 'customer'], ['09:40', 'Bank Agent가 FDS Alert 확인', 'bank'], ['09:38', 'Verification 요청 생성', 'verify'], ['09:34', 'AI 통화 텍스트 분석으로 Case 생성', 'system'],
] as const;
