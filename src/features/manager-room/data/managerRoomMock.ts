import { ManagerRoomCase } from '../types';

// URL의 caseId만 실제 화면 흐름에서 받고, 나머지는 API 교체 전까지 사용할 가상 정보다.
export const createManagerRoomCaseMock = (
  caseId: string
): ManagerRoomCase => ({
  caseId,
  title: '보이스피싱 의심 사건',
  risk: 'HIGH',
  status: '확인 중',
  dataSource: 'MVP Mock',
});
