import type { CaseBundle, CaseSupportSnapshot, StoredCase } from '../../api/types';

export const MOCK_ACCOUNT_DATA = {
  withdrawalAccount: { bankName: '국민은행', accountNumber: '123-456-7890', holder: '김민수' },
  receivingAccount: { bankName: '우리은행', accountNumber: '987-654-3210', holder: '박지훈' },
};

export const MOCK_ADDITIONAL_TRANSACTIONS = [
  { datetime: '정보 없음', amount: 0, type: '현재 데이터 없음' },
];

const MOCK_FDS_ACCOUNT_INFO = {
  reportCount: 3,
  suspiciousAccountStatus: '의심',
  holdPossibleStatus: '가능',
};

export function toBankCardData(caseItem: StoredCase, support: CaseSupportSnapshot | null, _bundle: CaseBundle) {
  const status = caseItem.victim_transfer_status === 'YES' ? '이체 완료' : caseItem.victim_transfer_status === 'NO' ? '미이체' : '정보 없음';
  const brief = support?.case_brief;
  const reasons = support?.case_context?.key_signals?.filter((item) => item.trim()) ?? [];
  return {
    transaction: {
      transferAmount: typeof caseItem.actual_loss_amount_krw === 'number' ? caseItem.actual_loss_amount_krw : null,
      transactionStatus: status,
      transferDateTime: '정보 없음',
      updatedAt: caseItem.updated_at || '',
      ...MOCK_ACCOUNT_DATA,
      transactionMethod: '모바일뱅킹',
    },
    risk: {
      riskScore: typeof brief?.risk_score === 'number' ? brief.risk_score : null,
      riskLevel: brief?.risk_level || '정보 없음',
      updatedAt: caseItem.updated_at || '',
      reasons,
      ...MOCK_FDS_ACCOUNT_INFO,
    },
    additionalLookup: {
      updatedAt: caseItem.updated_at || '',
      transactions: MOCK_ADDITIONAL_TRANSACTIONS,
    },
  };
}
