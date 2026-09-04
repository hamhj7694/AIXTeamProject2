import React, { FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import { Loader2, Pencil, Plus, Save, StickyNote, Trash2, X } from 'lucide-react';
import { casesApi } from '../api/cases';
import type { PersonalNote } from '../api/types';

interface Props {
  caseId: string;
  open: boolean;
  onClose: () => void;
}

export const BankPersonalNotes: React.FC<Props> = ({ caseId, open, onClose }) => {
  const closeRef = useRef<HTMLButtonElement>(null);
  const [notes, setNotes] = useState<PersonalNote[]>([]);
  const [draft, setDraft] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingContent, setEditingContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try { setNotes(await casesApi.personalNotes(caseId)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : '개인 메모를 불러오지 못했습니다.'); }
    finally { setLoading(false); }
  }, [caseId]);

  useEffect(() => {
    if (!open) return;
    void load(); closeRef.current?.focus();
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose(); };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [load, onClose, open]);

  const create = async (event: FormEvent) => {
    event.preventDefault();
    if (!draft.trim() || busy) return;
    setBusy(true); setError('');
    try { const created = await casesApi.createPersonalNote(caseId, draft.trim()); setNotes((items) => [created, ...items]); setDraft(''); }
    catch (reason) { setError(reason instanceof Error ? reason.message : '개인 메모를 저장하지 못했습니다.'); }
    finally { setBusy(false); }
  };
  const save = async () => {
    if (!editingId || !editingContent.trim() || busy) return;
    setBusy(true); setError('');
    try { const updated = await casesApi.updatePersonalNote(caseId, editingId, editingContent.trim()); setNotes((items) => items.map((item) => item.note_id === updated.note_id ? updated : item)); setEditingId(null); setEditingContent(''); }
    catch (reason) { setError(reason instanceof Error ? reason.message : '개인 메모를 수정하지 못했습니다.'); }
    finally { setBusy(false); }
  };
  const remove = async (noteId: string) => {
    if (busy || !window.confirm('이 개인 메모를 삭제할까요?')) return;
    setBusy(true); setError('');
    try { await casesApi.deletePersonalNote(caseId, noteId); setNotes((items) => items.filter((item) => item.note_id !== noteId)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : '개인 메모를 삭제하지 못했습니다.'); }
    finally { setBusy(false); }
  };

  if (!open) return null;
  return <div className="bank-drawer-backdrop" role="presentation" onMouseDown={onClose}>
    <aside className="bank-note-drawer" role="dialog" aria-modal="true" aria-labelledby="bank-note-title" onMouseDown={(event) => event.stopPropagation()}>
      <header><StickyNote size={19}/><div><h2 id="bank-note-title">개인 메모</h2><p>고객에게 공개되지 않는 담당자 개인 기록입니다.</p></div><button ref={closeRef} type="button" onClick={onClose} aria-label="개인 메모 닫기"><X size={18}/></button></header>
      <form onSubmit={create}><textarea value={draft} onChange={(event) => setDraft(event.target.value)} maxLength={10000} placeholder="기억할 내용이나 다음 확인 사항을 적어두세요."/><div><small>{draft.length.toLocaleString()} / 10,000</small><button type="submit" disabled={busy || !draft.trim()}><Plus size={14}/>메모 추가</button></div></form>
      {error && <p className="bank-note-error">{error}</p>}
      <div className="bank-note-list">{loading ? <p className="bank-note-state"><Loader2 className="spin" size={18}/>메모를 불러오고 있습니다.</p> : notes.length === 0 ? <p className="bank-note-state">아직 작성한 개인 메모가 없습니다.</p> : notes.map((note) => <article key={note.note_id}>
        {editingId === note.note_id ? <><textarea value={editingContent} onChange={(event) => setEditingContent(event.target.value)} maxLength={10000}/><div className="bank-note-actions"><button type="button" onClick={() => { setEditingId(null); setEditingContent(''); }}>취소</button><button type="button" className="primary" disabled={busy || !editingContent.trim()} onClick={() => void save()}><Save size={13}/>저장</button></div></> : <><p>{note.content}</p><footer><time>{new Date(note.updated_at).toLocaleString('ko-KR')}</time><button type="button" onClick={() => { setEditingId(note.note_id); setEditingContent(note.content); }} aria-label="개인 메모 수정"><Pencil size={13}/></button><button type="button" onClick={() => void remove(note.note_id)} aria-label="개인 메모 삭제"><Trash2 size={13}/></button></footer></>}
      </article>)}</div>
    </aside>
  </div>;
};
