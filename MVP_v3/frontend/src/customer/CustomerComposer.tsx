import React, { FormEvent, useRef, useState } from 'react';
import { Paperclip, Send, Sparkles, X } from 'lucide-react';

const MAX_FILES = 10;
const MAX_FILE_BYTES = 10 * 1024 * 1024;

interface Props {
  busy: boolean;
  aiBusy: boolean;
  disabled?: boolean;
  onSend: (content: string, files: File[], requestAi: boolean) => Promise<void>;
}

export const CustomerComposer: React.FC<Props> = ({ busy, aiBusy, disabled = false, onSend }) => {
  const [draft, setDraft] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [requestAi, setRequestAi] = useState(true);
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const blocked = busy || disabled;
  const submit = async () => {
    if (blocked || (!draft.trim() && files.length === 0)) return;
    try {
      setError('');
      await onSend(draft.trim(), files, requestAi && Boolean(draft.trim()));
      setDraft(''); setFiles([]);
    } catch (reason) { setError(reason instanceof Error ? reason.message : '메시지를 보내지 못했습니다.'); }
  };
  const addFiles = (incoming: FileList | null) => {
    if (!incoming) return;
    const next = [...files, ...Array.from(incoming)];
    if (next.length > MAX_FILES) { setError(`파일은 최대 ${MAX_FILES}개까지 첨부할 수 있습니다.`); return; }
    const tooLarge = next.find((file) => file.size > MAX_FILE_BYTES);
    if (tooLarge) { setError(`${tooLarge.name}: 파일당 최대 10MB까지 첨부할 수 있습니다.`); return; }
    setFiles(next); setError('');
  };

  return <div className="customer-composer">
    {files.length > 0 && <div className="queued-files">{files.map((file, index) => <span key={`${file.name}-${file.lastModified}-${index}`}><Paperclip size={13}/>{file.name}<button type="button" onClick={() => setFiles((items) => items.filter((_, itemIndex) => itemIndex !== index))} aria-label={`${file.name} 첨부 제거`}><X size={12}/></button></span>)}</div>}
    <button type="button" className={`customer-ai-request ${requestAi ? 'active' : ''}`} aria-pressed={requestAi} onClick={() => setRequestAi((value) => !value)} disabled={blocked}><Sparkles size={14}/>{requestAi ? 'AI 안전 안내 켜짐' : 'AI 안전 안내 끔'}<span>{requestAi ? '메시지를 보내면 AI가 안내합니다.' : '필요할 때 다시 켤 수 있습니다.'}</span></button>
    <form onSubmit={(event: FormEvent) => { event.preventDefault(); void submit(); }}>
      <div className="customer-composer-input">
        <input ref={inputRef} className="sr-only" type="file" multiple onChange={(event) => { addFiles(event.target.files); event.currentTarget.value = ''; }}/>
        <button type="button" className="icon-button" onClick={() => inputRef.current?.click()} disabled={blocked} aria-label="파일 또는 사진 첨부"><Paperclip size={19}/></button>
        <textarea rows={2} value={draft} disabled={disabled} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void submit(); } }} placeholder={disabled ? '종료된 상담입니다.' : '상대방이 요구한 내용이나 현재 상황을 입력하세요.'}/>
        <button type="submit" className="customer-send" disabled={blocked || (!draft.trim() && files.length === 0)} aria-label="메시지 전송"><Send size={19}/></button>
      </div>
    </form>
    {error && <p className="customer-inline-error">{error} 작성한 내용은 유지했습니다.</p>}
    {aiBusy && <p className="customer-ai-progress"><Sparkles size={13}/>AI가 방금 보낸 내용과 현재 상담 기록을 함께 살펴보고 있습니다. 계속 입력할 수 있습니다.</p>}
    <p className="customer-composer-help">Enter 전송 · Shift+Enter 줄바꿈 · 이미지·PDF·문서 최대 10개/각 10MB</p>
  </div>;
};
