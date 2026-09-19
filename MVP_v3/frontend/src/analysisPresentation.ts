/**
 * Presentation-only labels for Analysis Envelope identifiers.
 *
 * Raw identifiers stay untouched in API payloads and persisted Case data. Only
 * the final staff-facing view calls these helpers.
 */
const labels: Record<string, string> = {
  SUSPECTED_PARTY: '보이스피싱 의심 인물', CALLER: '보이스피싱 의심 인물',
  CUSTOMER: '고객', BANK_STAFF: '은행 담당자', SYSTEM: '분석 시스템', UNKNOWN: '확인 필요',

  IMPERSONATION: '기관·신분 사칭', PSY_STRATEGY: '심리적 압박', ACTION_REQUEST: '행동 요청',
  MONEY_MOVEMENT: '금전 이동 요구', AMOUNT: '금액 정보',
  AUTH_INFO: '인증정보', SENSITIVE_INFO: '민감정보', DEVICE_CONTROL: '기기 제어',
  CONTACT_RESTRICTION: '외부 연락 제한', CARD_HANDOVER: '카드 전달', ACCOUNT_RENTAL: '계좌 대여',
  IDENTITY_CLAIM: '신분 주장', ORGANIZATION_CLAIM: '기관·소속 주장', ROLE_CLAIM: '직책·역할 주장',
  STATE_CLAIM: '상태 주장', EVENT_CLAIM: '사건 주장', ACTION_INSTRUCTION: '행동 지시',
  PROHIBITION: '행동 금지', QUESTION: '질문', WARNING: '경고', THREAT: '위협', PROMISE: '약속',
  JUSTIFICATION: '명분 제시', CONDITION: '조건 제시', OBSERVED_ACTION: '관찰된 행동',
  REPORTED_ACTION: '진술된 행동', CUSTOMER_RESPONSE: '고객 반응', DISCLOSURE_REQUEST: '정보 제공 요구',
  SECRECY_REQUEST: '비밀 유지 요구', COMMUNICATION_CONTROL: '연락 통제', FINANCIAL_ACTION: '금전 행동',

  CLAIMS_IDENTITY: '신분 사칭 주장', CLAIMS_ORGANIZATION: '기관·소속 사칭 주장',
  CLAIMS_ROLE: '직책·역할 사칭 주장', CLAIMS_ACCOUNT_INVOLVEMENT: '계좌 범죄 연루 주장',
  CLAIMS_CRIME_INVOLVEMENT: '계좌·명의 범죄 연루 주장', TRANSFER_FUNDS: '자금 이체 요구',
  WITHDRAW_CASH: '현금 인출 요구', DISCLOSE_OTP: '일회용 인증번호(OTP) 제공 요구',
  DISCLOSE_PASSWORD: '비밀번호 제공 요구', PROVIDE_CARD_INFO: '카드정보 제공 요구',
  INSTALL_APP: '앱 설치 요구', OPEN_URL: '링크 열기 요구', SHARE_SCREEN: '화면 공유 요구',
  MAINTAIN_CALL: '통화 유지 요구', END_CALL: '통화 종료', KEEP_SECRET: '비밀 유지 요구',
  AVOID_REPORTING: '신고 제한 요구', AVOID_EXTERNAL_CONTACT: '외부 연락 제한 요구',
  THREATEN_ARREST: '체포 위협', THREATEN_ASSET_FREEZE: '자산 동결 위협',
  JUSTIFY_ASSET_PROTECTION: '자산 보호 명분', PROMISE_RETURN: '자금 반환 약속', OTHER: '기타',

  CUSTOMER_ACCOUNT: '고객 계좌', EXTERNAL_ACCOUNT: '외부 계좌',
  CLAIMED_SAFE_ACCOUNT: '상대방이 제시한 안전계좌', THIRD_PARTY: '제3자', FAMILY: '가족',
  PROSECUTION_SERVICE: '검찰', POLICE_SERVICE: '경찰', FINANCIAL_SUPERVISORY_SERVICE: '금융감독원',
  FINANCIAL_INSTITUTION: '금융기관', BANK: '은행', CARD_COMPANY: '카드사', COURT: '법원',
  PUBLIC_AGENCY: '공공기관', ACQUAINTANCE: '지인', DELIVERY_LOGISTICS: '배송·물류기관',
  LOAN_COMPANY: '대출업체', TELECOM_COMPANY: '통신사', DELIVERY_COMPANY: '배송업체',
  GOVERNMENT_AGENCY: '공공기관',
  INVESTIGATOR: '수사관', PROSECUTOR: '검사', POLICE_OFFICER: '경찰관',
  BANK_EMPLOYEE: '은행 직원', FSS_EMPLOYEE: '금융감독원 직원', COURT_EMPLOYEE: '법원 직원',
  LOAN_COUNSELOR: '대출 상담원', DELIVERY_AGENT: '배송 담당자', FAMILY_MEMBER: '가족',
  CHILD: '자녀', PARENT: '부모', SON: '아들', DAUGHTER: '딸',

  INSTITUTION: '기관', ORGANIZATION: '조직', PERSON_NAME: '인물명', ROLE: '직책·역할',
  RELATIONSHIP: '관계', VOCATIVE: '호칭 대상', ACTION: '행동', PURPOSE: '목적',
  DEADLINE: '기한', LOCATION: '장소', DEVICE: '기기', CONTACT: '연락처',
  SUBJECT: '주체', ACTOR: '행위자', TARGET: '대상', DESTINATION: '도착 대상', OBJECT: '행동 대상',

  SUPPORTS: '뒷받침 관계', JUSTIFIES: '명분 관계', REQUIRES: '선행 요구 관계',
  CAUSES: '원인·결과 관계', CONDITIONAL_ON: '조건 관계', CONTRADICTS: '상충 관계',
  PRESSURE: '압박 구간', MIXED: '복합 정황 구간',

  MENTIONED: '언급됨', CLAIMED: '주장됨', REQUESTED: '요구됨', REPORTED: '진술됨', INSTRUCTED: '지시됨',
  PLANNED: '계획됨', ATTEMPTED: '시도됨', VERIFIED: '확인됨', COMPLETED: '완료 진술',
  FAILED: '실패', CANCELLED: '취소', DENIED: '부인됨', UNVERIFIED: '미확인',
  CALLER_CLAIM: '의심 인물 주장', CUSTOMER_REPORTED: '고객 진술', STAFF_REPORTED: '담당자 기록',
  ASSERTION: '주장', REQUEST: '요청', DIRECTIVE: '지시', INSTRUCTION: '지시',
  CONDITIONAL: '조건부 표현', OPTIONAL: '선택적 표현', SUGGESTED: '권고 표현', REQUIRED: '필수 요구',
  POSITIVE: '긍정형', NEGATIVE: '부정형', WEAK: '약함', MEDIUM: '보통', STRONG: '강함',
  NONE: '없음', LOW: '낮음', HIGH: '높음', CRITICAL: '매우 높음',

  IMMEDIATE: '즉시', TODAY: '오늘 안', WITHIN_30_MINUTES: '30분 이내',
  BEFORE_CALL_END: '통화 종료 전', BEFORE_BANK_CLOSE: '은행 영업 종료 전',
  UNKNOWN_DEADLINE: '기한 확인 필요',
  NO_END_CALL: '통화 종료 금지', NO_EXTERNAL_CONTACT: '외부 연락 금지',
  NO_REPORTING: '신고 금지', NO_FAMILY_DISCLOSURE: '가족에게 알리지 말라는 요구',
  NO_BANK_CONTACT: '은행 연락 금지', NO_SEARCH: '검색 금지',

  OTP: '일회용 인증번호(OTP)', SECURITY_CODE: '인증번호', PASSWORD: '비밀번호',
  PIN: '비밀번호(PIN)', CARD_CVC: '카드 보안코드(CVC)', CERTIFICATE_SECRET: '인증서 비밀번호',
  ALL_FUNDS: '전액', PARTIAL_FUNDS: '일부 금액', HALF: '절반',
  REMAINING_BALANCE: '잔액', MAXIMUM_AVAILABLE: '가능한 최대 금액', EXPLICIT_AMOUNT: '명시된 금액',
  TRANSFER_OUT: '출금·이체 금액', REFUND_IN: '환급 금액', REQUESTED_AMOUNT: '요구 금액',
  CLAIMED_LOSS: '주장된 피해 금액', OUT: '출금', IN: '입금',
  ASSET_PROTECTION: '자산 보호', INVESTIGATION: '수사', VERIFICATION: '본인·계좌 확인',
  FEE_PAYMENT: '수수료 납부', REPAYMENT: '대출 상환',

  ARREST_THREAT: '체포 위협', ASSET_FREEZE_THREAT: '자산 동결 위협',
  LEGAL_ACTION_THREAT: '법적 조치 위협', FINANCIAL_LOSS_THREAT: '금전 손실 위협',
  ACCOUNT_SUSPENSION_THREAT: '계좌 정지 위협', FAMILY_HARM_THREAT: '가족 위해 위협',
  INVESTIGATION_ESCALATION_THREAT: '수사 확대 위협',

  PROSECUTION: '검찰', POLICE: '경찰', FINANCIAL_AUTHORITY: '금융기관',
  INVESTIGATOR_ROLE: '수사관 신분', PROSECUTOR_ROLE: '검사 신분', POLICE_ROLE: '경찰 신분',
  BANK_ROLE: '은행 직원 신분', ACCOUNT_CRIME_LINK: '계좌 범죄 연루', CRIME_INVOLVEMENT: '범죄 연루',
  ARREST: '체포', ASSET_FREEZE: '자산 동결', SAFE_ACCOUNT: '안전계좌 명목',
  TRANSFER: '송금·이체', WITHDRAWAL: '현금 인출', EXACT_AMOUNT: '구체 금액',
  APP_INSTALL: '앱 설치', URL_OPEN: '링크 열기', SCREEN_SHARE: '화면 공유',
  NO_FAMILY: '가족 연락 제한',

  UNMAPPED: '분류 검토 필요', REVIEWED: '검토됨', MAPPED: '분류됨', DISMISSED: '제외됨',
  TRANSFERRED: '이체함', NOT_TRANSFERRED: '이체하지 않음', EXPOSED: '노출 의심',
  YES: '예', NO: '아니요', PARTIAL: '일부 해당',
  BANK_INTERNAL: '은행 내부', CUSTOMER_SHARED: '고객 공유', SHARED: '공유',
  DETERMINISTIC_ATOM_RULE: '구조화 규칙', LLM_VERIFIED: 'AI 검토',
};

