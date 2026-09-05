/** Presentation only: never rewrite IDs, API keys, URLs or persisted source data. */
const labels: Record<string, string> = {
  personal_info_shared: '개인정보 제공 여부', personal_information_exposure: '개인정보 제공 여부', personal_info: '개인정보 제공 여부',
  authentication_information_exposure: '인증정보 제공 여부', authentication_info: '인증정보 제공 여부', auth_info_shared: '인증정보 제공 여부', auth_info: '인증정보 제공 여부',
  victim_transfer_status: '실제 송금 여부', transfer_status: '실제 송금 여부', transfer_purpose: '송금 요구 이유',
  claimed_organization: '사칭 기관', incident_claim: '상대방 주장', requested_account: '요구받은 계좌',
  caller_phone: '상대방 전화번호', remote_control_app: '원격제어 앱 설치 여부', actual_loss_amount_krw: '실제 피해 금액',
  impersonation: '기관·신분 사칭', action_request: '특정 행동 요구', 'action request': '특정 행동 요구',
  money_movement: '금전 이동 요구', 'money movement': '금전 이동 요구', psy_strategy: '심리적 압박', 'psy strategy': '심리적 압박',
  sensitive_info: '개인정보 요구', contact_restriction: '주변 연락 제한', prosecution: '검찰 사칭',
  urgency: '긴급성 강조', isolation: '주변과의 연락 차단', fear: '불안·공포 조성',
  casefact: '사건 확인 정보', proposed: '확인 전', confirmed: '담당자 확인', unresolved: '확인 필요',
  payment_hold_review: '지급정지 검토', human_takeover: '담당자 직접 대응', staff_judgment: '담당자 판단',
  evidence_preservation: '증빙 보관', account_report_guidance: '계좌 신고 안내',
  not_provided: '제공하지 않음', not_transferred: '송금하지 않음', unknown: '확인되지 않음',
};
const pattern = new RegExp('(?<![A-Za-z0-9_])(' + Object.keys(labels).sort((a, b) => b.length - a.length).join('|') + ')(?![A-Za-z0-9_])', 'gi');
export const userText = (text: string): string => text.split(/(https?:\/\/[^\s<>]+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|[^\s]+\.(?:pdf|docx?|xlsx?|png|jpe?g|txt|csv))/gi).map((part, index) => index % 2 ? part : part.replace(pattern, (token) => labels[token.toLowerCase()]).replace(/\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+\b/g, '추가 확인 정보')).join('');

const visibleKeys = new Set(['content', 'note', 'summary', 'situation_summary', 'initial_brief', 'question_text', 'customer_explanation', 'reason', 'description', 'result_summary', 'claim', 'target', 'value', 'evidence_text', 'text', 'incident_type', 'next_action', 'answer_text', 'staff_text', 'ai_text', 'title', 'label', 'purpose']);
const visibleArrays = new Set(['key_signals', 'offender_claims', 'offender_demands', 'manipulation_tactics', 'customer_exposure', 'next_actions', 'claims', 'recommended_next_steps', 'warnings', 'next_checks']);
export const presentResponse = (value: unknown, key = ''): unknown => {
  if (typeof value === 'string') return visibleKeys.has(key) || visibleArrays.has(key) ? userText(value) : value;
  if (Array.isArray(value)) return value.map((item) => presentResponse(item, key));
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>;
    return Object.fromEntries(Object.entries(record).map(([childKey, child]) => [childKey,
      childKey === 'content' && ['CUSTOMER', 'BANK_STAFF'].includes(String(record.actor_type)) ? child : presentResponse(child, childKey)]));
  }
  return value;
};

/** Default list is short; a disclosure retains access to longer source material. */
export const bulletLines = (text: string) => [...new Set(userText(text).split(text.includes('\n') ? /\n+/ : /(?<=[.!?。])\s+(?=[가-힣A-Z])/).map((line) => line.replace(/^\s*(?:[-*•]|\d+[.)])\s*/, '').trim()).filter(Boolean))];

export const priorityLabel = (value: string) => ({ P0: '긴급', P1: '우선 확인', P2: '일반 확인' }[value] ?? '확인 필요');
export const eventLabel = (value: string) => ({
  CASE_CREATED: '사건 등록', CASE_UPDATED: '사건 정보 변경', CASE_STATUS_CHANGED: '사건 처리 상태 변경',
  BANK_ACTION_ADDED: '대응 업무 기록 추가', CASE_CHECKLIST_UPDATED: '체크리스트 상태 변경',
  CUSTOMER_QUESTION_DISPATCHED: '고객 확인 질문 발송', CUSTOMER_QUESTION_ANSWERED: '고객 답변 접수',
  CASE_FACT_PROPOSED: '확인할 사실 추가', CASE_FACT_CONFIRMED: '담당자 사실 확인',
  VERIFICATION_REQUESTED: '기관 확인 요청', VERIFICATION_UPDATED: '기관 확인 결과 변경',
  MESSAGE_CREATED: '대화 기록 추가', REPORT_FINALIZED: '사건 정리 완료',
  VOICE_SESSION_REQUESTED: '통화 연결 요청', CUSTOMER_QUESTIONS_QUEUED: '고객 확인 질문 등록',
}[value] ?? '사건 기록 변경');
