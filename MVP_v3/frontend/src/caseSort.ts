import type { StoredCase } from './api/types';

export type CaseSortField = 'CASE_ID' | 'CREATED_AT' | 'UPDATED_AT';
export type SortDirection = 'ASC' | 'DESC';

const safeTimestamp = (value: string | undefined) => {
  const timestamp = Date.parse(value ?? '');
  return Number.isFinite(timestamp) ? timestamp : 0;
};

export const compareCases = (
  left: StoredCase,
  right: StoredCase,
  field: CaseSortField,
  direction: SortDirection,
) => {
  let result = 0;
  if (field === 'CASE_ID') {
    result = left.case_id.localeCompare(right.case_id, 'ko', { numeric: true, sensitivity: 'base' });
  } else if (field === 'CREATED_AT') {
    result = safeTimestamp(left.created_at) - safeTimestamp(right.created_at);
  } else {
    result = safeTimestamp(left.updated_at || left.created_at) - safeTimestamp(right.updated_at || right.created_at);
  }
  if (result === 0) result = left.case_id.localeCompare(right.case_id, 'ko', { numeric: true, sensitivity: 'base' });
  return direction === 'ASC' ? result : -result;
};
