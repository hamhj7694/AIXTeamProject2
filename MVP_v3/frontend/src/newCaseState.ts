const prefix = 'csr-new-case:';
const eventName = 'csr:new-case-state-changed';
const storage = (): Storage | null => typeof window === 'undefined' ? null : window.localStorage;
export const markNewCase = (caseId: string) => { const store = storage(); if (!store || !caseId) return; store.setItem(`${prefix}${caseId}`, '1'); window.dispatchEvent(new Event(eventName)); };
export const markCaseOpened = (caseId: string) => { const store = storage(); if (!store || !caseId) return; store.removeItem(`${prefix}${caseId}`); window.dispatchEvent(new Event(eventName)); };
export const isNewCase = (caseId: string) => { const store = storage(); return Boolean(store?.getItem(`${prefix}${caseId}`)); };
export const newCaseStateEventName = eventName;
