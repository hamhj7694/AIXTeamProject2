export type RiskLevel = 'NORMAL' | 'LOW' | 'HIGH';
export type MessageChannel = 'TEAM' | 'CUSTOMER' | 'AI_INTERNAL';
export type MessageVisibility = 'BANK_INTERNAL' | 'CUSTOMER' | 'AI_PRIVATE';

export interface DiagnosisEvent {
  event_family: 'IMPERSONATION' | 'PSY_STRATEGY' | 'ACTION_REQUEST' | 'MONEY_MOVEMENT' | 'AMOUNT';
  subtype?: string | null;
  impersonation_group?: string | null;
  evidence_text: string;
  amount_krw?: number | null;
  amount_context?: string | null;
  is_requested?: boolean | null;
}

export interface DiagnosisEvidence {
  turn: number;
  event_family: string;
  subtype?: string | null;
  text: string;
}

export interface DiagnosisWindow {
  segment_id: string;
  start_turn: number;
  end_turn: number;
  text: string;
  raw_ml_risk_score: number;
  final_risk_score: number;
  threshold_score: number;
  candidate_signal_count: number;
  guardrail_applied: boolean;
  label: 'NORMAL' | 'PHISHING';
}

export interface InitialReportSection {
  section_key: string;
  content: Record<string, unknown>;
  version: number;
}

export interface InitialReport {
  report_id: string;
  case_id: string;
  report_version: number;
  status: string;
  sections: InitialReportSection[];
  created_at: string;
  note?: string | null;
}

export interface AnalyzeCaseResponse {
  schema_version: string;
  disposition: 'CASE_CREATED' | 'NO_CASE' | 'FAILED';
  case_id?: string | null;
  risk?: RiskLevel | null;
  mode?: 'PREVENT' | 'RECOVERY' | null;
  status?: string | null;
  initial_brief?: string | null;
  initial_report?: { report_id: string; case_id: string; report_version: number } | null;
  error?: { code: string; message: string; retryable: boolean } | null;
}

export interface StoredCase {
  case_id: string;
  version: number;
  risk: RiskLevel;
  risk_score: number;
  mode: 'PREVENT' | 'RECOVERY' | 'CLOSED';
  status: string;
  initial_brief: string;
  primary_assignee?: string | null;
  victim_transfer_status?: 'UNKNOWN' | 'YES' | 'NO';
  actual_loss_amount_krw?: number | null;
  input_text: string;
  diagnosis: {
    context?: {
      summary?: string;
      incident_type?: string;
      claims?: string[];
      recommended_next_steps?: string[];
      confidence?: number;
    };
    events?: DiagnosisEvent[];
    evidence?: DiagnosisEvidence[];
    windows?: DiagnosisWindow[];
    features?: Record<string, number>;
    case_context_features?: {
      claimed_actor_types: string[]; claim_codes: string[]; requested_action_codes: string[];
      manipulation_tactic_codes: string[]; exposure_risk_codes: string[];
      amount_values_krw: number[]; chronology: string[]; unknown_fields: string[];
    };
    warnings?: string[];
  };
  initial_report?: InitialReport | null;
  created_at: string;
  updated_at: string;
  deleted_at?: string | null;
  trash_expires_at?: string | null;
}

export interface Attachment {
  attachment_id: string;
  case_id: string;
  original_name: string;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  uploaded_by: string;
  status: 'UPLOADED' | 'LINKED';
  visibility: MessageVisibility;
  ai_readable: boolean;
  download_url: string;
  created_at: string;
}

export interface CaseMessage {
  message_id: string;
  case_id: string;
  actor_type: 'CUSTOMER' | 'BANK_STAFF' | 'CUSTOMER_AGENT' | 'BANK_AGENT' | 'VERIFICATION' | 'SYSTEM';
  actor_user_id: string;
  actor_display_name: string;
  actor_role: string | null;
  content: string;
  channel: MessageChannel;
  audience: 'BANK_INTERNAL' | 'CUSTOMER';
  visibility: MessageVisibility;
  message_kind: 'CHAT' | 'AI_REQUEST' | 'AI_RESPONSE' | 'SYSTEM_EVENT' | 'REPORT_CARD';
  private_owner_user_id: string | null;
  mentions: string[];
  reply_to_message_id: string | null;
  client_request_id?: string | null;
  attachments: Attachment[];
  created_at: string;
  /** Frontend-only delivery state. API responses omit this field. */
  delivery_state?: 'SENDING' | 'FAILED';
  delivery_error?: string | null;
}

export interface CaseEvent {
  event_id: number;
  case_id: string;
  event_type: string;
  actor_type: string;
  payload: Record<string, unknown>;
  occurred_at: string;
}

export interface VerificationTask {
  verification_task_id: string;
  case_id: string;
  claim: string;
  target: string;
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'ON_HOLD' | 'FAILED' | string;
  version: number;
  created_at: string;
  updated_at: string;
  result_summary?: string | null;
  evidence_url?: string | null;
  verified_by?: string | null;
  rag_source?: string | null;
  customer_visible?: boolean;
}

export interface CaseAction {
  action_id: string;
  case_id: string;
  action_type: string;
  status: string;
  actor_type: string;
  note: string;
  created_at: string;
  updated_at?: string | null;
  updated_by?: string | null;
}

