import React, { useEffect, useRef } from 'react';
import { Bookmark, X } from 'lucide-react';
import type { BankBookmark } from '../bank/bookmarks';

interface Props {
  open: boolean;
  items: BankBookmark[];
  onClose: () => void;
}

export const BankBookmarks: React.FC<Props> = ({ open, items, onClose }) => {
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose(); };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [onClose, open]);
  if (!open) return null;
  return <div className="bank-drawer-backdrop" role="presentation" onMouseDown={onClose}>
    <aside className="bank-bookmark-drawer" role="dialog" aria-modal="true" aria-labelledby="bank-bookmark-title" onMouseDown={(event) => event.stopPropagation()}>
      <header><Bookmark size={18}/><div><h2 id="bank-bookmark-title">내 북마크</h2><p>이 Case에서 개인적으로 저장한 대화와 업무 기록입니다.</p></div><button ref={closeRef} type="button" onClick={onClose} aria-label="북마크 닫기"><X size={18}/></button></header>
      <div>{items.length > 0 ? items.map((item) => <button key={item.entryId} type="button" onClick={() => { document.getElementById(item.entryId)?.scrollIntoView({ behavior: 'smooth', block: 'center' }); onClose(); }}><span>{item.label}</span><p>{item.summary}</p><time>{new Date(item.createdAt).toLocaleString('ko-KR')}</time></button>) : <p className="bank-bookmark-empty">아직 북마크한 기록이 없습니다.</p>}</div>
    </aside>
  </div>;
};
