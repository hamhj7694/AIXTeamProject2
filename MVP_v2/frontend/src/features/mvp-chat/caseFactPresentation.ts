export const canonicalCaseField = (field: string) => {
  const normalized = field.trim().toUpperCase();
  const aliases: Record<string, string> = {
    PERSONAL_INFO: 'personal_information_exposure',
    PERSONAL_INFORMATION: 'personal_information_exposure',
    AUTHENTICATION_INFO: 'authentication_information_exposure',
    AUTH_INFO: 'authentication_information_exposure',
    VICTIM_TRANSFER_STATUS: 'transfer_status',
  };
  return aliases[normalized] ?? field.trim().toLowerCase();
};

const presentations: Record<string, { label: string; fallbackQuestion: string }> = {
  transfer_status: { label: '송금 여부', fallbackQuestion: '상대방에게 송금하거나 이체한 사실이 있습니까?' },
  transfer_purpose: { label: '송금 요구 목적', fallbackQuestion: '상대방은 어떤 이유로 송금이나 자금 이동을 요구했습니까?' },
  personal_information_exposure: { label: '개인정보 제공 여부', fallbackQuestion: '주민등록번호나 계좌번호 등 개인정보를 제공했습니까?' },
  authentication_information_exposure: { label: '인증정보 제공 여부', fallbackQuestion: '인증번호, 비밀번호 또는 OTP를 제공했습니까?' },
  credential_exposure: { label: '개인·인증정보 제공 여부', fallbackQuestion: '비밀번호, 인증번호 또는 신분증 정보를 전달했습니까?' },
  remote_control_app: { label: '원격제어 앱 설치 여부', fallbackQuestion: '원격제어 또는 화면공유 앱을 설치했습니까?' },
  claimed_organization: { label: '사칭 기관', fallbackQuestion: '상대방은 어느 기관이나 회사 소속이라고 말했습니까?' },
  impersonated_institution: { label: '사칭 기관', fallbackQuestion: '상대방이 어느 기관이나 은행을 사칭했습니까?' },
  incident_claim: { label: '상대방의 사건 주장', fallbackQuestion: '상대방은 어떤 사건이나 문제가 발생했다고 말했습니까?' },
};

export const caseFieldPresentation = (field: string) => {
  const canonical = canonicalCaseField(field);
  return presentations[canonical] ?? {
    label: '고객 확인 정보',
    fallbackQuestion: '이 내용이 맞는지 고객 답변을 확인해 주세요.',
  };
};
