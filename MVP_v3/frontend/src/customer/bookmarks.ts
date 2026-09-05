import { presentResponse } from '../userText';
export interface CustomerBookmark {
  entryId: string;
  label: string;
  summary: string;
  createdAt: string;
}

const storageKey = (caseId: string) => `mvp-v3:customer-bookmarks:${caseId}`;

export const readCustomerBookmarks = (caseId: string): CustomerBookmark[] => {
  try {
    const value = presentResponse(JSON.parse(localStorage.getItem(storageKey(caseId)) || '[]'));
    return Array.isArray(value) ? value : [];
  } catch { return []; }
};

export const writeCustomerBookmarks = (caseId: string, items: CustomerBookmark[]) => {
  localStorage.setItem(storageKey(caseId), JSON.stringify(items));
};
