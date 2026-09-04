import React, { FormEvent, useEffect, useMemo, useRef, useState } from 'react';
import { Bookmark, Bot, Loader2, Paperclip, Send, Share2, ShieldCheck, UserRound } from 'lucide-react';
import type { MessageAttachment, MvpMessage } from '../../services/mvpChatApi';
import { AttachmentQueue, type QueuedFile } from './attachments/AttachmentQueue';
import { MessageAttachments } from './attachments/MessageAttachments';
import { bookmarkStore } from './bookmarkStore';

interface Props {
  title: string;
  description: string;
  channelLabel?: string;
  headerActions?: React.ReactNode;
  messages: MvpMessage[];
  placeholder: string;
  currentUserId: string;
  theme?: 'light' | 'dark';
  sending?: boolean;
  onSend: (content: string, attachmentIds?: string[]) => Promise<void>;
  onUploadFile?: (file: File) => Promise<MessageAttachment>;
  attachmentView?: 'bank' | 'customer';
  quickActions?: Array<{ id: string; label: string }>;
  onQuickAction?: (id: string) => void;
  timelineCards?: Array<{ id: string; createdAt: string; content: React.ReactNode }>;
  onShareMessage?: (message: MvpMessage) => Promise<void>;
  sharingMessageId?: string | null;
  draftStorageKey?: string;
  heightClassName?: string;
  focusMessageId?: string | null;
  disabled?: boolean;
  loading?: boolean;
}

const actorLabel: Record<MvpMessage['actor_type'], string> = {
  CUSTOMER: '고객', BANK_STAFF: '은행 담당자', CUSTOMER_AGENT: 'Customer Agent',
  BANK_AGENT: 'CaseCopilot', VERIFICATION: '기관 검증', SYSTEM: '시스템',
};

