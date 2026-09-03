import React from 'react';
import { Download, FileText } from 'lucide-react';
import { mvpChatApi, type MessageAttachment } from '../../../services/mvpChatApi';

const formatBytes = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
};

export const MessageAttachments: React.FC<{ attachments?: MessageAttachment[]; view: 'bank' | 'customer'; mine: boolean }> = ({ attachments = [], view, mine }) => {
  if (!attachments.length) return null;
  return <div className="mt-2 grid gap-2">
    {attachments.map((attachment) => {
      const url = mvpChatApi.attachmentContentUrl(attachment, view);
      const image = attachment.mime_type.startsWith('image/');
      return image ? <a key={attachment.attachment_id} href={url} target="_blank" rel="noreferrer" className="block overflow-hidden rounded-xl border border-white/20 bg-slate-950/10" title={`${attachment.original_name} 새 창에서 열기`}>
        <img src={url} alt={attachment.original_name} loading="lazy" className="max-h-72 w-full object-contain"/>
        <span className={`flex items-center justify-between gap-2 px-3 py-2 text-[10px] ${mine ? 'text-blue-50' : 'text-slate-500'}`}><span className="truncate">{attachment.original_name}</span><span>{formatBytes(attachment.size_bytes)}</span></span>
      </a> : <a key={attachment.attachment_id} href={url} download={attachment.original_name} className={`flex items-center gap-3 rounded-xl border p-3 text-left ${mine ? 'border-white/20 bg-white/10 text-white' : 'border-slate-200 bg-slate-50 text-slate-700'}`}>
        <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-lg ${mine ? 'bg-white/15' : 'bg-white text-blue-600'}`}><FileText size={17}/></span>
        <span className="min-w-0 flex-1"><b className="block truncate text-xs">{attachment.original_name}</b><span className={`mt-0.5 block text-[10px] ${mine ? 'text-blue-100' : 'text-slate-400'}`}>{formatBytes(attachment.size_bytes)} · {attachment.mime_type}</span></span>
        <Download size={15}/>
      </a>;
    })}
  </div>;
};
