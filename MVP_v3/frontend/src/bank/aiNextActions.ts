import type { VerificationTask } from '../api/types';

// 현재 Case에서 결과 확인이 남은 항목만 AI 카드의 이동 Action으로 노출한다.
export const reviewableVerifications = (tasks: VerificationTask[]): VerificationTask[] =>
  tasks.filter((task) => task.status === 'PENDING' || task.status === 'IN_PROGRESS' || task.status === 'ON_HOLD');
