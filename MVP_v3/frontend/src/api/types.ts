export type RiskLevel = 'NORMAL' | 'LOW' | 'HIGH';
export type CaseMode = 'PREVENT' | 'RECOVERY' | 'CLOSED';
export type CaseStatus = 'NEW' | 'TRIAGE' | 'VERIFYING' | 'IN_PROGRESS' | 'CLOSED';
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

export interface SemanticAtom {
  atom_id: string;
  atom_class: string;
  speaker?: string;
  subject?: string | null;
  predicate: string;
  actor?: string | null;
  target?: string | null;
  object?: string | null;
  destination?: string | null;
  action_state?: string | null;
  modality?: string | null;
  polarity?: string;
  claim_status: string;
  lexical_cues?: string[];
  speech_form_codes?: string[];
  speech_act?: string | null;
  directive_strength?: string | null;
  obligation?: string | null;
  urgency?: string | null;
  authority_pressure?: string | null;
  fear_pressure?: string | null;
  secrecy_pressure?: string | null;
  isolation_pressure?: string | null;
  financial_pressure?: string | null;
  repetition_pressure?: string | null;
  threat_type?: string | null;
  communication_control?: string | null;
  auth_secret_type?: string | null;
  amount_scope?: string | null;
  amount_value_krw?: number | null;
  amount_role?: string | null;
  amount_direction?: string | null;
  amount_event_id?: string | null;
  claimed_organization?: string | null;
  claimed_organization_name?: string | null;
  claimed_branch_name?: string | null;
  claimed_person_name?: string | null;
  claimed_role?: string | null;
  claimed_role_name?: string | null;
  claimed_relationship?: string | null;
  claimed_purpose?: string | null;
  speaker_role?: AnalysisActorRole | null;
  actor_role?: AnalysisActorRole | null;
  target_role?: AnalysisActorRole | null;
  reported_by_role?: AnalysisActorRole | null;
  speaker_confidence?: number | null;
  attribution_confidence?: number | null;
  vocative_target?: string | null;
  deadline_at?: string | null;
  relative_deadline_minutes?: number | null;
  mention_order?: number | null;
  occurrence_count?: number;
  observed_terms?: Array<{
    surface_form?: string;
    normalized_code?: string;
    semantic_value?: string | null;
    term_type?: string;
    confidence?: number;
  }>;
  source_turn_id: number;
}

export interface UnmappedObservation {
  observation_id: string;
  observation_type: string;
  candidate_categories: string[];
  lexical_codes: string[];
  observed_terms: Array<{
    surface_form?: string;
    normalized_code?: string;
    semantic_value?: string | null;
    term_type?: string;
    confidence?: number;
  }>;
  speech_act?: string | null;
  action_state?: string | null;
  polarity?: string;
  modality?: string | null;
  amount_role?: string | null;
  amount_value_krw?: number | null;
  source_turn_id: number;
  source_event_id?: string | null;
  confidence: number;
  status: string;
}

export type AnalysisActorRole = 'SUSPECTED_PARTY' | 'CUSTOMER' | 'BANK_STAFF' | 'SYSTEM' | 'UNKNOWN';

export interface SemanticMention {
  mention_id: string;
  normalized_code: string;
  normalized_value: string;
  mention_type: string;
  source_turn_id: number;
  sequence_index: number;
  speaker_role: AnalysisActorRole;
  occurrence_count: number;
  first_turn_id: number;
  last_turn_id: number;
  confidence: number;
}

export interface SemanticRelation {
  relation_id: string;
  relation_type: string;
  source_atom_id: string;
  target_atom_id: string;
  confidence: number;
}

export interface ContextSignal {
  signal_id: string;
  signal_code: string;
  severity: string;
  confidence: number;
  claim_status: string;
  atom_ids: string[];
}

export interface FeatureNarrative {
  code: string;
  sentence: string;
  status: 'CLAIMED' | 'REQUESTED' | 'REPORTED' | 'DENIED';
  source_turns: number[];
  atom_ids: string[];
  speaker_role?: AnalysisActorRole;
  actor_role?: AnalysisActorRole;
  target_role?: AnalysisActorRole;
  reported_by_role?: AnalysisActorRole;
  detail_items?: string[];
  entity_names?: string[];
  deadline_at?: string | null;
  relative_deadline_minutes?: number | null;
  occurrence_count?: number;
  confidence?: number | null;
}

