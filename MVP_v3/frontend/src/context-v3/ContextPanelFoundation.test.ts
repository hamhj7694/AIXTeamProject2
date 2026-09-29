import { describe, expect, it } from 'vitest';
import type { RightPanelProjection } from '../api/types';
import { groupExposureRows, RIGHT_PANEL_ADD_CHOICES, RIGHT_PANEL_TOP_LEVEL_LABELS, rightPanelPresentation } from './ContextPanelFoundation';
import { summarizeTransferAmounts } from './sections';

describe('right panel presentation projection', () => {
  it('includes recorded additional transfers in the displayed total without requiring confirmation', () => {
    const makeTransfer = (id: string, amount: number, sourceId: string) => ({
      item_id: id, semantic_key: 'transfer.actual.amount', label: '실제 송금',
      display_value: `${amount.toLocaleString('ko-KR')}원 송금`,
      value: { amount_krw: amount, direction: 'OUT', amount_scope: 'EVENT' },
      source_kind: 'CUSTOMER_STATEMENT', status: 'PROPOSED', evidence_refs: [{ type: 'MESSAGE', id: sourceId }],
      visibility: 'BANK_INTERNAL' as const, masked: false, version: 1,
    });
    const result = summarizeTransferAmounts([
      makeTransfer('first', 5_000_000, 'message-1'),
      makeTransfer('additional', 2_000_000, 'message-2'),
      makeTransfer('same-message-retry', 2_000_000, 'message-2'),
    ]);
    expect(result.sent).toEqual({ count: 2, total: 7_000_000 });
  });

  it('assigns add targets to middle groups rather than top-level sections', () => {
    expect(Object.keys(RIGHT_PANEL_ADD_CHOICES)).toEqual(['exposure', 'progress', 'fraud']);
    for (const choices of Object.values(RIGHT_PANEL_ADD_CHOICES)) {
      expect(new Set(choices.map(({ id }) => id)).size).toBe(choices.length);
    }
    expect(RIGHT_PANEL_ADD_CHOICES.exposure.map(({ section, groupKey }) => [section, groupKey])).toEqual([
      ['EXPOSURE', 'other'], ['EXPOSURE', 'personal_information'], ['EXPOSURE', 'authentication_information'],
      ['EXPOSURE', 'device_access'], ['SIGNAL', 'money'],
    ]);
    expect(RIGHT_PANEL_ADD_CHOICES.progress.map(({ section }) => section)).toEqual(['WORK', 'VERIFICATION']);
    expect(RIGHT_PANEL_ADD_CHOICES.fraud.map(({ section }) => section)).toContain('CONTACT');
    expect(RIGHT_PANEL_ADD_CHOICES.fraud.map(({ section }) => section)).toContain('SIGNAL');
    expect(new Set(RIGHT_PANEL_ADD_CHOICES.fraud.map(({ groupKey }) => groupKey))).toEqual(new Set(['identity', 'claim', 'demand', 'pressure']));
  });

  it('maps source categories to the four stable sections without text inference', () => {
    const makeSignal = (key: string, title: string, presentation_group?: RightPanelProjection['exposure'][number]['presentation_group']) => ({ key, label: key, items: [{
      item_id: `signal-${key}`, section: 'SIGNAL' as const, semantic_key: `${key}:one`,
      title, detail: '', source_badge: '상대방 요구' as const,
      origin: 'AI_ANALYSIS' as const, status: null, occurred_at: null,
      evidence_refs: ['atom-1'], actor_id: null, version: null, presentation_group,
    }] });
    const signals = [
      makeSignal('identity', '서울중앙지검을 사칭'), makeSignal('claim', '사건에 연루됐다고 주장'),
      makeSignal('demand', '개인정보 제공 요구'), makeSignal('pressure', '외부 연락 금지'),
      makeSignal('money', '송금 요구 정황', 'money'), makeSignal('exposure', '인증정보 노출 정황', 'authentication_information'),
    ];
    const projection = {
      schema_version: 'right-panel.v1', current_case_summary: '상대방이 개인정보 제공을 요구했습니다.',
      summary_badges: [{ key: 'transfer', label: '송금 미확인', tone: 'unknown' }],
      exposure: [], contact_information: [], fraud_signals: signals, verification: [],
      incomplete_work: [], completed_work: [], activity: [], source_revision: 1,
    } satisfies RightPanelProjection;

    const presentation = rightPanelPresentation(projection);
    expect(presentation.summary).toBe('상대방이 개인정보 제공을 요구했습니다.');
    expect(presentation.summaryBadges).toEqual(projection.summary_badges);
    expect(RIGHT_PANEL_TOP_LEVEL_LABELS).toEqual([
      '현재 사건 요약', '1. 피해·노출', '2. 확인·조치 진행', '3. 주요 사기 정황', '4. 처리 기록',
    ]);
    expect(presentation.fraudGroups.map(({ key, label }) => [key, label])).toEqual([
      ['identity', '사칭·접촉'], ['claim', '사건·상황 주장'], ['demand', '요구·행동'], ['pressure', '압박·연락 통제'],
    ]);
    expect(presentation.fraudGroups.map((group) => group.items[0]?.title)).toEqual([
      '서울중앙지검을 사칭', '사건에 연루됐다고 주장', '개인정보 제공 요구', '외부 연락 금지',
    ]);
    expect(presentation.exposureSignalGroups.map(({ key, label, items }) => [key, label, items[0]?.title])).toEqual([
      ['money', '금전', '송금 요구 정황'], ['personal_information', '개인정보', undefined],
      ['authentication_information', '인증정보', '인증정보 노출 정황'], ['device_access', '기기·접근', undefined],
      ['other', '기타 피해·노출', undefined],
    ]);
  });

  it('keeps rows without group metadata visible as unclassified instead of guessing 기타', () => {
    const row = {
      item_id: 'missing-group', section: 'EXPOSURE' as const, semantic_key: 'unknown:auth',
      title: '인증정보 제공 요구', detail: 'legacy server row', source_badge: '상대방 요구' as const,
      origin: 'AI_ANALYSIS' as const, status: null, occurred_at: null,
      evidence_refs: [], actor_id: null, version: null,
    };
    const grouped = groupExposureRows([row]);
    expect(grouped.groups.other).toEqual([]);
    expect(grouped.groups.authentication_information).toEqual([]);
    expect(grouped.unclassified).toEqual([row]);
  });

  it('keeps the six exposure rows in their semantic groups and leaves 기타 empty', () => {
    const rows = [
      ['money', 'transfer-request'], ['money', 'transfer-status'],
      ['personal_information', 'personal-status'],
      ['authentication_information', 'otp-request'], ['authentication_information', 'otp-status'],
      ['device_access', 'remote-app-status'],
    ].map(([presentation_group, semantic_key]) => ({
      item_id: semantic_key, section: 'EXPOSURE' as const, semantic_key,
      title: semantic_key, detail: '', source_badge: null, origin: 'AI_ANALYSIS' as const,
      status: null, occurred_at: null, evidence_refs: [], actor_id: null, version: null,
      presentation_group: presentation_group as RightPanelProjection['exposure'][number]['presentation_group'],
    }));
    const grouped = groupExposureRows(rows);
    expect(grouped.groups.money).toHaveLength(2);
    expect(grouped.groups.personal_information).toHaveLength(1);
    expect(grouped.groups.authentication_information).toHaveLength(2);
    expect(grouped.groups.device_access).toHaveLength(1);
    expect(grouped.groups.other).toHaveLength(0);
    expect(grouped.unclassified).toHaveLength(0);
  });

  it('does not infer facts from legacy diagnosis or case text when projection is absent', () => {
    const presentation = rightPanelPresentation(null);
    expect(presentation.summary).toBe('현재 확인된 사건 요약이 없습니다.');
    expect(presentation.summaryBadges).toEqual([]);
    expect(presentation.fraudGroups.every((group) => group.items.length === 0)).toBe(true);
    expect(presentation.exposureSignalGroups.every((group) => group.items.length === 0)).toBe(true);
  });
});
