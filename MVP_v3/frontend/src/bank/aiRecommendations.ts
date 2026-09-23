import type { RecommendedChatAction } from '../api/types';

const STORAGE_PREFIX = 'csr:ai-recommendations:';

const storageKey = (caseId: string) => `${STORAGE_PREFIX}${caseId}`;

const isValidAction = (value: unknown): value is RecommendedChatAction => {
  if (!value || typeof value !== 'object') return false;
  const action = value as Partial<RecommendedChatAction>;
  const keys = ['CUSTOMER_QUESTION', 'TRANSACTION_LOOKUP', 'OFFICIAL_VERIFICATION', 'RESPONSE_ACTION', 'DRAFT_REPLY'];
  if (!keys.includes(action.action_key ?? '') || !['TOOL', 'REPLY_DRAFT'].includes(action.kind ?? '') || !['TEAM', 'CUSTOMER'].includes(action.target_channel ?? '')) return false;
  if (action.kind === 'TOOL' && action.target_channel !== 'TEAM') return false;
  if (action.kind === 'REPLY_DRAFT' && (action.action_key !== 'DRAFT_REPLY' || !action.draft_text?.trim())) return false;
  return action.action_key !== 'DRAFT_REPLY' || action.kind === 'REPLY_DRAFT';
};

export function saveLatestAiRecommendations(caseId: string, messageId: string, actions: RecommendedChatAction[]): void {
  if (typeof window === 'undefined') return;
  try {
    if (!actions.length) {
      window.localStorage.removeItem(storageKey(caseId));
      return;
    }
    window.localStorage.setItem(storageKey(caseId), JSON.stringify({ messageId, actions: actions.slice(0, 3) }));
  } catch {
    // Storage is an enhancement; the in-memory optimistic message still works.
  }
}

export function readLatestAiRecommendations(caseId: string, messageId: string): RecommendedChatAction[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(storageKey(caseId));
    if (!raw) return [];
    const stored = JSON.parse(raw) as { messageId?: string; actions?: RecommendedChatAction[] };
    if (stored.messageId !== messageId || !Array.isArray(stored.actions)) return [];
    return stored.actions.filter(isValidAction).filter((action, index, all) => all.findIndex((candidate) => candidate.action_key === action.action_key) === index).slice(0, 3);
  } catch {
    return [];
  }
}