const WorkflowNoticeCard: React.FC<{
  message: MvpMessage; dark: boolean; focused: boolean; bookmarked: boolean;
  bookmarkEnabled: boolean; onBookmark: () => void;
}> = ({ message, dark, focused, bookmarked, bookmarkEnabled, onBookmark }) => {
  const urgent = message.actor_display_name.includes('긴급 알림');
  const prepared = message.content.startsWith('업무 카드 준비됨');
  const completed = message.content.startsWith('업무 실행 완료');
  const customerAnswer = message.content.startsWith('고객 답변 접수');
  const noticeLabel = urgent ? '피해 발생 긴급 알림' : customerAnswer ? '고객 답변 · 확인 필요' : prepared ? 'AI 업무 초안' : completed ? '업무 반영 완료' : 'Shared Case 업무 알림';
  const container = focused
    ? 'border-blue-300 bg-blue-100 ring-2 ring-blue-300'
    : urgent
      ? dark ? 'border-rose-400/70 bg-rose-500/15 ring-1 ring-rose-500/30' : 'border-rose-300 bg-rose-50'
      : customerAnswer
        ? dark ? 'border-emerald-400/40 bg-emerald-500/10' : 'border-emerald-200 bg-emerald-50'
      : completed
        ? dark ? 'border-blue-400/40 bg-blue-500/10' : 'border-blue-200 bg-blue-50'
      : dark ? 'border-blue-500/30 bg-blue-500/10' : 'border-blue-200 bg-blue-50';
  return <article id={`message-${message.message_id}`} className={`scroll-mt-4 rounded-xl border p-3 transition ${container}`}>
    <div className="flex items-start gap-2">
      <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-lg ${urgent ? 'bg-rose-600 text-white' : dark ? 'bg-blue-500/20 text-blue-300' : 'bg-blue-600 text-white'}`}><Bot size={14}/></span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className={`text-[11px] font-black ${urgent ? 'text-rose-400' : customerAnswer ? dark ? 'text-emerald-200' : 'text-emerald-800' : dark ? 'text-blue-200' : 'text-blue-800'}`}>{message.actor_display_name || actorLabel[message.actor_type]} · {noticeLabel}</p>
          <time className="text-[10px] text-slate-400">{new Date(message.created_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}</time>
          {bookmarkEnabled && <button type="button" onClick={onBookmark} className={`ml-auto rounded p-1 ${bookmarked ? 'text-amber-500' : 'text-slate-400 hover:text-amber-500'}`} aria-label={bookmarked ? '북마크 해제' : '북마크 추가'}><Bookmark size={13} fill={bookmarked ? 'currentColor' : 'none'}/></button>}
        </div>
        <p className={`mt-1 whitespace-pre-wrap text-xs font-semibold leading-5 ${dark ? 'text-slate-200' : 'text-slate-700'}`}>{message.content}</p>
      </div>
    </div>
  </article>;
};

const MAX_FILES = 10;
const MAX_FILE_BYTES = 10 * 1024 * 1024;

export const ChatWorkspace: React.FC<Props> = ({
  title, description, channelLabel, headerActions, messages, placeholder, currentUserId, theme = 'light', sending = false,
  onSend, onUploadFile, attachmentView = 'customer', quickActions = [], onQuickAction,
  onShareMessage, sharingMessageId, draftStorageKey, heightClassName = 'min-h-[620px]', focusMessageId, timelineCards = [], disabled = false, loading = false,
}) => {
  const [draft, setDraft] = useState(() => draftStorageKey ? localStorage.getItem(draftStorageKey) ?? '' : '');
  const [bookmarked, setBookmarked] = useState<string[]>([]);
  const [queuedFiles, setQueuedFiles] = useState<QueuedFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [attachmentError, setAttachmentError] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queuedFilesRef = useRef<QueuedFile[]>([]);
  const followLatestRef = useRef(true);
  const initializedScrollRef = useRef(false);
  const dark = theme === 'dark';
  const caseId = messages[0]?.case_id;
  const bookmarkEnabled = currentUserId === 'mvp-v2-current-user' || currentUserId === 'mvp-v2-customer';
  const busy = sending || uploading || disabled;
  const timeline = useMemo(() => [
    ...messages.map((message, sequence) => ({ id: `message-${message.message_id}`, createdAt: message.created_at, sequence, kind: 'message' as const, message })),
    ...timelineCards.map((card, index) => ({ id: `card-${card.id}`, createdAt: card.createdAt, sequence: messages.length + index, kind: 'card' as const, card })),
  ].sort((left, right) => {
    const leftTime = Date.parse(left.createdAt);
    const rightTime = Date.parse(right.createdAt);
    const timeDelta = (Number.isFinite(leftTime) ? leftTime : 0) - (Number.isFinite(rightTime) ? rightTime : 0);
    return timeDelta || left.sequence - right.sequence;
  }), [messages, timelineCards]);

  useEffect(() => {
    if (!draftStorageKey) return;
    const timer = window.setTimeout(() => localStorage.setItem(draftStorageKey, draft), 250);
    return () => { window.clearTimeout(timer); localStorage.setItem(draftStorageKey, draft); };
  }, [draft, draftStorageKey]);
  useEffect(() => {
    const node = scrollRef.current;
    if (!node) return;
    if (!initializedScrollRef.current || followLatestRef.current) node.scrollTop = node.scrollHeight;
    initializedScrollRef.current = true;
  }, [timeline.length]);
  useEffect(() => { if (focusMessageId) document.getElementById(`message-${focusMessageId}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }); }, [focusMessageId, messages]);
  useEffect(() => { if (caseId) setBookmarked(bookmarkStore.list(caseId, currentUserId).map((item) => item.target_id)); }, [caseId, currentUserId, messages.length]);
  useEffect(() => { queuedFilesRef.current = queuedFiles; }, [queuedFiles]);
  useEffect(() => () => queuedFilesRef.current.forEach((item) => item.previewUrl && URL.revokeObjectURL(item.previewUrl)), []);

  const removeQueuedFile = (id: string) => setQueuedFiles((items) => {
    const target = items.find((item) => item.id === id);
    if (target?.previewUrl) URL.revokeObjectURL(target.previewUrl);
    return items.filter((item) => item.id !== id);
  });

  const queueFiles = (files: FileList | null) => {
    if (!files) return;
    setAttachmentError('');
    const remaining = MAX_FILES - queuedFiles.length;
    const accepted: QueuedFile[] = [];
    for (const file of Array.from(files).slice(0, Math.max(0, remaining))) {
      if (!file.size || file.size > MAX_FILE_BYTES) {
        setAttachmentError('빈 파일은 첨부할 수 없으며, 파일 하나당 최대 크기는 10MB입니다.');
        continue;
      }
      accepted.push({ id: crypto.randomUUID(), file, previewUrl: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined });
    }
    if (files.length > remaining) setAttachmentError(`메시지 하나에는 파일을 최대 ${MAX_FILES}개까지 첨부할 수 있습니다.`);
    setQueuedFiles((items) => [...items, ...accepted]);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const sendDraft = async () => {
    const content = draft.trim();
    if ((!content && !queuedFiles.length) || busy) return;
    if (queuedFiles.length && !onUploadFile) {
      setAttachmentError('이 채널에서는 아직 파일 업로드를 사용할 수 없습니다.');
      return;
    }
    setUploading(queuedFiles.length > 0);
    setAttachmentError('');
    try {
      const uploaded: Array<{ id: string; attachment: MessageAttachment }> = [];
      for (const item of queuedFiles) uploaded.push({ id: item.id, attachment: item.attachment ?? await onUploadFile!(item.file) });
      if (uploaded.length) setQueuedFiles((items) => items.map((item) => ({ ...item, attachment: uploaded.find((entry) => entry.id === item.id)?.attachment ?? item.attachment })));
      await onSend(content, uploaded.map((item) => item.attachment.attachment_id));
      setDraft('');
      if (draftStorageKey) localStorage.removeItem(draftStorageKey);
      queuedFiles.forEach((item) => item.previewUrl && URL.revokeObjectURL(item.previewUrl));
      setQueuedFiles([]);
    } catch (reason) {
      setAttachmentError(reason instanceof Error ? reason.message : '파일을 전송하지 못했습니다.');
    } finally {
      setUploading(false);
    }
  };

  const toggleBookmark = (message: MvpMessage) => setBookmarked(bookmarkStore.toggle(message, currentUserId).map((item) => item.target_id));

  return <section className={`flex ${heightClassName} min-h-0 flex-col overflow-hidden rounded-2xl border shadow-sm ${dark ? 'border-slate-700 bg-slate-950' : 'border-slate-200 bg-white'}`}>
    <header className={`border-b px-5 py-4 ${dark ? 'border-slate-800 bg-slate-950' : 'border-slate-100'}`}><div className="flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center"><div className="min-w-0"><h1 className={`text-base font-black ${dark ? 'text-white' : 'text-slate-900'}`}>{title}</h1><p className={`mt-1 text-xs ${dark ? 'text-slate-400' : 'text-slate-500'}`}>{description}</p></div>{headerActions ?? (channelLabel ? <span className={`shrink-0 rounded-full px-2.5 py-1 text-[11px] font-bold ${dark ? 'bg-slate-800 text-slate-200' : 'bg-slate-100 text-slate-600'}`}>{channelLabel}</span> : null)}</div></header>
    <div ref={scrollRef} onScroll={(event) => { const node = event.currentTarget; followLatestRef.current = node.scrollHeight - node.scrollTop - node.clientHeight < 72; }} className={`flex-1 space-y-4 overflow-y-auto p-4 sm:p-5 ${dark ? 'bg-slate-900' : 'bg-slate-50/70'}`} aria-live="polite">
      {loading ? <div className={`flex items-center justify-center gap-2 rounded-2xl border border-dashed p-6 text-center text-sm ${dark ? 'border-slate-700 bg-slate-800 text-slate-300' : 'border-blue-100 bg-blue-50 text-blue-700'}`}><Loader2 size={16} className="animate-spin"/> 안전 상담을 연결하고 있습니다.</div> : timeline.length === 0 && <div className={`rounded-2xl border border-dashed p-6 text-center text-sm ${dark ? 'border-slate-700 bg-slate-800 text-slate-400' : 'border-slate-200 bg-white text-slate-500'}`}>아직 대화가 없습니다.</div>}
      {timeline.map((entry) => {
        if (entry.kind === 'card') return <article key={entry.id} className="space-y-1"><time className={`block px-1 text-[10px] ${dark ? 'text-slate-500' : 'text-slate-400'}`}>{new Date(entry.createdAt).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}</time>{entry.card.content}</article>;
        const message = entry.message;
        const mine = message.actor_user_id === currentUserId;
        const agent = message.actor_type === 'CUSTOMER_AGENT' || message.actor_type === 'BANK_AGENT';
        const canShare = Boolean(onShareMessage && message.actor_type === 'BANK_AGENT' && message.message_kind === 'AI_RESPONSE' && message.visibility === 'AI_PRIVATE' && message.private_owner_user_id === currentUserId);
        const marked = bookmarked.includes(message.message_id);
        if (message.message_kind === 'SYSTEM_EVENT') return <WorkflowNoticeCard key={message.message_id} message={message} dark={dark} focused={focusMessageId === message.message_id} bookmarked={marked} bookmarkEnabled={bookmarkEnabled} onBookmark={() => toggleBookmark(message)}/>;
        return <article id={`message-${message.message_id}`} key={message.message_id} className={`scroll-mt-4 flex gap-2.5 rounded-xl transition ${focusMessageId === message.message_id ? 'bg-blue-100 p-2 ring-2 ring-blue-300' : ''} ${mine ? 'flex-row-reverse' : ''}`}>
          <div className={`grid h-8 w-8 shrink-0 place-items-center rounded-full ${mine ? 'bg-blue-600 text-white' : agent ? 'bg-violet-200 text-violet-800' : 'bg-amber-100 text-amber-700'}`}>{agent ? <Bot size={16}/> : mine ? <UserRound size={16}/> : <ShieldCheck size={16}/>}</div>
          <div className={`max-w-[82%] ${mine ? 'text-right' : ''}`}>
            <div className={`mb-1 flex items-center gap-1 ${mine ? 'justify-end' : ''}`}><p className={`text-[11px] font-bold ${dark ? 'text-slate-400' : 'text-slate-500'}`}>{message.actor_display_name || actorLabel[message.actor_type]}</p>{bookmarkEnabled && <button type="button" onClick={() => toggleBookmark(message)} className={`rounded p-1 ${marked ? 'text-amber-500' : 'text-slate-400 hover:text-amber-500'}`} aria-label={marked ? '북마크 해제' : '북마크 추가'} title={marked ? '북마크 해제' : '북마크 추가'}><Bookmark size={13} fill={marked ? 'currentColor' : 'none'}/></button>}</div>
            <div className={`rounded-2xl px-3.5 py-2.5 text-left text-sm leading-6 ${mine ? 'rounded-tr-sm bg-blue-600 text-white' : dark ? 'rounded-tl-sm border border-slate-700 bg-slate-800 text-slate-100' : 'rounded-tl-sm border border-slate-200 bg-white text-slate-700'}`}>{message.content && <p className="whitespace-pre-wrap">{message.content}</p>}<MessageAttachments attachments={message.attachments} view={attachmentView} mine={mine}/></div>
            {canShare && <button type="button" disabled={sharingMessageId === message.message_id} onClick={() => onShareMessage && void onShareMessage(message)} className={`mt-2 inline-flex items-center gap-1 rounded-lg border px-2 py-1 text-[11px] font-bold ${dark ? 'border-violet-500/50 bg-slate-800 text-violet-200' : 'border-blue-200 bg-white text-blue-700'}`}><Share2 size={12}/>{sharingMessageId === message.message_id ? '공유 중' : '팀에 공유'}</button>}
            <time className="mt-1 block text-[10px] text-slate-400">{new Date(message.created_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}</time>
          </div>
        </article>;
      })}
    </div>
    <form onSubmit={(event: FormEvent) => { event.preventDefault(); void sendDraft(); }} className={`border-t p-3 sm:p-4 ${dark ? 'border-slate-800 bg-slate-950' : 'border-slate-200 bg-white'}`}>
      {quickActions.length > 0 && <div className="mb-3 flex flex-wrap items-center gap-2"><span className="mr-1 text-[11px] font-bold text-slate-400">빠른 AI 작업</span>{quickActions.map((action) => <button key={action.id} type="button" disabled={busy} onClick={() => onQuickAction?.(action.id)} className={`rounded-full border px-2.5 py-1.5 text-[11px] font-bold ${dark ? 'border-violet-500/50 bg-slate-800 text-violet-200' : 'border-violet-200 bg-violet-50 text-violet-800'}`}>{action.label}</button>)}</div>}
      <AttachmentQueue files={queuedFiles} dark={dark} onRemove={removeQueuedFile}/>
      {attachmentError && <p className="mb-2 rounded-lg bg-rose-50 px-3 py-2 text-[11px] font-bold text-rose-700">{attachmentError}</p>}
      <div className={`flex items-end gap-2 rounded-2xl border p-2 ${dark ? 'border-slate-700 bg-slate-900' : 'border-slate-200 bg-slate-50'}`}>
        <input ref={fileInputRef} type="file" multiple accept="image/jpeg,image/png,image/gif,image/webp,application/pdf,text/plain,text/csv,application/json,.doc,.docx,.xls,.xlsx" onChange={(event) => queueFiles(event.target.files)} className="hidden"/>
        <button type="button" disabled={busy || !onUploadFile} onClick={() => fileInputRef.current?.click()} className="grid h-9 w-9 place-items-center rounded-lg text-slate-400 hover:bg-blue-50 hover:text-blue-600 disabled:opacity-40" aria-label="파일 또는 이미지 첨부" title="파일 또는 이미지 첨부"><Paperclip size={18}/></button>
        <textarea value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void sendDraft(); } }} rows={2} placeholder={placeholder} className={`min-h-[44px] flex-1 resize-none bg-transparent px-1 py-2 text-sm outline-none ${dark ? 'text-white placeholder:text-slate-500' : ''}`}/>
        <button type="submit" disabled={(!draft.trim() && !queuedFiles.length) || busy} className="grid h-10 w-10 place-items-center rounded-xl bg-blue-600 text-white disabled:opacity-40" aria-label="메시지 전송">{uploading ? <Loader2 size={17} className="animate-spin"/> : <Send size={17}/>}</button>
      </div>
      <p className="mt-2 text-[11px] text-slate-400">Enter 전송 · Shift+Enter 줄바꿈 · 이미지·PDF·문서 최대 10개/각 10MB · 작성 중인 텍스트는 자동 저장됩니다.</p>
    </form>
  </section>;
};
