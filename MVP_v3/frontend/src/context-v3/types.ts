import type { StructuredContextProjection } from '../api/types';

export type ContextPanelItemV3 = {
  item_id: string;
  semantic_key: string;
  label: string;
  display_value: string;
  value: Record<string, unknown>;
  source_kind: string;
  status: string;
  confidence?: number | null;
  evidence_refs: { type: string; id: string; revision?: number | null; summary?: string | null }[];
  visibility: 'BANK_INTERNAL' | 'CUSTOMER_SHARED';
  masked: boolean;
  version: number;
};

export type ContextPanelSectionV3 = {
  section_id: 'SUMMARY' | 'EXPOSURE' | 'IMPERSONATION_CONTACT' | 'FRAUD_CIRCUMSTANCES' | 'FACT_VERIFICATION' | 'STAFF_ACTIONS' | 'CUSTOMER_SHARE';
  title: string;
  items: ContextPanelItemV3[];
  groups: Record<string, ContextPanelItemV3[]>;
};

export type ContextPanelV3 = {
  schema_version: 'context-panel.v3';
  case_id: string;
  view: 'bank' | 'customer';
  source_revision: number;
  projection_status: 'CURRENT' | 'UPDATING' | 'STALE' | 'FAILED' | 'UNCACHED';
  generated_by: 'DETERMINISTIC_FALLBACK' | 'LAST_SUCCESS' | 'LLM';
  updated_at: string | null;
  structured_context?: StructuredContextProjection | null;
  sections: ContextPanelSectionV3[];
};

