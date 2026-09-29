import { describe, expect, it } from 'vitest';
import { buildInitialSummary, compactInitialSummaryLine } from './analysisInitialSummary';

describe('analysis initial summary display model', () => {
  it('removes repeated subjects without changing claim uncertainty', () => {
    expect(compactInitialSummaryLine('보이스피싱 의심 인물이 카드사라고 주장함')).toBe('카드사라고 주장함');
    expect(compactInitialSummaryLine('고객이 통화 중 질문함', 'customer')).toBe('통화 중 질문함');
    expect(compactInitialSummaryLine('고객이 실제 인증번호 제공 여부는 확인되지 않음', 'customer')).toBe('실제 인증번호 제공 여부는 확인되지 않음');
  });

  it('deduplicates punctuation-only duplicates and caps visible items at three', () => {
    const model = buildInitialSummary({
      summary: '카드사 사칭 정황이 있음.',
      claims: ['보이스피싱 의심 인물이 카드사라고 주장함.', '상대방이 카드사라고 주장함'],
      demands: ['고객에게 안전계좌로 송금하도록 요구함', '고객에게 안전계좌로 송금하도록 요구함.'],
      manipulation_tactics: ['즉시 처리 요구', '외부 연락 차단', '불안감 조성', '추가 정황'],
      customer_statements: [],
    }, {
      sections: [{ section_key: 'unresolved_items', content: { items: ['실제 송금 여부', '개인정보·인증정보 노출 여부', '상대방 주장 진위'] } }],
    } as never);

    expect(model.sections.find((item) => item.key === 'claims')?.items).toEqual(['카드사라고 주장함']);
    expect(model.sections.find((item) => item.key === 'demands')?.items).toEqual(['안전계좌로 송금 요구']);
    expect(model.sections.find((item) => item.key === 'tactics')?.hiddenCount).toBe(1);
    expect(model.sections.find((item) => item.key === 'unresolved')?.items).toEqual([
      '실제 송금 여부', '개인정보·인증정보 노출 여부', '상대방 주장 진위',
    ]);
  });

  it('merges structured fallback items when a context category is empty', () => {
    const model = buildInitialSummary({ summary: '사건 요약', claims: [] }, undefined, {
      demands: ['안전계좌 송금 요구'],
      tactics: ['즉시 처리 압박'],
      customer: ['통화 중 질문함'],
    });
    expect(model.sections.map((item) => item.key)).toEqual(['demands', 'tactics', 'customer']);
  });

  it('keeps one representative for semantically repeated claims and demands', () => {
    const model = buildInitialSummary({
      summary: 'case',
      claims: [
        '자신을 카드사 보안센터 소속인 것처럼 주장함',
        '자신이 카드사 보안센터 소속인 것처럼 주장함',
        '고객 계정에 승인되지 않은 결제가 있었다고 주장함. 해당 결제 발생 여부는 확인되지 않음',
        '고객 계정에 승인되지 않은 결제가 발생했다고 주장함. 실제 결제 발생 여부와 승인 상태는 확인되지 않음',
      ],
      demands: [
        '인증번호, 즉 OTP를 제공 요구',
        '인증번호를 즉시 제공 요구',
        '인증번호, 즉 일회용 인증번호(일회용 인증번호(일회용 인증번호(OTP)))를 제공 요구',
        '외부 계좌로 즉시 송금하도록 요구함',
        '자금 이체 또는 송금 요구',
      ],
      manipulation_tactics: [],
      customer_statements: [],
    });

    expect(model.sections.find((item) => item.key === 'claims')?.items).toHaveLength(2);
    expect(model.sections.find((item) => item.key === 'demands')?.items).toHaveLength(2);
    expect(model.sections.find((item) => item.key === 'demands')?.items.join(' ')).not.toContain('인증번호(인증번호(');
  });

  it('does not merge customer questions with whether the action was completed', () => {
    const model = buildInitialSummary({
      summary: 'case', claims: [], demands: [], manipulation_tactics: [],
      customer_statements: [
        '통화 중 인증번호와 관련된 질문을 한 정황이 있음',
        '인증번호 제공 또는 송금이 실제로 완료됐다는 고객 진술은 없음',
      ],
    });
    expect(model.sections.find((item) => item.key === 'customer')?.items).toHaveLength(2);
  });
});
