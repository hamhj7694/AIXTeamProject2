import type { MessageChannel, MvpMessage } from '../../services/mvpChatApi';

export interface CaseBookmark { bookmark_id: string; case_id: string; user_id: string; target_id: string; channel: MessageChannel; summary: string; actor_name: string; created_at: string; }
const key = (caseId: string, userId: string) => `mvp-v2:bookmarks:${caseId}:${userId}`;
export const bookmarkStore = {
  list(caseId: string, userId: string): CaseBookmark[] { try { return JSON.parse(localStorage.getItem(key(caseId, userId)) ?? '[]'); } catch { return []; } },
  toggle(message: MvpMessage, userId: string): CaseBookmark[] { const current = this.list(message.case_id, userId); const exists = current.some((item) => item.target_id === message.message_id); const next = exists ? current.filter((item) => item.target_id !== message.message_id) : [{ bookmark_id: crypto.randomUUID(), case_id: message.case_id, user_id: userId, target_id: message.message_id, channel: message.channel, summary: message.content.slice(0, 100), actor_name: message.actor_display_name, created_at: new Date().toISOString() }, ...current]; localStorage.setItem(key(message.case_id, userId), JSON.stringify(next)); window.dispatchEvent(new CustomEvent('mvp-bookmarks-changed', { detail: { caseId: message.case_id } })); return next; },
};
