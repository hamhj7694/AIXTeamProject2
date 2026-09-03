export interface CaseChangedDetail {
  eventId: string;
  caseId: string | null;
  reason: string;
  changedAt: string;
}

const EVENT_NAME = 'mvp-v2:case-changed';
const STORAGE_KEY = 'mvp-v2:last-case-change';

const parseCaseId = (path: string, payload?: unknown): string | null => {
  if (payload && typeof payload === 'object' && 'case_id' in payload) {
    const value = (payload as { case_id?: unknown }).case_id;
    if (typeof value === 'string' && value) return value;
  }
  const matched = path.match(/^\/api\/cases\/([^/?]+)/);
  if (!matched) return null;
  const value = decodeURIComponent(matched[1]);
  return ['analyze', 'admin', 'trash'].includes(value) ? null : value;
};

export const notifyCaseChanged = (caseId: string | null, reason: string) => {
  const detail: CaseChangedDetail = { eventId: crypto.randomUUID(), caseId, reason, changedAt: new Date().toISOString() };
  window.dispatchEvent(new CustomEvent<CaseChangedDetail>(EVENT_NAME, { detail }));
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(detail)); } catch { /* 브라우저 저장소 차단 시 현재 탭 이벤트만 사용한다. */ }
};

export const notifyApiMutation = (path: string, init: RequestInit | undefined, payload?: unknown) => {
  const method = (init?.method ?? 'GET').toUpperCase();
  if (method === 'GET' || path.includes('/presence/heartbeat') || path.includes('/admin/verify-password')) return;
  notifyCaseChanged(parseCaseId(path, payload), `${method} ${path}`);
};

export const subscribeCaseChanged = (caseId: string | null, listener: (detail: CaseChangedDetail) => void) => {
  const accept = (detail: CaseChangedDetail | null) => {
    if (!detail || (caseId && detail.caseId && detail.caseId !== caseId)) return;
    listener(detail);
  };
  const onLocal = (event: Event) => accept((event as CustomEvent<CaseChangedDetail>).detail);
  const onStorage = (event: StorageEvent) => {
    if (event.key !== STORAGE_KEY || !event.newValue) return;
    try { accept(JSON.parse(event.newValue) as CaseChangedDetail); } catch { /* 손상된 외부 저장 이벤트는 무시한다. */ }
  };
  window.addEventListener(EVENT_NAME, onLocal);
  window.addEventListener('storage', onStorage);
  return () => {
    window.removeEventListener(EVENT_NAME, onLocal);
    window.removeEventListener('storage', onStorage);
  };
};
