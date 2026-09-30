import { describe, expect, it } from 'vitest';
import type { CaseBundle, CustomerUiAction } from '../api/types';
import { isCurrentCustomerUiAction } from './customerActions';

const bundle = (overrides: Partial<CaseBundle> = {}) => ({
  case: { case_id: 'CASE-1', mode: 'PREVENT', victim_transfer_status: 'NO' },
  questions: [
    { question_id: 'asked-1', status: 'ASKED' },
    { question_id: 'answered-1', status: 'ANSWERED' },
  ],
  ...overrides,
} as CaseBundle);

describe('customer AI navigation actions', () => {
  it('accepts only a question that is still awaiting an answer', () => {
    const valid: CustomerUiAction = { action_key: 'OPEN_ACTIVE_QUESTION', target_id: 'asked-1' };
    const stale: CustomerUiAction = { action_key: 'OPEN_ACTIVE_QUESTION', target_id: 'answered-1' };

    expect(isCurrentCustomerUiAction(bundle(), valid)).toBe(true);
    expect(isCurrentCustomerUiAction(bundle(), stale)).toBe(false);
    expect(isCurrentCustomerUiAction(bundle({ questions: [] }), valid)).toBe(false);
  });

  it('opens the recovery guide only while the public recovery mode is active', () => {
    const action: CustomerUiAction = { action_key: 'OPEN_RECOVERY_GUIDE' };

    expect(isCurrentCustomerUiAction(bundle(), action)).toBe(false);
    expect(isCurrentCustomerUiAction(bundle({ case: { case_id: 'CASE-1', mode: 'RECOVERY' } as CaseBundle['case'] }), action)).toBe(true);
    expect(isCurrentCustomerUiAction(bundle({ case: { case_id: 'CASE-1', victim_transfer_status: 'YES' } as CaseBundle['case'] }), action)).toBe(true);
  });
});
