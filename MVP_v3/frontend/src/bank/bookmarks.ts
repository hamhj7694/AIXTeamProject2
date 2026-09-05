import { presentResponse } from '../userText';
export interface BankBookmark {
  entryId: string;
  label: string;
  summary: string;
  createdAt: string;
}

const storageKey = (caseId: string) => `mvp-v3:bank-bookmarks:${caseId}`;

export const readBankBookmarks = (caseId: string): BankBookmark[] => {
  try {
    const value = window.localStorage.getItem(storageKey(caseId));
    const parsed: unknown = value ? presentResponse(JSON.parse(value)) : [];
    return Array.isArray(parsed) ? parsed.filter((item): item is BankBookmark => Boolean(item && typeof item === 'object' && typeof (item as BankBookmark).entryId === 'string')) : [];
  } catch { return []; }
};

export const writeBankBookmarks = (caseId: string, items: BankBookmark[]) => {
  window.localStorage.setItem(storageKey(caseId), JSON.stringify(items));
};
