import type { CaseBundle, CustomerUiAction } from '../api/types';

export const isCurrentCustomerUiAction = (bundle: CaseBundle, action: CustomerUiAction): boolean => {
  if (action.action_key === 'OPEN_ACTIVE_QUESTION') {
    return bundle.questions.some((question) => question.question_id === action.target_id && question.status === 'ASKED');
  }
  return String(bundle.case.mode ?? '') === 'RECOVERY' || String(bundle.case.victim_transfer_status ?? '') === 'YES';
};
