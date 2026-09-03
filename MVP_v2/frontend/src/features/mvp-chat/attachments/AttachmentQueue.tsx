import React from 'react';
import { FileText, Image, X } from 'lucide-react';
import type { MessageAttachment } from '../../../services/mvpChatApi';

export interface QueuedFile { id: string; file: File; previewUrl?: string; attachment?: MessageAttachment; }

const formatBytes = (bytes: number) => bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)}KB` : `${(bytes / 1024 / 1024).toFixed(1)}MB`;

export const AttachmentQueue: React.FC<{ files: QueuedFile[]; dark: boolean; onRemove: (id: string) => void }> = ({ files, dark, onRemove }) => {
  if (!files.length) return null;
  return <div className="mb-2 grid gap-2 sm:grid-cols-2">
    {files.map((item) => <div key={item.id} className={`flex items-center gap-2 rounded-xl border p-2 ${dark ? 'border-slate-700 bg-slate-900 text-slate-200' : 'border-slate-200 bg-white text-slate-700'}`}>
      {item.previewUrl ? <img src={item.previewUrl} alt="" className="h-10 w-10 rounded-lg object-cover"/> : <span className={`grid h-10 w-10 place-items-center rounded-lg ${dark ? 'bg-slate-800 text-blue-300' : 'bg-blue-50 text-blue-600'}`}>{item.file.type.startsWith('image/') ? <Image size={17}/> : <FileText size={17}/>}</span>}
      <span className="min-w-0 flex-1"><b className="block truncate text-xs">{item.file.name}</b><span className="text-[10px] text-slate-400">{formatBytes(item.file.size)}</span></span>
      <button type="button" onClick={() => onRemove(item.id)} className="rounded-lg p-1 text-slate-400 hover:bg-rose-50 hover:text-rose-600" aria-label={`${item.file.name} 첨부 취소`}><X size={14}/></button>
    </div>)}
  </div>;
};
