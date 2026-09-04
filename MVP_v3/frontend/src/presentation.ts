import type { CaseFact, DiagnosisEvent, RiskLevel, StoredCase, VerificationTask } from './api/types';

export const riskLabel = (risk: RiskLevel) => ({ HIGH: '고위험', LOW: '주의', NORMAL: '낮은 위험' }[risk]);
export const riskTone = (risk: RiskLevel) => ({ HIGH: 'danger', LOW: 'warning', NORMAL: 'safe' }[risk]);

export const statusLabel = (status: string, mode?: string) => {
  if (status === 'CLOSED' || mode === 'CLOSED') return '종료';
  if (mode === 'RECOVERY') return '피해구제';
  if (status === 'VERIFYING') return '검증 중';
  if (status === 'IN_PROGRESS') return '대응 중';
  if (status === 'TRIAGE' || status === 'NEW') return '확인 중';
  return '확인 중';
};

export const verificationStatusLabel = (status: string) => ({
  PENDING: '확인 대기', IN_PROGRESS: '확인 중', COMPLETED: '확인 완료', ON_HOLD: '보류', FAILED: '확인 불가',
}[status] ?? status);

export const actionLabel = (type: string) => ({
  PAYMENT_HOLD_REVIEW: '송금·지급정지 검토',
  ACCOUNT_REPORT_GUIDANCE: '사기이용계좌 신고 안내',
  EVIDENCE_PRESERVATION: '증빙자료 확보',
  DEVICE_SECURITY_GUIDANCE: '기기·계정 보호 안내',
  CUSTOMER_CALLBACK: '고객 재확인',
  HUMAN_TAKEOVER: '담당자 직접 대응',
  RESUME_AI: 'AI 지원 재개',
  OTHER: '기타 대응 업무',
}[type] ?? type.replace(/_/g, ' '));

export const fieldLabel = (field: string) => ({
  transfer_status: '실제 송금 여부', VICTIM_TRANSFER_STATUS: '실제 송금 여부',
  personal_information_exposure: '개인정보 제공 여부', PERSONAL_INFO: '개인정보 제공 여부',
  authentication_information_exposure: '인증정보 제공 여부', AUTHENTICATION_INFO: '인증정보 제공 여부',
  requested_account: '요구받은 계좌', caller_phone: '상대방 전화번호', institution_name: '사칭 기관',
  remote_control_app: '원격제어 앱 설치 여부', actual_loss_amount_krw: '실제 피해 금액',
}[field] ?? field.replace(/_/g, ' '));

export const formatClock = (value: string) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '시간 미상' : date.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
};

export const relativeTime = (value: string) => {
  const time = new Date(value).getTime();
  if (!Number.isFinite(time)) return '시간 미상';
  const seconds = Math.max(0, Math.floor((Date.now() - time) / 1000));
  if (seconds < 60) return '방금 전';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}분 전`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}시간 전`;
  return new Date(value).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
};

const unique = (items: Array<string | null | undefined>) => Array.from(new Set(items.map((item) => item?.trim()).filter((item): item is string => Boolean(item))));

export const incidentTitle = (item: StoredCase) => item.diagnosis.context?.incident_type || '보이스피싱 의심 사건';
export const caseSummary = (item: StoredCase) => item.diagnosis.context?.summary || item.initial_brief;
export const caseClaims = (item: StoredCase) => unique(item.diagnosis.context?.claims ?? []);
export const caseDemands = (item: StoredCase) => unique((item.diagnosis.events ?? [])
  .filter((event: DiagnosisEvent) => ['ACTION_REQUEST', 'MONEY_MOVEMENT', 'AMOUNT'].includes(event.event_family))
  .filter((event) => event.is_requested !== false)
  .map((event) => event.evidence_text));
export const riskReasons = (item: StoredCase) => unique([
  ...(item.diagnosis.evidence ?? []).map((evidence) => evidence.text),
  ...(item.diagnosis.events ?? []).filter((event) => ['IMPERSONATION', 'PSY_STRATEGY', 'MONEY_MOVEMENT'].includes(event.event_family)).map((event) => event.evidence_text),
]).slice(0, 4);
export const recommendedSteps = (item: StoredCase) => unique(item.diagnosis.context?.recommended_next_steps ?? []);

export const confirmedFacts = (facts: CaseFact[]) => facts.filter((fact) => fact.status === 'CONFIRMED');
export const proposedFacts = (facts: CaseFact[]) => facts.filter((fact) => fact.status !== 'CONFIRMED');
export const activeVerifications = (tasks: VerificationTask[]) => tasks.filter((task) => !['COMPLETED', 'FAILED'].includes(task.status));
