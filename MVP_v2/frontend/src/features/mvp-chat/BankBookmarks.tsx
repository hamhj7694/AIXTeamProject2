import React, { useEffect, useState } from 'react';
import { Bookmark, X } from 'lucide-react';
import { bookmarkStore, type CaseBookmark } from './bookmarkStore';

const USER_ID = 'mvp-v2-current-user';
const channelLabel: Record<CaseBookmark['channel'], string> = {
  TEAM: '은행 협업',
  CUSTOMER: '고객 대화',
  AI_INTERNAL: 'AI 개인 작업공간',
};
export const BankBookmarks: React.FC<{ caseId: string }> = ({ caseId }) => {
  const [open, setOpen] = useState(false); const [items, setItems] = useState<CaseBookmark[]>([]);
  const refresh = () => setItems(bookmarkStore.list(caseId, USER_ID));
  useEffect(() => { refresh(); const listener = () => refresh(); window.addEventListener('mvp-bookmarks-changed', listener); return () => window.removeEventListener('mvp-bookmarks-changed', listener); }, [caseId]);
  const go = (item: CaseBookmark) => { window.dispatchEvent(new CustomEvent('mvp-bookmark-open', { detail: item })); setOpen(false); };
  return <><button type="button" onClick={() => setOpen(true)} className="fixed bottom-20 right-40 z-40 inline-flex items-center gap-2 rounded-full bg-white px-4 py-3 text-sm font-black text-slate-800 shadow-lg ring-1 ring-slate-200 hover:bg-slate-50 lg:bottom-6"><Bookmark size={17}/>북마크{items.length > 0 && <span className="rounded-full bg-blue-600 px-1.5 py-0.5 text-[10px] text-white">{items.length}</span>}</button>{open && <div className="fixed inset-0 z-50 bg-slate-950/30" onMouseDown={(event) => { if (event.target === event.currentTarget) setOpen(false); }}><aside className="absolute bottom-0 right-0 flex h-[min(620px,90vh)] w-full max-w-sm flex-col rounded-t-3xl bg-white shadow-2xl sm:bottom-4 sm:right-4 sm:rounded-3xl"><header className="flex items-center gap-2 border-b p-4"><Bookmark size={18} className="text-blue-600"/><div><h2 className="text-sm font-black">Case 북마크</h2><p className="text-[11px] text-slate-500">클릭하면 원래 채널과 메시지로 이동합니다.</p></div><button type="button" onClick={() => setOpen(false)} className="ml-auto rounded-lg p-2 hover:bg-slate-100"><X size={18}/></button></header><div className="flex-1 space-y-2 overflow-y-auto p-4">{items.length ? items.map((item) => <button key={item.bookmark_id} type="button" onClick={() => go(item)} className="w-full rounded-xl border border-slate-200 p-3 text-left hover:border-blue-300 hover:bg-blue-50"><div className="flex justify-between gap-2"><span className="text-[11px] font-black text-blue-700">{channelLabel[item.channel]}</span><time className="text-[10px] text-slate-400">{new Date(item.created_at).toLocaleString('ko-KR')}</time></div><p className="mt-1 text-xs font-bold text-slate-700">{item.actor_name}</p><p className="mt-1 line-clamp-2 text-xs leading-5 text-slate-500">{item.summary}</p></button>) : <p className="rounded-xl border border-dashed p-6 text-center text-xs text-slate-500">북마크한 메시지가 없습니다.</p>}</div></aside></div>}</>;
};
