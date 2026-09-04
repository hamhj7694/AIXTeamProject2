import type { CaseFact } from '../../services/mvpChatApi';
import { canonicalCaseField } from './caseFactPresentation';

export interface AnswerRiskItem {
  risk_id: string;
  claim: string;
  sourceLabel: string;
}

const riskLabels: Record<string, string> = {
  transfer_status: '고객이 상대방에게 송금 또는 이체를 진행했다고 답했습니다.',
  personal_information_exposure: '고객이 주민등록번호·계좌번호 등 개인정보를 제공했다고 답했습니다.',
  authentication_information_exposure: '고객이 인증번호·비밀번호·OTP 등 인증정보를 제공했다고 답했습니다.',
  credential_exposure: '고객이 개인정보 또는 인증정보를 전달했다고 답했습니다.',
  remote_control_app: '고객이 원격제어 또는 화면공유 앱을 설치했다고 답했습니다.',
};

const negativeAnswers = ['아니요', '없음', '안했어요', '하지않음', '제공하지않았어요', '설치하지않음', '잘모르겠어요', '모르겠어요', 'no', 'false'];
const positiveAnswers = ['예', '네', '있음', '했어요', '진행했어요', '제공했어요', '전달함', '설치함', 'yes', 'true'];

const compact = (value: string) => value.trim().replace(/\s+/g, '').toLocaleLowerCase('ko-KR');

const isAffirmative = (value: string) => {
  const normalized = compact(value);
  if (negativeAnswers.some((answer) => normalized === answer || normalized.includes(answer))) return false;
  return positiveAnswers.some((answer) => normalized === answer || normalized.includes(answer));
};

export const deriveAnswerRisks = (facts: CaseFact[]): AnswerRiskItem[] => {
  const latestByField = new Map<string, CaseFact>();
  for (const fact of facts) latestByField.set(canonicalCaseField(fact.field), fact);
  return [...latestByField.values()]
    .filter((fact) => Boolean(riskLabels[canonicalCaseField(fact.field)]) && isAffirmative(fact.value))
    .map((fact) => ({
      risk_id: `answer-risk-${fact.fact_id}`,
      claim: riskLabels[canonicalCaseField(fact.field)],
      sourceLabel: fact.status === 'CONFIRMED' ? '담당자 확정' : '고객 답변',
    }));
};