export interface StructuredContextProjection {
  source_revision: number;
  atoms: SemanticAtom[];
  relations: SemanticRelation[];
  signals: ContextSignal[];
  feature_codes: Record<string, string[]>;
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
  summary_source_revision?: number | null;
  current_context_revision?: number | null;
  is_stale?: boolean | null;
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

/**
 * Case bundle에서 고객·은행·검증 화면이 공통으로 사용하는 안전한 요약 계약입니다.
 * 진단 원문이나 내부 분석 payload는 포함하지 않습니다.
 */
export interface CaseSummary {
  case_id: string;
  version: number;
  case_name: string | null;
  context_revision: number;
  risk: RiskLevel;
  mode: CaseMode;
  status: CaseStatus;
  initial_brief: string;
  primary_assignee: string | null;
  victim_transfer_status: 'UNKNOWN' | 'YES' | 'NO';
  actual_loss_amount_krw: number | null;
  created_at: string;
  updated_at: string;
}

/**
 * Case read 응답의 진단 payload입니다.
 * CaseSummary와 분리해, 요약 화면이 내부 분석 구조에 의존하지 않도록 합니다.
 */
export interface CaseDiagnosis {
  context?: {
    summary?: string;
    incident_type?: string;
    claims?: string[];
    demands?: string[];
    manipulation_tactics?: string[];
    customer_statements?: string[];
    recommended_next_steps?: string[];
    confidence?: number;
    feature_narratives?: FeatureNarrative[];
  };
  events?: DiagnosisEvent[];
  evidence?: DiagnosisEvidence[];
  windows?: DiagnosisWindow[];
  features?: Record<string, number>;
  semantic_atoms?: SemanticAtom[];
  semantic_mentions?: SemanticMention[];
  unmapped_observations?: UnmappedObservation[];
  semantic_relations?: SemanticRelation[];
  context_signals?: ContextSignal[];
  conversation_episodes?: Array<{ episode_id: string; start_turn: number; end_turn: number; atom_ids: string[]; episode_type: string }>;
  action_groups?: Array<{ group_id: string; action_predicate: string; atom_ids: string[]; action_states: string[]; target_codes: string[] }>;
  entity_registry?: Array<{ entity_id: string; entity_code: string; mention_roles: string[]; atom_ids: string[]; source_turn_ids: number[] }>;
  case_context_features?: {
    claimed_actor_types: string[]; claim_codes: string[]; requested_action_codes: string[];
    manipulation_tactic_codes: string[]; exposure_risk_codes: string[];
    amount_values_krw: number[]; requested_amount_values_krw?: number[]; chronology: string[]; unknown_fields: string[];
    observations?: Array<{ code: string; turn: number; status: string }>;
  };
  warnings?: string[];
}

export interface StoredCase {
  case_id: string;
  version: number;
  case_name?: string | null;
  risk: RiskLevel;
  risk_score: number;
  mode: 'PREVENT' | 'RECOVERY' | 'CLOSED';
  status: string;
  initial_brief: string;
  primary_assignee?: string | null;
  victim_transfer_status?: 'UNKNOWN' | 'YES' | 'NO';
  actual_loss_amount_krw?: number | null;
  diagnosis: CaseDiagnosis;
  initial_report?: InitialReport | null;
  created_at: string;
  updated_at: string;
  deleted_at?: string | null;
  trash_expires_at?: string | null;
}

export interface CaseTransaction {
  id: number;
  case_id: string;
  transaction_type: 'TRANSFER_OUT' | 'RETURN_IN' | 'CANCELLED';
  transaction_at: string;
  /** KRW integer; fractional amounts are not part of the public contract. */
  amount: number;
  account_number?: string | null;
  counterparty_name?: string | null;
  counterparty_account?: string | null;
  bank_name?: string | null;
  memo?: string | null;
  source: string;
  created_at: string;
  updated_at: string;
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

/**
 * Case bundle에 포함되는 통화 세션 metadata입니다.
 * 원문 transcript를 포함하지 않으며, 현재 화면에서는 직접 표시하지 않습니다.
 */
export interface VoiceSession {
  session_id: string;
  case_id: string;
  status: 'REQUESTED' | 'ACTIVE' | 'ENDED' | 'FAILED';
  participants: string[];
  started_at: string | null;
  ended_at: string | null;
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
  /** Structured next actions returned with the latest internal AI response. */
  recommended_actions?: RecommendedChatAction[];
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
  title?: string | null;
  note: string;
  version?: number;
  visibility?: 'BANK_INTERNAL' | 'CUSTOMER_SHARED';
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
  allow_multi_select?: boolean;
  option_items?: QuestionOption[];
}

export interface QuestionOption { option_id: string; label: string }
export interface StructuredQuestionAnswer { selected_option_ids: string[]; free_text?: string | null; question_version: number }

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
  question_version?: number;
  answer_payload?: { selected_option_ids: string[]; selected_option_labels?: string[]; free_text?: string | null } | null;
  answer_question_version?: number | null;
}

export interface CustomerVerificationResult {
  verification_task_id: string;
  target: string;
  result_summary: string;
  published_at?: string | null;
}

export interface CaseBundle {
  customer_progress?: CustomerProgressItem[];
  case: CaseSummary;
  /** Initial/live analysis snapshot. It is typed for contract parity only; the UI does not render it directly. */
  live_report?: InitialReport | null;
  final_report?: InitialReport | null;
  /** Session metadata only; transcript storage and transcript APIs are disabled. */
  voice_session?: VoiceSession | null;
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
  recommended_actions?: RecommendedChatAction[];
}

export type RecommendedActionKey =
  | 'CUSTOMER_QUESTION'
  | 'TRANSACTION_LOOKUP'
  | 'OFFICIAL_VERIFICATION'
  | 'RESPONSE_ACTION'
  | 'DRAFT_REPLY';

export interface RecommendedChatAction {
  action_key: RecommendedActionKey;
  kind: 'TOOL' | 'REPLY_DRAFT';
  target_channel: 'TEAM' | 'CUSTOMER';
  draft_text?: string | null;
  reason_code?: string | null;
}

export type WorkCardType = 'FACT_REVIEW' | 'QUESTION_PLAN' | 'VERIFICATION_REQUEST' | 'BANK_ACTION' | 'CUSTOMER_NOTICE' | 'CASE_TRANSITION';

export interface VerificationMessageDraft {
  institution: string;
  target: string;
  claim: string;
  message: string;
  reason_codes: string[];
}

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
  verification_messages?: VerificationMessageDraft[];
  suggested_action_type?: string | null;
  suggested_action_note?: string | null;
  suggested_actions?: SuggestedResponseAction[];
  suggested_notice?: string | null;
  suggested_transition?: string | null;
  warnings: string[];
  model_mode: string;
}

