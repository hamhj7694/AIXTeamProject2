import React, { FormEvent, useRef, useState } from 'react';
import { Bot, Building2, MessageCircleQuestion, Paperclip, Send, ShieldCheck, X } from 'lucide-react';

export type ComposerTarget = 'CUSTOMER' | 'TEAM';
const MAX_FILES = 10;
const MAX_FILE_BYTES = 10 * 1024 * 1024;

interface Props {
  busy: boolean;
  onSend: (content: string, files: File[], target: ComposerTarget) => Promise<void>;
  onOpenQuestions: () => void;
  onOpenVerification: () => void;
  onOpenAction: () => void;
  onInvokeAi: () => void;
}

export const ConversationComposer: React.FC<Props> = ({ busy, onSend, onOpenQuestions, onOpenVerification, onOpenAction, onInvokeAi }) => {
  const [target, setTarget] = useState<ComposerTarget>('TEAM');
  const [draft, setDraft] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const submit = async () => {
    if (busy || (!draft.trim() && files.length === 0)) return;
    try { await onSend(draft.trim(), files, target); setDraft(''); setFiles([]); setError(''); }
    catch (reason) { setError(reason instanceof Error ? reason.message : '메시지를 전송하지 못했습니다.'); }
  };
  const addFiles = (incoming: FileList | null) => {
    if (!incoming) return;
    const next = [...files, ...Array.from(incoming)];
    if (next.length > MAX_FILES) { setError(`파일은 한 번에 최대 ${MAX_FILES}개까지 첨부할 수 있습니다.`); return; }
    const tooLarge = next.find((file) => file.size > MAX_FILE_BYTES);
    if (tooLarge) { setError(`${tooLarge.name}: 파일당 최대 10MB까지 첨부할 수 있습니다.`); return; }
    setFiles(next); setError('');
  };
  return <div className={`composer-shell composer-target-${target.toLowerCase()}`}>
    <div className="context-actions" aria-label="Case 빠른 작업">
      <button onClick={onOpenQuestions} disabled={busy}><MessageCircleQuestion size={15}/>고객에게 확인 질문</button>
      <button onClick={onOpenVerification} disabled={busy}><Building2 size={15}/>기관 확인 요청</button>
      <button onClick={onOpenAction} disabled={busy}><ShieldCheck size={15}/>조치 기록</button>
      <button onClick={onInvokeAi} disabled={busy}><Bot size={15}/>사건 정리</button>
    </div>
    <form onSubmit={(event: FormEvent) => { event.preventDefault(); void submit(); }}>
      <div className="target-toggle" aria-label="메시지 공개 대상">
        <button type="button" className={target === 'TEAM' ? 'active internal' : ''} onClick={() => setTarget('TEAM')}>은행 내부</button>
        <button type="button" className={target === 'CUSTOMER' ? 'active customer' : ''} onClick={() => setTarget('CUSTOMER')}>고객에게</button>
        <span>{target === 'CUSTOMER' ? '고객에게 공개됩니다.' : '고객에게 보이지 않습니다.'}</span>
      </div>
      {files.length > 0 && <div className="queued-files">{files.map((file, index) => <span key={`${file.name}-${file.lastModified}-${index}`}><Paperclip size={13}/>{file.name}<button type="button" onClick={() => setFiles((items) => items.filter((_, itemIndex) => itemIndex !== index))} aria-label={`${file.name} 첨부 제거`}><X size={12}/></button></span>)}</div>}
      <div className="composer-input">
        <input ref={inputRef} type="file" multiple className="sr-only" onChange={(event) => { addFiles(event.target.files); event.currentTarget.value = ''; }}/>
        <button type="button" className="icon-button" onClick={() => inputRef.current?.click()} disabled={busy} aria-label="파일 또는 사진 첨부"><Paperclip size={18}/></button>
        <textarea rows={2} value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void submit(); } }} placeholder={target === 'CUSTOMER' ? '고객에게 보낼 메시지를 입력하세요.' : '은행 내부에 남길 내용을 입력하세요.'}/>
        <button className="send-button" type="submit" disabled={busy || (!draft.trim() && files.length === 0)} aria-label="메시지 전송"><Send size={18}/></button>
      </div>
      {error && <p className="composer-error">{error}</p>}
      <p className="composer-help">Enter 전송 · Shift+Enter 줄바꿈 · 이미지·PDF·문서 최대 10개/각 10MB</p>
    </form>
  </div>;
};
