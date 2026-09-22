import React, { FormEvent, useRef, useState } from 'react';

import { ChevronUp, Send, Sparkles } from 'lucide-react';

import { usePersistentDraft } from '../draftStorage';


interface Props {
  busy: boolean;
  aiBusy: boolean;
  disabled?: boolean;
  showEmergency?: boolean;
  emergencyActive?: boolean;
  guideOpen?: boolean;
  onEmergency?: () => void;
  onOpenRecoveryGuide?: () => void;
  onSend: (content: string, requestAi: boolean) => Promise<void>;
  draftStorageKey?: string;
}


export const CustomerComposer: React.FC<Props> = ({ busy, aiBusy, disabled = false, showEmergency = false, emergencyActive = false, guideOpen = false, onEmergency, onOpenRecoveryGuide, onSend }) => {
  const [draft, setDraft] = useState('');

  //나중에 형준이랑 얘기해서 통합
// export const CustomerComposer: React.FC<Props> = ({ busy, aiBusy, disabled = false, onSend, draftStorageKey }) => {
//   const [draft, setDraft] = usePersistentDraft(draftStorageKey);

  const [requestAi, setRequestAi] = useState(true);
  const [error, setError] = useState('');
  const submittingRef = useRef(false);
  const blocked = busy || disabled;
  const submit = async () => {
    if (submittingRef.current || blocked || !draft.trim()) return;
    submittingRef.current = true;
    try {
      setError('');
      await onSend(draft.trim(), requestAi);
      setDraft('');
    } catch (reason) { setError(reason instanceof Error ? reason.message : '메시지를 보내지 못했습니다.'); }
    finally { submittingRef.current = false; }
  };
  return <div className="customer-composer">
    <div className="customer-composer-toolbar">
      <button type="button" className={`customer-ai-request ${requestAi ? 'active' : ''}`} aria-pressed={requestAi} onClick={() => setRequestAi((value) => !value)} disabled={blocked}><Sparkles size={14}/>{requestAi ? 'AI 안전 안내 켜짐' : 'AI 안전 안내 끔'}<span>{requestAi ? '메시지를 보내면 AI가 안내합니다.' : '필요할 때 다시 켤 수 있습니다.'}</span></button>
      {showEmergency && (!emergencyActive ? <button type="button" className="customer-emergency-button" disabled={blocked} onClick={onEmergency}>이미 사기 당했어요</button> : <div className="customer-recovery-status" role="status"><span>피해 대응 안내 중</span>{!guideOpen && <button type="button" className="customer-recovery-open-button" disabled={blocked} onClick={onOpenRecoveryGuide} aria-label="구제 안내 열기"><ChevronUp size={14}/></button>}</div>)}
    </div>
    <form onSubmit={(event: FormEvent) => { event.preventDefault(); void submit(); }}>
      <div className="customer-composer-input">
        <textarea rows={2} value={draft} disabled={disabled} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void submit(); } }} placeholder={disabled ? '종료된 상담입니다.' : '상대방이 요구한 내용이나 현재 상황을 입력하세요.'}/>
        <button type="submit" className="customer-send" disabled={blocked || !draft.trim()} aria-label="메시지 전송"><Send size={19}/></button>
      </div>
    </form>
    {error && <p className="customer-inline-error">{error} 작성한 내용은 유지했습니다.</p>}
    <p className="customer-composer-help">Enter 전송 · Shift+Enter 줄바꿈</p>
  </div>;
};
