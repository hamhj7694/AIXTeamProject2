import React, { FormEvent, useRef, useState } from 'react';
import { Bookmark, Bot, Building2, MessageCircleQuestion, Paperclip, Send, ShieldCheck, Sparkles, StickyNote, X } from 'lucide-react';
import { hasBankAiMention } from '../bank/aiMention';

export type ComposerTarget = 'CUSTOMER' | 'TEAM';
const MAX_FILES = 10;
const MAX_FILE_BYTES = 10 * 1024 * 1024;

interface Props {
  busy: boolean;
  aiBusy: boolean;
  onSend: (content: string, files: File[], target: ComposerTarget, requestAi: boolean) => Promise<void>;
  onOpenQuestions: () => void;
  onOpenVerification: () => void;
  onOpenAction: () => void;
  onInvokeAi: () => void;
  onOpenNotes: () => void;
  onOpenBookmarks: () => void;
  bookmarkCount: number;
}

export const ConversationComposer: React.FC<Props> = ({ busy, aiBusy, onSend, onOpenQuestions, onOpenVerification, onOpenAction, onInvokeAi, onOpenNotes, onOpenBookmarks, bookmarkCount }) => {
  const [target, setTarget] = useState<ComposerTarget>('TEAM');
  const [draft, setDraft] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [requestAi, setRequestAi] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const submittingRef = useRef(false);
  const mentionRequestsAi = target === 'TEAM' && hasBankAiMention(draft);
  const aiRequested = target === 'TEAM' && (requestAi || mentionRequestsAi);
  const selectTarget = (nextTarget: ComposerTarget) => {
    setTarget(nextTarget);
    // 고객 채널은 고객에게 실제로 공개되는 메시지이므로 AI 요청을 허용하지 않는다.
    if (nextTarget === 'CUSTOMER') setRequestAi(false);
  };
  const updateDraft = (value: string) => {
    setDraft(value);
    // 고객에게 보낼 문장에 @AI가 들어가면 내부 요청으로 즉시 전환해
    // AI 지시가 고객 채널에 실수로 공개되지 않게 한다.
    if (target === 'CUSTOMER' && hasBankAiMention(value)) setTarget('TEAM');
  };
  const submit = async () => {
    if (submittingRef.current || busy || (!draft.trim() && files.length === 0)) return;
    submittingRef.current = true;
    try { await onSend(draft.trim(), files, target, aiRequested && Boolean(draft.trim())); setDraft(''); setFiles([]); setError(''); }
    catch (reason) { setError(reason instanceof Error ? reason.message : '메시지를 전송하지 못했습니다.'); }
    finally { submittingRef.current = false; }
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
      <button onClick={onOpenVerification} disabled={busy}><Building2 size={15}/>기관 확인 리스트</button>
      <button onClick={onOpenAction} disabled={busy}><ShieldCheck size={15}/>조치 기록</button>
      <button onClick={onInvokeAi} disabled={busy || aiBusy}><Bot size={15}/>{aiBusy ? 'AI 검토 중' : '사건 정리'}</button>
      <span className="context-actions-spacer"/>
      <button className="personal-note-open" type="button" onClick={onOpenNotes}><StickyNote size={15}/>개인 메모</button>
      <button className="bookmark-list-open" type="button" onClick={onOpenBookmarks}><Bookmark size={15}/>북마크{bookmarkCount > 0 && <b>{bookmarkCount}</b>}</button>
    </div>
    <form onSubmit={(event: FormEvent) => { event.preventDefault(); void submit(); }}>
      <div className="target-toggle" aria-label="메시지 공개 대상">
        <button type="button" className={`bank-ai-compose-toggle ${aiRequested ? 'active' : ''}`} aria-pressed={aiRequested} onClick={() => setRequestAi((current) => !current)} disabled={busy || target === 'CUSTOMER'} title={target === 'CUSTOMER' ? '고객에게 보내는 메시지에서는 AI 요청을 사용할 수 없습니다.' : undefined}><Sparkles size={14}/><b>AI에게 물어보기</b><span>{target === 'CUSTOMER' ? '고객 채널에서는 사용할 수 없음' : mentionRequestsAi ? '@AI 멘션 감지 · 자동 호출' : requestAi ? '전송 후 은행 내부 대화에만 응답 표시' : '@AI를 입력하거나 버튼으로 호출'}</span></button>
        <button type="button" className={`target-option ${target === 'TEAM' ? 'active internal' : ''}`} onClick={() => selectTarget('TEAM')}>은행 내부</button>
        <button type="button" className={`target-option ${target === 'CUSTOMER' ? 'active customer' : ''}`} onClick={() => selectTarget('CUSTOMER')}>고객에게</button>
        <span className="target-hint">{target === 'CUSTOMER' ? '고객에게 공개됩니다.' : '고객에게 보이지 않습니다.'}</span>
      </div>
      {files.length > 0 && <div className="queued-files">{files.map((file, index) => <span key={`${file.name}-${file.lastModified}-${index}`}><Paperclip size={13}/>{file.name}<button type="button" onClick={() => setFiles((items) => items.filter((_, itemIndex) => itemIndex !== index))} aria-label={`${file.name} 첨부 제거`}><X size={12}/></button></span>)}</div>}
      <div className="composer-input">
        <input ref={inputRef} type="file" multiple className="sr-only" onChange={(event) => { addFiles(event.target.files); event.currentTarget.value = ''; }}/>
        <button type="button" className="icon-button" onClick={() => inputRef.current?.click()} disabled={busy} aria-label="파일 또는 사진 첨부"><Paperclip size={18}/></button>
        <textarea rows={2} value={draft} onChange={(event) => updateDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void submit(); } }} placeholder={target === 'CUSTOMER' ? '고객에게 보낼 메시지를 입력하세요.' : '은행 내부 메시지 또는 @AI 요청사항을 입력하세요.'}/>
        <button className="send-button" type="submit" disabled={busy || (!draft.trim() && files.length === 0)} aria-label="메시지 전송"><Send size={18}/></button>
      </div>
      {error && <p className="composer-error">{error}</p>}
      {mentionRequestsAi && !aiBusy && <p className="composer-ai-mention"><Sparkles size={13}/><b>@AI 호출 준비됨</b><span>전송하면 최신 Shared Case와 요청사항을 함께 분석합니다.</span></p>}
      <p className="composer-help">Enter 전송 · Shift+Enter 줄바꿈 · 이미지·PDF·문서 최대 10개/각 10MB</p>
      {aiBusy && <p className="composer-ai-progress"><Sparkles size={13}/>AI가 방금 보낸 내용과 최신 Case 기록을 함께 검토하고 있습니다. 입력은 계속할 수 있습니다.</p>}
    </form>
  </div>;
};
