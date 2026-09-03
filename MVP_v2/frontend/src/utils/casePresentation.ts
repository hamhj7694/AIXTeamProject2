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