export interface SuggestedResponseAction {
  dedupe_key: string;
  category: string;
  priority: 'P0' | 'P1' | 'P2';
  title: string;
  note: string;
  reason_codes: string[];
  steps?: SuggestedResponseStep[];
}

export interface SuggestedResponseStep {
  dedupe_key: string;
  title: string;
  note: string;
  reason_codes: string[];
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

export type CaseAssignmentRole = 'SUPERVISOR' | 'MONITORING' | 'CONSULTATION' | 'VIEWER' | 'HANDOVER_PENDING';
export type PresenceState = 'VIEWING' | 'TYPING' | 'AWAY' | 'OFFLINE';

export interface CaseMember {
  case_id: string;
  user_id: string;
  display_name: string;
  assignment_role: CaseAssignmentRole;
  status: 'ACTIVE' | 'REMOVED';
  assigned_at: string;
  updated_at: string;
}

/** API staff colors are GREEN~GRAY. BLACK is a synthetic local color for the demo/test user only. */
export type BankStaffColor = 'GREEN' | 'BLUE' | 'YELLOW' | 'ORANGE' | 'RED' | 'PURPLE' | 'GRAY' | 'BLACK';
/** Directory role OTHER_VIEWER is mapped to Case-member role VIEWER by the General API. */
export type BankStaffAssignmentRole = 'SUPERVISOR' | 'MONITORING' | 'CONSULTATION' | 'OTHER_VIEWER' | 'HANDOVER_PENDING';
export interface BankStaff {
  staff_id: string;
  display_name: string;
  assignment_role: BankStaffAssignmentRole;
  role_label: string;
  position_title?: string | null;
  status_text: string;
  status_color_key: BankStaffColor;
  assignment_eligible: boolean;
  linked_user_id?: string | null;
  is_self: boolean;
  created_at: string;
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
