import { Message, Choice, ConsultationSession, RiskSignal, SituationInfo } from '../../types';

/**
 * 상담 관련 타입 정의
 */
export interface ConsultationState {
  session: ConsultationSession | null;
  isLoading: boolean;
  error: string | null;
  showActionIntervention: boolean;
  interventionType?: 'stop_money_transfer' | 'stop_personal_info' | 'already_damaged';
}

export interface ConsultationMessage {
  id: string;
  role: 'assistant' | 'user' | 'system';
  type: 'text' | 'question' | 'choice' | 'warning' | 'persuasion' | 'action_instruction' | 'action_confirmation' | 'result' | 'briefing';
  content: string;
  choices?: Choice[];
  situationInfo?: SituationInfo[];
  riskSignals?: RiskSignal[];
  metadata?: Record<string, any>;
  createdAt: number;
  animated?: boolean;
}

export type UserState = 'S0' | 'S1' | 'S2' | 'S3' | 'S4' | 'S5';

export interface ConsultationFlowStep {
  id: string;
  type: string;
  message: string;
  choices?: Choice[];
  nextStepByChoice?: Record<string, string>;
  riskSignalsToAdd?: RiskSignal[];
  situationToAdd?: SituationInfo[];
  shouldShowIntervention?: boolean;
  interventionType?: 'stop_money_transfer' | 'stop_personal_info' | 'already_damaged';
}
