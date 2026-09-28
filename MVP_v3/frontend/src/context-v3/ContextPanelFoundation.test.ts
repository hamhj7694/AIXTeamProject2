import { describe, expect, it } from 'vitest';
import type { RightPanelProjection } from '../api/types';
import { rightPanelPresentation } from './ContextPanelFoundation';

describe('right panel presentation projection', () => {
  it('renders only presentation-ready summary and signals from the read model', () => {
    const signal = {
      key: 'demand', label: '요구 행동', items: [{
        item_id: 'signal-1', section: 'SIGNAL' as const, semantic_key: 'demand:one',
        title: '개인정보 제공 요구', detail: '', source_badge: '상대방 요구' as const,
        origin: 'AI_ANALYSIS' as const, status: null, occurred_at: null,
        evidence_refs: ['atom-1'], actor_id: null, version: null,
      }],
    };
    const projection = {
      schema_version: 'right-panel.v1', current_case_summary: '상대방이 개인정보 제공을 요구했습니다.',
      exposure: [], contact_information: [], fraud_signals: [signal], verification: [],
      incomplete_work: [], completed_work: [], activity: [], source_revision: 1,
    } satisfies RightPanelProjection;

    expect(rightPanelPresentation(projection)).toEqual({
      summary: '상대방이 개인정보 제공을 요구했습니다.', fraudSignals: [signal],
    });
  });

  it('does not infer facts from legacy diagnosis or case text when projection is absent', () => {
    expect(rightPanelPresentation(null)).toEqual({
      summary: '현재 확인된 사건 요약이 없습니다.', fraudSignals: [],
    });
  });
});
