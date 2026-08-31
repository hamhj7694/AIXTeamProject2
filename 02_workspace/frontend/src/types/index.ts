// 상담 관련 타입
export interface Message {
  id: string;
  role: 'assistant' | 'user' | 'system';
  type: 'text' | 'question' | 'choice' | 'warning' | 'persuasion' | 'action_instruction' | 'action_confirmation' | 'result';
  content: string;
  choices?: Choice[];
  relatedStep?: string;
  createdAt: number;
  metadata?: Record<string, any>;
}

export interface Choice {
  id: string;
  label: string;
  value: string;
  nextStep?: string;
  riskImpact?: 'low' | 'medium' | 'high';
  action?: string;
}

export interface SituationInfo {
  id: string;
  description: string;
  category?: string;
}

export interface RiskSignal {
  id: string;
  signal: string;
  severity: 'low' | 'medium' | 'high';
  explanation?: string;
}

export type ConsultationState = 'idle' | 'in_progress' | 'waiting_for_action' | 'action_completed' | 'completed' | 'paused';
export type ConsultationStep = 'situation_check' | 'risk_signal_check' | 'persuasion' | 'immediate_action' | 'action_confirmation' | 'next_action' | 'result';
export type UserState = 'S0' | 'S1' | 'S2' | 'S3' | 'S4' | 'S5';

export interface ConsultationSession {
  id: string;
  status: ConsultationState;
  currentStep: ConsultationStep;
  userState: UserState;
  scenario?: string;
  riskLevel: 'low' | 'medium' | 'high';
  messages: Message[];
  detectedSignals: RiskSignal[];
  situationInfo: SituationInfo[];
  actionPlan?: string[];
  completedActions: string[];
  currentAction?: string;
  result?: ConsultationResult;
  startedAt: number;
  completedAt?: number;
}

export interface ConsultationResult {
  id: string;
  summary: string;
  situation: string;
  riskSignals: RiskSignal[];
  completedActions: string[];
  pendingActions: string[];
  recommendations: string[];
  relatedGuides: string[];
}

export interface ConsultationHistory {
  id: string;
  title: string;
  scenario?: string;
  status: ConsultationState;
  riskLevel: 'low' | 'medium' | 'high';
  summary: string;
  completedActions: string[];
  startedAt: number;
  completedAt?: number;
}

export interface SafetyGuide {
  id: string;
  title: string;
  summary: string;
  sections: GuideSection[];
  priority: number;
}

export interface GuideSection {
  id: string;
  title: string;
  content: string;
  tips?: string[];
}

export interface ResponseGuide {
  id: string;
  title: string;
  description: string;
  warningSigns: string[];
  responseSteps: ResponseStep[];
  emergencyContacts?: EmergencyContact[];
  relatedGuides: string[];
}

export interface ResponseStep {
  id: string;
  order: number;
  title: string;
  description: string;
  action?: string;
}

export interface EmergencyContact {
  name: string;
  phone: string;
  description?: string;
  url?: string;
}
