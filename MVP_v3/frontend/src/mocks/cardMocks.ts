export const mockBankTransaction = {
  transferAmount: 3000000,
  transferDateTime: '2026.09.10 16:11:24',
  transactionStatus: '이체 완료',
  updatedAt: '16:13',
  withdrawalAccount: { bankName: '국민은행', accountNumber: '123-456-7890', holder: '이○○' },
  receivingAccount: { bankName: 'OO은행', accountNumber: '987-654-3210', holder: '홍○○' },
  transactionMethod: '모바일뱅킹',
};

export const mockFdsResult = {
  riskScore: 87,
  riskLevel: 'HIGH',
  updatedAt: '16:13',
  reasons: ['신규 수취계좌', '단시간 고액 이체', '유사 사기계좌와 패턴 유사'],
  reportCount: 3,
  suspiciousAccountStatus: '의심',
  holdPossibleStatus: '가능',
};

export const mockAdditionalLookup = {
  updatedAt: '16:13',
  description: '해당 수취계좌의 최근 거래 내역이 확인되었습니다.',
  transactions: [
    { datetime: '2026.09.10 16:11', amount: 3000000, type: '이체' },
    { datetime: '2026.09.10 15:02', amount: 1000000, type: '이체' },
    { datetime: '2026.09.10 14:21', amount: 500000, type: '이체' },
  ],
};
