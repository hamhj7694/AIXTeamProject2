import React, { useEffect, useRef } from 'react';
import { Bookmark, X } from 'lucide-react';
import type { CustomerBookmark } from './bookmarks';

interface Props {
  open: boolean;
  items: CustomerBookmark[];
  onClose: () => void;
}

export const CustomerBookmarks: React.FC<Props> = ({ open, items, onClose }) => {
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();
    const listener = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose(); };
    window.addEventListener('keydown', listener);
    return () => window.removeEventListener('keydown', listener);
  }, [onClose, open]);
  if (!open) return null;
  return <div className="customer-drawer-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <aside className="customer-bookmark-drawer" role="dialog" aria-modal="true" aria-labelledby="customer-bookmark-title">
      <header><Bookmark size={18}/><div><h2 id="customer-bookmark-title">내 북마크</h2><p>이 브라우저에서 저장한 상담 기록입니다.</p></div><button ref={closeRef} type="button" onClick={onClose} aria-label="북마크 닫기"><X size={18}/></button></header>
      <div>{items.length > 0 ? items.map((item) => <button key={item.entryId} type="button" onClick={() => { document.getElementById(item.entryId)?.scrollIntoView({ behavior: 'smooth', block: 'center' }); onClose(); }}><span>{item.label}</span><p>{item.summary}</p><time>{new Date(item.createdAt).toLocaleString('ko-KR')}</time></button>) : <p className="customer-bookmark-empty">아직 북마크한 기록이 없습니다.</p>}</div>
    </aside>
  </div>;
};
