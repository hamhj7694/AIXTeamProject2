import type { CaseRecord } from '../services/caseApi';

export const workflowStatusLabel = (status: string) => ({
  TRIAGE: '진행중',
  OPEN: '진행중',
  IN_PROGRESS: '진행중',
  VERIFYING: '검증 진행중',
  PREVENT: '예방 진행중',
  RECOVERY: '피해 복구중',
  CLOSED: '처리완료',
  RESOLVED: '처리완료',
}[status] ?? '확인중');

export const victimStatusLabel = (transferred: CaseRecord['transferred']) =>
  transferred === true ? '피해 발생' : transferred === false ? '피해 없음' : '확인안됨';

export const actualLossLabel = (amount?: string) => amount ?? '확인안됨';
export const caseDisplayId = (id: string) => '#' + id.replace(/^VP-/, '');

export const caseProgressStage = (status: string, transferred: boolean | null | undefined, mode?: string) => {
  if (status === 'CLOSED' || status === 'RESOLVED') return 4;
  if (status === 'IN_PROGRESS' || mode === 'RECOVERY' || transferred === true) return 3;
  if (status === 'VERIFYING') return 2;
  return 1;
};

export const caseProgressMessage = (stage: number, recovery = false) => {
  if (stage >= 4) return '사건 처리가 완료되었습니다.';
  if (recovery) return '추가 피해 차단과 피해구제 절차를 진행하고 있습니다.';
  if (stage === 3) return '필요한 보호 조치를 안내하고 있습니다.';
  if (stage === 2) return '공식 채널을 통해 기관 정보를 확인하고 있습니다.';
  return '피해 여부와 필요한 정보를 확인하고 있습니다.';
};
