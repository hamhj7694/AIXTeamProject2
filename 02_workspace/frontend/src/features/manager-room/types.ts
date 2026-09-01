export const MANAGER_ROOM_VIEWS = [
  'workspace',
  'progress',
  'evidence',
  'report',
] as const;

export type ManagerRoomView = (typeof MANAGER_ROOM_VIEWS)[number];

export interface ManagerRoomCase {
  caseId: string;
  title: string;
  risk: 'HIGH' | 'MEDIUM' | 'LOW';
  status: string;
  dataSource: 'MVP Mock';
}

export interface ManagerRoomAssignee {
  role: string;
  name: string;
  workStatus: string;
}

export interface ManagerRoomFinalReport {
  caseId: string;
  risk: ManagerRoomCase['risk'];
  status: string;
  assignee: string;
  closedAt: string;
  reportUpdatedAt: string;
  summary: string;
  riskEvidence: string[];
  counterEvidence: string[];
  customerFindings: string[];
  unknowns: string[];
  checklistItems: ManagerRoomChecklistItem[];
  internalMemos: ManagerRoomMemoItem[];
  resolution: string[];
  evidenceSources: string[];
}

export interface ManagerRoomMessage {
  id: string;
  role: 'manager' | 'assistant';
  content: string;
}

export interface ManagerRoomCustomerMessage {
  id: string;
  role: 'manager' | 'customer' | 'system';
  content: string;
}

export interface ManagerRoomWorkspaceMock {
  brief: string;
  riskEvidence: string[];
  counterEvidence: string[];
  unknowns: string[];
  recommendedQuestion: string;
  initialMessages: ManagerRoomMessage[];
}

export type ManagerRoomEvidenceSource = 'fds' | 'stt';

export interface ManagerRoomFdsMock {
  signalStatus: string;
  managerStatus: string;
  summary: string;
  unavailableDetails: string[];
  confirmationPoints: string[];
}

export interface ManagerRoomSttExcerpt {
  id: string;
  speaker: '상대방';
  content: string;
}

export interface ManagerRoomSttMock {
  sourceLabel: 'MVP Mock 발췌';
  notice: string;
  excerpts: ManagerRoomSttExcerpt[];
  confirmationPoints: string[];
}

export type ManagerRoomProgressPhase = 'past' | 'current' | 'next';

export interface ManagerRoomProgressEvent {
  id: string;
  phase: ManagerRoomProgressPhase;
  title: string;
  description: string;
  label: string;
  isKey: boolean;
}

export interface ManagerRoomChecklistItem {
  id: string;
  label: string;
  completed: boolean;
}

export interface ManagerRoomMemoItem {
  id: string;
  content: string;
}

export interface ManagerRoomProgressMock {
  currentStage: string;
  currentFocus: string;
  nextStage: string;
  events: ManagerRoomProgressEvent[];
  checklist: ManagerRoomChecklistItem[];
}

export const isManagerRoomView = (
  value: string | null
): value is ManagerRoomView => {
  return MANAGER_ROOM_VIEWS.some((view) => view === value);
};
