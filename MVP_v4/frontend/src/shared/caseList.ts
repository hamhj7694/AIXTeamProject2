import type { CaseListItem } from '../api/cases.ts';
export type UserStatus = '의심' | '피해 발생' | '해결 및 종결';
export type SortKey = 'id' | 'created_at' | 'updated_at';
export function userStatus(item: { status: string; loss_status: string }): UserStatus {
  return item.status === 'CLOSED' ? '해결 및 종결' : item.loss_status === 'LOSS_CONFIRMED' ? '피해 발생' : '의심';
}
export function caseTitle(item: CaseListItem): string {
  return item.title || item.summary || '상황 확인이 필요한 사건';
}
export function selectCases(items: CaseListItem[], query: string, filter: string, sort: SortKey, ascending: boolean): CaseListItem[] {
  const needle = query.trim().toLocaleLowerCase();
  return items.filter(item => (!filter || userStatus(item) === filter) &&
    `${item.id} ${item.case_number} ${item.title} ${item.summary}`.toLocaleLowerCase().includes(needle))
    .sort((a, b) => (String(a[sort]).localeCompare(String(b[sort])) || a.id.localeCompare(b.id)) * (ascending ? 1 : -1));
}
export function displayTime(value: string): string {
  // DB audit timestamps are UTC; SQLite/MySQL can serialize them without the zone suffix.
  const date = new Date(/(?:Z|[+-][0-9]{2}:[0-9]{2})$/.test(value) ? value : `${value}Z`);
  return Number.isNaN(date.valueOf()) ? '-' : new Intl.DateTimeFormat('ko-KR', { dateStyle: 'short', timeStyle: 'short' }).format(date);
}
