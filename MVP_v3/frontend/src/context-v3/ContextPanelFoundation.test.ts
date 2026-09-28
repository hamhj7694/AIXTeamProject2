import { describe, expect, it } from 'vitest';
import type { CaseSupportSnapshot, StoredCase } from '../api/types';
import { buildBriefCategories, orderByConversationTurn, summarizePanelHeadline } from './ContextPanelFoundation';

const baseCase = (overrides: Partial<StoredCase> = {}): StoredCase => ({
  case_id: 'VP-TEST',
  version: 1,
  case_name: null,
  risk: 'HIGH',
  risk_score: 80,
  mode: 'PREVENT',
  status: 'OPEN',
  analysis_status: 'COMPLETED',
  initial_brief: '사건 요약',
  primary_assignee: null,
  victim_transfer_status: 'UNKNOWN',
  actual_loss_amount_krw: null,
  created_at: '2026-09-28T00:00:00Z',
  updated_at: '2026-09-28T00:00:00Z',
  diagnosis: { context: { claims: ['카드사라고 주장함'], demands: ['안전계좌 송금을 요구함'], customer_statements: ['인증정보 제공 여부는 확인되지 않음'] } },
  ...overrides,
});

describe('right panel brief model', () => {
  it('renders the current summary as a readable situation paragraph', () => {
    const result = summarizePanelHeadline('사건: 카드사 사칭 · 안전계좌 송금 요구\n고객 상태: 송금 여부 확인 필요\n다음으로: 거래 기록 확인 필요');

    expect(result).toBe('카드사 사칭. 안전계좌 송금 요구. 현재 고객 상태는 송금 여부 확인 필요. 다음으로 거래 기록 확인 필요.');
    expect(result).not.toContain('…');
  });

  it('removes normalized duplicates and preserves source turn order', () => {
    const result = orderByConversationTurn(
      ['카드사라고 주장함.', '카드사라고 주장함', '안전계좌 송금을 요구함'],
      [
        { sentence: '안전계좌 송금을 요구함.', source_turns: [8] },
        { sentence: '카드사라고 주장함.', source_turns: [3] },
      ],
    );

    expect(result.map((item) => item.text)).toEqual(['카드사라고 주장함', '안전계좌 송금 요구']);
    expect(result.map((item) => item.turn)).toEqual([3, 8]);
  });

  it('falls back to diagnosis when support context arrays are empty', () => {
    const support = {
      case_id: 'VP-TEST',
      available: true,
      case_brief: null,
      case_context: {
        situation_summary: '', key_signals: [], offender_claims: [], offender_demands: [], manipulation_tactics: [], customer_exposure: [], next_actions: [],
      },
      recommended_questions: [], unresolved_items: [], warnings: [], source_revision: 1, projection_revision: 1, projection_status: 'CURRENT',
    } satisfies CaseSupportSnapshot;

    const categories = buildBriefCategories(baseCase(), support);
    expect(categories.find((category) => category.key === 'identity')?.entries.map((entry) => entry.text)).toEqual(['카드사라고 주장함']);
    expect(categories.find((category) => category.key === 'demand')?.entries.map((entry) => entry.text)).toEqual(['안전계좌 송금 요구']);
    expect(categories.find((category) => category.key === 'exposure')?.entries.map((entry) => entry.text)).toEqual(['인증정보 제공 여부는 확인되지 않음']);
  });
});
