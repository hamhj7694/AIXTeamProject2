import React from 'react';
import { Bell, CheckCircle2, Inbox, Trash2, X } from 'lucide-react';

export interface AppNotification { id: string; title: string; message: string; tone: 'success' | 'info'; createdAt: string; read: boolean; }
const STORAGE_KEY = 'csr-app-notifications-v1';
export const notificationEventName = 'csr:notification-created';
const readStored = (): AppNotification[] => { try { const value = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || '[]'); return Array.isArray(value) ? value : []; } catch { return []; } };
const writeStored = (items: AppNotification[]) => window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items.slice(0, 50)));
export const loadNotifications = (): AppNotification[] => typeof window === 'undefined' ? [] : readStored();
export const publishAnalysisNotification = (notification: Omit<AppNotification, 'id' | 'createdAt' | 'read'>) => { if (typeof window === 'undefined') return; const next: AppNotification = { ...notification, id: crypto.randomUUID(), createdAt: new Date().toISOString(), read: false }; writeStored([next, ...readStored()]); window.dispatchEvent(new CustomEvent(notificationEventName)); };

interface Props { items: AppNotification[]; onReadAll: () => void; onDelete: (id: string) => void; onClose: () => void; }
export const NotificationCenter: React.FC<Props> = ({ items, onReadAll, onDelete, onClose }) => <aside className="notification-center" aria-label="알림함">
  <header><div><p className="eyebrow">NOTIFICATION INBOX</p><h2><Bell size={16}/>알림함</h2></div><button type="button" className="icon-button" onClick={onClose} aria-label="알림함 닫기"><X size={16}/></button></header>
  <div className="notification-toolbar"><span>{items.length ? `${items.length}개의 알림` : '새 알림이 없습니다'}</span>{items.some((item) => !item.read) && <button type="button" onClick={onReadAll}>모두 읽음</button>}</div>
  <div className="notification-list">{items.length === 0 ? <div className="notification-empty"><Inbox size={22}/><p>분석 완료 알림이 여기에 표시됩니다.</p></div> : items.map((item) => <article key={item.id} className={`notification-item ${item.read ? 'is-read' : 'is-new'}`}><span className={`notification-icon ${item.tone}`}><CheckCircle2 size={15}/></span><div><strong>{item.title}</strong><p>{item.message}</p><time>{new Date(item.createdAt).toLocaleString('ko-KR')}</time></div><button type="button" className="notification-delete" onClick={() => onDelete(item.id)} aria-label="알림 삭제"><Trash2 size={14}/></button></article>)}</div>
</aside>;