const normalize = (value: string) => value.trim().replace(/[\s-]+/g, '_').toUpperCase();
const internalToken = /^[A-Z][A-Z0-9_.-]*(?:_[A-Z0-9_.-]+)+$|^[A-Z][A-Z0-9_.-]{2,}$/;

export const analysisCodeLabel = (value?: string | null, fallback = '분류 확인 필요'): string => {
  if (!value?.trim()) return fallback;
  const text = value.trim();
  return labels[normalize(text)] ?? (/[가-힣]/.test(text) ? text : fallback);
};

export const analysisConcreteLabel = (value?: string | null, fallback = '확인 필요'): string => {
  if (!value?.trim()) return fallback;
  const text = value.trim();
  const known = labels[normalize(text)];
  if (known) return known;
  return internalToken.test(text) ? fallback : text;
};

export const analysisRoleLabel = (value?: string | null): string => {
  if (!value || normalize(value) === 'UNKNOWN') return '화자 미상 · 확인 필요';
  return labels[normalize(value)] ?? '화자 미상 · 확인 필요';
};

export const replaceAnalysisTokens = (value: string): string => {
  let result = value;
  Object.entries(labels)
    .sort(([left], [right]) => right.length - left.length)
    .forEach(([token, label]) => {
      result = result.replace(new RegExp(`(?<![A-Za-z0-9_])${token.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?![A-Za-z0-9_])`, 'gi'), label);
    });
  return result.replace(/\b[A-Z][A-Z0-9_.]*(?:_[A-Z0-9_.]+)+\b/g, '분류 확인 필요');
};

