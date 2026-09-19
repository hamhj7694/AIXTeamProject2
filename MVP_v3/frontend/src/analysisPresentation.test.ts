import { describe, expect, it } from 'vitest';
import {
  analysisCodeLabel,
  analysisConcreteLabel,
  analysisRoleLabel,
  attributionWarning,
  observedTermLabel,
  replaceAnalysisTokens,
} from './analysisPresentation';

describe('analysis presentation labels', () => {
  it('renders envelope predicates and enum values in Korean', () => {
    expect(analysisCodeLabel('claims organization')).toBe('기관·소속 사칭 주장');
    expect(analysisCodeLabel('TRANSFER_FUNDS')).toBe('자금 이체 요구');
    expect(analysisConcreteLabel('CARD_COMPANY')).toBe('카드사');
    expect(analysisConcreteLabel('CLAIMED_SAFE_ACCOUNT')).toBe('상대방이 제시한 안전계좌');
    expect(analysisConcreteLabel('SECURITY_CODE')).toBe('인증번호');
    expect(analysisConcreteLabel('IMMEDIATE')).toBe('즉시');
  });

  it('never exposes an unknown internal identifier as staff copy', () => {
    expect(analysisCodeLabel('NEW_INTERNAL_PREDICATE')).toBe('분류 확인 필요');
    expect(analysisConcreteLabel('NEW_INTERNAL_VALUE')).toBe('확인 필요');
    expect(replaceAnalysisTokens('CARD_COMPANY · NEW_INTERNAL_VALUE')).toBe('카드사 · 분류 확인 필요');
  });

  it('preserves concrete names while preferring grounded Korean surface forms', () => {
    expect(analysisConcreteLabel('서울중앙지검')).toBe('서울중앙지검');
    expect(analysisConcreteLabel('김민수')).toBe('김민수');
    expect(observedTermLabel({ semantic_value: 'CARD_COMPANY', surface_form: 'OO카드' })).toBe('OO카드');
  });

  it('keeps unknown roles unknown and flags contradictory customer attribution', () => {
    expect(analysisRoleLabel('UNKNOWN')).toBe('화자 미상 · 확인 필요');
    expect(attributionWarning('TRANSFER_FUNDS', 'CUSTOMER', 'UNVERIFIED')).toBe('역할 귀속 충돌 · 확인 필요');
    expect(attributionWarning('TRANSFER_FUNDS', 'CUSTOMER', 'CUSTOMER_REPORTED')).toBeNull();
    expect(attributionWarning('REQUEST_AUTH_INFO', 'CUSTOMER', 'REQUESTED')).toBe('역할 귀속 충돌 · 확인 필요');
  });
});
