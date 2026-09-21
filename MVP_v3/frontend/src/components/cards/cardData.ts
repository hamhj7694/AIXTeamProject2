import type { CaseBundle, CaseSupportSnapshot, StoredCase, CaseTransaction } from '../../api/types';
import type { TransactionItem } from './AdditionalLookupCard';

export const MOCK_ACCOUNT_DATA = {
  withdrawalAccount: { bankName: '국민은행', accountNumber: '123-456-7890', holder: '김민수' },
  receivingAccount: { bankName: '우리은행', accountNumber: '987-654-3210', holder: '박지훈' },
};

export const MOCK_ADDITIONAL_TRANSACTIONS = [
  { datetime: '정보 없음', amount: 0, description: '' },
];

const MOCK_FDS_ACCOUNT_INFO = {
  reportCount: 3,
  suspiciousAccountStatus: '의심',
  holdPossibleStatus: '가능',
};

export function toBankCardData(caseItem: StoredCase, support: CaseSupportSnapshot | null, _bundle: CaseBundle, selectedTransaction: TransactionItem | null = null, apiTransactions: CaseTransaction[] = [], fdsUpdatedAt?: string) {
  const status = caseItem.victim_transfer_status === 'YES' ? '이체 완료' : caseItem.victim_transfer_status === 'NO' ? '미이체' : '정보 없음';
  const transaction = selectedTransaction ? {
    transferAmount: selectedTransaction.amount,
    transferDateTime: selectedTransaction.datetime,
    transactionMethod: selectedTransaction.description || '정보 없음',
  } : {
    transferAmount: typeof caseItem.actual_loss_amount_krw === 'number' ? caseItem.actual_loss_amount_krw : null,
    transferDateTime: '정보 없음',
    transactionMethod: '모바일뱅킹',
  };
  const brief = support?.case_brief;
  const reasons = support?.case_context?.key_signals?.filter((item) => item.trim()) ?? [];
  return {
    transaction: {
      ...transaction,
      transactionStatus: status,
      updatedAt: fdsUpdatedAt || caseItem.updated_at || '',
      ...MOCK_ACCOUNT_DATA,
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
      transactions: (apiTransactions.length ? apiTransactions.map((item) => ({ datetime: item.transaction_at, amount: item.amount, description: item.memo || '-', })) : MOCK_ADDITIONAL_TRANSACTIONS).map((transaction) => ({
        ...transaction,
        description: transaction.description?.trim() || '-',
      })),
    },
  };
}