export interface QuestionCandidate {
  question_id: string;
  target_field: string;
  question_text: string;
  reason: string;
  priority: 'P0' | 'P1' | 'P2';
  options?: string[];
  customer_explanation?: string | null;
  answer_mode?: 'SINGLE_CHOICE' | 'TEXT' | 'CHOICE_OR_TEXT';
  allow_free_text?: boolean;
}

export interface CustomerQuestion extends QuestionCandidate {
  case_id: string;
  source?: 'BANK_SELECTED' | 'CUSTOMER_AGENT';
  status: 'PENDING' | 'ASKED' | 'ANSWERED' | 'SKIPPED';
  sequence: number;
  requested_by?: string | null;
  asked_at?: string | null;
  answered_at?: string | null;
  answer_message_id?: string | null;
  answer_text?: string | null;
}

export interface CustomerVerificationResult {
  verification_task_id: string;
  target: string;
  result_summary: string;
  published_at?: string | null;
}

export interface CaseFact {
  fact_id: string;
  case_id: string;
  field: string;
  value: string;
  source: 'AI_EXTRACTED' | 'HUMAN_CONFIRMED' | 'VERIFIED' | 'UNRESOLVED';
  status: 'PROPOSED' | 'CONFIRMED' | 'UNRESOLVED';
  confidence: number;
  evidence_message_id?: string | null;
  source_question_id?: string | null;
  confirmed_by?: string | null;
  confirmed_at?: string | null;
  created_at: string;
}

export interface CaseBundle {
  customer_progress?: CustomerProgressItem[];
  case: Record<string, unknown>;
  final_report?: InitialReport | null;
  recent_messages: CaseMessage[];
  recent_events: CaseEvent[];
  recent_actions: CaseAction[];
  verification_tasks: VerificationTask[];
  questions: CustomerQuestion[];
  progress_items: Array<Record<string, unknown>>;
  customer_verification_results?: CustomerVerificationResult[];
  cursor?: string | null;
}

export interface CaseSupportSnapshot {
  case_id: string;
  available: boolean;
  case_brief: {
    summary: string;
    incident_type: string;
    risk_level: string;
    risk_score: number;
    next_checks: string[];
  } | null;
  case_context: {
    situation_summary: string;
    key_signals: string[];
    offender_claims: string[];
    offender_demands: string[];
    manipulation_tactics: string[];
    customer_exposure: string[];
    next_actions: string[];
  } | null;
  recommended_questions: QuestionCandidate[];
  unresolved_items: Array<{ target_field: string; description: string; priority: 'P0' | 'P1' | 'P2' }>;
  warnings: string[];
  source_revision: number | null;
  projection_revision: number | null;
  projection_status: 'CURRENT' | 'UPDATING' | 'STALE' | 'FAILED' | 'UNCACHED';
}

export type ProgressStep = 'SAFETY' | 'EVIDENCE' | 'PAYMENT_HOLD' | 'REPORT' | 'RELIEF';
export type ProgressStatus = 'UNKNOWN' | 'IN_PROGRESS' | 'SUBMITTED' | 'COMPLETED' | 'NOT_APPLICABLE';
export interface CustomerProgressItem {
  step: ProgressStep;
  label: string;
  status: ProgressStatus;
  status_label: string;
  summary: string;
  next_action: string;
  reference: string;
  confirmed_at: string | null;
  updated_at: string | null;
  updated_by: string | null;
  revision: number;
  confirmation_requested: boolean;
}
export interface UpdateCustomerProgress {
  expected_revision: number;
  status: ProgressStatus;
  summary: string;
  next_action: string;
  reference: string;
  confirmed_at: string | null;
  updated_by: string;
}

export interface AiInvocationResult {
  invocation_id: string;
  message_id: string;
  case_id: string;
  channel: 'TEAM' | 'AI_INTERNAL';
  content: string;
  model_mode: string;
  created_at: string;
}

export type WorkCardType = 'FACT_REVIEW' | 'QUESTION_PLAN' | 'VERIFICATION_REQUEST' | 'BANK_ACTION' | 'CUSTOMER_NOTICE' | 'CASE_TRANSITION';

export interface CaseWorkCard {
  card_type: WorkCardType;
  title: string;
  summary: string;
  context_sources: string[];
  rationale: string[];
  next_action: string;
  questions: QuestionCandidate[];
  suggested_claim?: string | null;
  suggested_target?: string | null;
  suggested_action_type?: string | null;
  suggested_action_note?: string | null;
  suggested_notice?: string | null;
  suggested_transition?: string | null;
  warnings: string[];
  model_mode: string;
}

export interface PersonalNote {
  note_id: string;
  case_id: string;
  author_id: string;
  content: string;
  visibility: 'PRIVATE_TO_AUTHOR';
  created_at: string;
  updated_at: string;
}

export type CaseMemberRole = 'CASE_OWNER' | 'CHAT_OPERATOR' | 'REVIEWER' | 'VIEWER';
export type PresenceState = 'VIEWING' | 'TYPING' | 'AWAY' | 'OFFLINE';

export interface CaseMember {
  case_id: string;
  user_id: string;
  display_name: string;
  role: CaseMemberRole;
  status: 'ACTIVE' | 'REMOVED';
  assigned_at: string;
  updated_at: string;
}

export interface CasePresence {
  case_id: string;
  user_id: string;
  display_name: string;
  presence: PresenceState;
  channel: MessageChannel;
  last_seen_at: string;
  expires_at: string;
}
