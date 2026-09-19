const pendingPrefix = 'csr-case-assignment-pending:';
const handledPrefix = 'csr-case-assignment-handled:';

const storage = (): Storage | null => {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
};

const key = (prefix: string, caseId: string) => `${prefix}${caseId}`;

export const shouldOpenInitialAssignment = (input: {
  hasPending: boolean;
  hasHandled: boolean;
  hasPrimaryAssignee: boolean;
  routeHint: boolean;
}) => !input.hasPrimaryAssignee && !input.hasHandled && (input.hasPending || input.routeHint);

/** Marks a newly created Case as waiting for its one-time initial assignment. */
export const markInitialAssignmentPending = (caseId: string) => {
  const store = storage();
  if (!store || !caseId) return;
  try {
    // An idempotent analysis response for an already-handled Case must not
    // resurrect its one-time prompt.
    if (store.getItem(key(handledPrefix, caseId)) === '1') return;
    store.setItem(key(pendingPrefix, caseId), '1');
  } catch {
    // Browser storage can be unavailable in privacy-restricted contexts.
  }
};

export const hasInitialAssignmentPending = (caseId: string) => {
  const store = storage();
  if (!store || !caseId) return false;
  try {
    return store.getItem(key(pendingPrefix, caseId)) === '1' && store.getItem(key(handledPrefix, caseId)) !== '1';
  } catch {
    return false;
  }
};

export const hasInitialAssignmentHandled = (caseId: string) => {
  const store = storage();
  if (!store || !caseId) return false;
  try {
    return store.getItem(key(handledPrefix, caseId)) === '1';
  } catch {
    return false;
  }
};

/** Marks the initial prompt as handled after save or explicit skip. */
export const markInitialAssignmentHandled = (caseId: string) => {
  const store = storage();
  if (!store || !caseId) return;
  try {
    store.removeItem(key(pendingPrefix, caseId));
    store.setItem(key(handledPrefix, caseId), '1');
  } catch {
    // Browser storage can be unavailable in privacy-restricted contexts.
  }
};