const suspectedActionPredicates = new Set([
  'TRANSFER_FUNDS', 'WITHDRAW_CASH', 'DISCLOSE_OTP', 'DISCLOSE_PASSWORD', 'PROVIDE_CARD_INFO',
  'INSTALL_APP', 'OPEN_URL', 'SHARE_SCREEN', 'MAINTAIN_CALL', 'KEEP_SECRET', 'AVOID_REPORTING',
  'AVOID_EXTERNAL_CONTACT',
]);

export const attributionWarning = (
  predicate?: string | null,
  actorRole?: string | null,
  claimStatus?: string | null,
): string | null => {
  if (!predicate || normalize(actorRole || '') !== 'CUSTOMER') return null;
  const normalizedPredicate = normalize(predicate);
  const suspectedFeature = ['ROLE_', 'CLAIM_', 'CLAIMED_', 'REQUEST_', 'PURPOSE_', 'TACTIC_', 'DEADLINE_']
    .some((prefix) => normalizedPredicate.startsWith(prefix));
  if (!suspectedActionPredicates.has(normalizedPredicate) && !suspectedFeature) return null;
  return normalize(claimStatus || '') === 'CUSTOMER_REPORTED' ? null : '역할 귀속 충돌 · 확인 필요';
};

export const observedTermLabel = (term: { surface_form?: string | null; semantic_value?: string | null }): string => {
  const surface = term.surface_form?.trim();
  if (surface && /[가-힣]/.test(surface)) return surface;
  return analysisConcreteLabel(term.semantic_value || surface, '세부 표현 확인 필요');
};
