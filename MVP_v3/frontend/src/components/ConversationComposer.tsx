import React, { FormEvent, useRef, useState } from 'react';
import { Bookmark, Bot, Building2, MessageCircleQuestion, Paperclip, Send, ShieldCheck, Sparkles, StickyNote, X } from 'lucide-react';
import { hasBankAiMention } from '../bank/aiMention';
import { BankCardMenu, type BankCardKind } from './cards/BankCardMenu';

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
  /** Hide legacy question/verification/action entry points during the frontend rebuild. */
  foundationMode?: boolean;
  /** Lock this composer to one communication channel. */
  fixedTarget?: ComposerTarget;
  /** Show the internal AI request toggle. */
  showAi?: boolean;
  /** Show notes and bookmarks in this composer. */
  showUtilities?: boolean;
  /** Show the customer-question action in the quick-actions row. */
  showQuestionAction?: boolean;
  /** Surface composer validation errors in the parent warning area. */
  onErrorChange?: (message: string) => void;
  /** Keep false when the parent owns the employee-facing warning area. */
  showInlineError?: boolean;
  onSelectBankCard?: (kind: BankCardKind) => void;
  selectedBankCard?: BankCardKind | null;
}

export const ConversationComposer: React.FC<Props> = ({ busy, aiBusy, onSend, onOpenQuestions, onOpenVerification, onOpenAction, onInvokeAi, onOpenNotes, onOpenBookmarks, bookmarkCount, foundationMode = false, fixedTarget, showAi = true, showUtilities = true, showQuestionAction = false, onErrorChange, showInlineError = true, onSelectBankCard, selectedBankCard = null }) => {
  const target = fixedTarget ?? 'TEAM';
  const [draft, setDraft] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [requestAi, setRequestAi] = useState(true);
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const submittingRef = useRef(false);
  const mentionRequestsAi = target === 'TEAM' && hasBankAiMention(draft);
  const aiRequested = target === 'TEAM' && (requestAi || mentionRequestsAi);
  const updateError = (message: string) => { setError(message); onErrorChange?.(message); };
  const updateDraft = (value: string) => {
    setDraft(value);
  };
  const submit = async () => {
    if (submittingRef.current || busy || (!draft.trim() && files.length === 0)) return;
    if (fixedTarget === 'CUSTOMER' && hasBankAiMention(draft)) {
      updateError('고객 메시지에는 AI 요청을 넣을 수 없습니다.');
      return;
    }
    submittingRef.current = true;
    try { await onSend(draft.trim(), files, target, aiRequested && Boolean(draft.trim())); setDraft(''); setFiles([]); updateError(''); }
    catch (reason) { updateError(reason instanceof Error ? reason.message : '메시지를 전송하지 못했습니다.'); }
    finally { submittingRef.current = false; }
  };
  const addFiles = (incoming: FileList | null) => {
    if (!incoming) return;
    const next = [...files, ...Array.from(incoming)];
    if (next.length > MAX_FILES) { updateError(`파일은 한 번에 최대 ${MAX_FILES}개까지 첨부할 수 있습니다.`); return; }
    const tooLarge = next.find((file) => file.size > MAX_FILE_BYTES);
    if (tooLarge) { updateError(`${tooLarge.name}: 파일당 최대 10MB까지 첨부할 수 있습니다.`); return; }
    setFiles(next); updateError('');
  };
  return <div className={`composer-shell composer-target-${target.toLowerCase()}`}>
    <div className="context-actions" aria-label="Case 빠른 작업">
      {showQuestionAction && <button type="button" onClick={onOpenQuestions} disabled={busy}><MessageCircleQuestion size={15}/>고객에게 질문하기</button>}
      {!foundationMode && <>
        <button onClick={onOpenQuestions} disabled={busy}><MessageCircleQuestion size={15}/>고객에게 확인 질문</button>
        <button onClick={onOpenVerification} disabled={busy}><Building2 size={15}/>기관 확인 리스트</button>
        <button onClick={onOpenAction} disabled={busy}><ShieldCheck size={15}/>조치 기록</button>
      </>}
      {showAi && <>
        <button type="button" className={`bank-ai-compose-toggle ${requestAi ? 'active' : ''}`} aria-pressed={requestAi} onClick={() => setRequestAi((current) => !current)} disabled={busy || aiBusy}><Sparkles size={14}/><b>AI에게 물어보기</b></button>
        <button type="button" onClick={onInvokeAi} disabled={busy || aiBusy} aria-label="사건 정리"><Bot size={15}/>{aiBusy ? 'AI 검토 중' : '사건 정리'}</button>
      </>}
      {showUtilities && <>
        <span className="context-actions-spacer"/>
        <button className="personal-note-open" type="button" onClick={onOpenNotes}><StickyNote size={15}/>개인 메모</button>
        <button className="bookmark-list-open" type="button" onClick={onOpenBookmarks}><Bookmark size={15}/>북마크{bookmarkCount > 0 && <b>{bookmarkCount}</b>}</button>
      </>}
      {target === 'TEAM' && onSelectBankCard && <><span className="context-actions-spacer"/><BankCardMenu value={selectedBankCard} onChange={onSelectBankCard}/></>}
    </div>
    <form onSubmit={(event: FormEvent) => { event.preventDefault(); void submit(); }}>
      {files.length > 0 && <div className="queued-files">{files.map((file, index) => <span key={`${file.name}-${file.lastModified}-${index}`}><Paperclip size={13}/>{file.name}<button type="button" onClick={() => setFiles((items) => items.filter((_, itemIndex) => itemIndex !== index))} aria-label={`${file.name} 첨부 제거`}><X size={12}/></button></span>)}</div>}
      <div className="composer-input">
        <input ref={inputRef} type="file" multiple className="sr-only" onChange={(event) => { addFiles(event.target.files); event.currentTarget.value = ''; }}/>
        <button type="button" className="icon-button" onClick={() => inputRef.current?.click()} disabled={busy} aria-label="파일 또는 사진 첨부"><Paperclip size={18}/></button>
        <textarea rows={2} value={draft} onChange={(event) => updateDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void submit(); } }} placeholder={target === 'CUSTOMER' ? '고객에게 보낼 메시지를 입력하세요.' : '은행 내부 메시지 또는 @AI 요청사항을 입력하세요.'}/>
        <button className="send-button" type="submit" disabled={busy || (!draft.trim() && files.length === 0)} aria-label="메시지 전송"><Send size={18}/></button>
      </div>
      {showInlineError && error && <p className="composer-error">{error}</p>}
      {mentionRequestsAi && !aiBusy && <p className="composer-ai-mention"><Sparkles size={13}/><b>@AI 호출 준비됨</b><span>전송하면 최신 Shared Case와 요청사항을 함께 분석합니다.</span></p>}
      <p className="composer-help">Enter 전송 · Shift+Enter 줄바꿈 · 이미지·PDF·문서 최대 10개/각 10MB</p>
      {aiBusy && <p className="composer-ai-progress"><Sparkles size={13}/>AI가 방금 보낸 내용과 최신 Case 기록을 함께 검토하고 있습니다. 입력은 계속할 수 있습니다.</p>}
    </form>
  </div>;
};
