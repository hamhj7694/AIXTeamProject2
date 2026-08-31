export const MANAGER_ROOM_VIEWS = [
  'workspace',
  'progress',
  'evidence',
  'customer',
] as const;

export type ManagerRoomView = (typeof MANAGER_ROOM_VIEWS)[number];

export interface ManagerRoomCase {
  caseId: string;
  title: string;
  risk: 'HIGH' | 'MEDIUM' | 'LOW';
  status: string;
  dataSource: 'MVP Mock';
}

export const isManagerRoomView = (
  value: string | null
): value is ManagerRoomView => {
  return MANAGER_ROOM_VIEWS.some((view) => view === value);
};
