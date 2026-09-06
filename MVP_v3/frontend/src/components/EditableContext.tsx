import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { Check, Pencil, Plus, RotateCcw, X } from 'lucide-react';
import { request } from '../api/client';
import { CURRENT_BANK_USER } from '../api/cases';
import { bulletLines } from '../userText';

type Section = 'SUMMARY' | 'SIGNAL' | 'CLAIM' | 'DEMAND' | 'TACTIC' | 'NEXT_STEP' | 'EXPOSURE';
type Item = { item_id: string; section: Section; semantic_key: string; item_version: number; ai_text?: string | null; staff_text: string | null; deleted_by: string | null; archive_index?: number | null };
type Operation = 'EDIT' | 'DELETE' | 'RESTORE' | 'RESET';
type ArchiveResult = {display: Item; archive: Item};
const Context = createContext<{
  items: Item[];
  ready: boolean;
  save: (section: Section, operation: Operation, version: number, text?: string) => Promise<Item>;
  archiveLine: (section: Section, version: number, remainingText: string | undefined, archivedText: string, archiveIndex: number) => Promise<void>;
  restoreArchive: (section: Section, version: number, archive: Item) => Promise<void>;
} | null>(null);

export const ContextEditing: React.FC<{caseId: string; children: React.ReactNode}> = ({ caseId, children }) => {
  const [items, setItems] = useState<Item[]>([]);
  const [error, setError] = useState('');
  const [ready, setReady] = useState(false);
  const serial = useRef(0);
  const saving = useRef(0);
  const alive = useRef(true);
  const url = `/api/cases/${encodeURIComponent(caseId)}/context-display`;
  const actor = `actor_user_id=${encodeURIComponent(CURRENT_BANK_USER.user_id)}`;
  useEffect(() => {
    let active = true;
    alive.current = true;
    const load = async () => {
      if (saving.current) return;
      const id = ++serial.current;
      try { const data = await request<Item[]>(`${url}?${actor}`); if (active && id === serial.current) { setItems(data); setReady(true); setError(''); } }
      catch { if (active && id === serial.current) setError('직원 편집 내용을 불러오지 못했습니다. 연결과 사건 참여 권한을 확인해 주세요.'); }
    };
    setItems([]); setReady(false); void load();
    const timer = window.setInterval(() => void load(), 5000);
    return () => { active = false; alive.current = false; ++serial.current; window.clearInterval(timer); };
  }, [url, actor]);
  const save = async (section: Section, operation: Operation, version: number, text?: string) => {
    ++saving.current; ++serial.current;
    try {
      const item = await request<Item>(`${url}/${section}?${actor}`, {method: 'PATCH', body: JSON.stringify({operation, expected_version: version, ...(text === undefined ? {} : {text})})});
      if (alive.current) {
        setItems((current) => [...current.filter((entry) => entry.item_id !== item.item_id && !(entry.section === section && entry.semantic_key === 'display')), item]);
        setError('');
      }
      return item;
    } finally { --saving.current; }
  };
  const archiveLine = async (section: Section, version: number, remainingText: string | undefined, archivedText: string, archiveIndex: number) => {
    ++saving.current; ++serial.current;
    try {
      const result = await request<ArchiveResult>(`${url}/${section}?${actor}`, {method: 'PATCH', body: JSON.stringify({operation: 'ARCHIVE', expected_version: version, archived_text: archivedText, archive_index: archiveIndex, ...(remainingText === undefined ? {} : {text: remainingText})})});
      if (alive.current) {
        setItems((current) => [...current.filter((entry) => entry.item_id !== result.display.item_id && entry.item_id !== result.archive.item_id && !(entry.section === section && entry.semantic_key === 'display')), result.display, result.archive]);
        setError('');
      }
    } finally { --saving.current; }
  };
  const restoreArchive = async (section: Section, version: number, archive: Item) => {
    ++saving.current; ++serial.current;
    try {
      const result = await request<ArchiveResult>(`${url}/${section}?${actor}`, {method: 'PATCH', body: JSON.stringify({operation: 'RESTORE_ARCHIVE', expected_version: version, archive_item_id: archive.item_id, archive_version: archive.item_version})});
      if (alive.current) {
        setItems((current) => [...current.filter((entry) => entry.item_id !== result.display.item_id && entry.item_id !== result.archive.item_id && !(entry.section === section && entry.semantic_key === 'display')), result.display]);
        setError('');
      }
    } finally { --saving.current; }
  };
  return <Context.Provider value={{items, ready, save, archiveLine, restoreArchive}}>{error && <p className="context-edit-error" role="status">{error}</p>}{children}</Context.Provider>;
};

type LineDraft = { index: number | null; text: string; lines: string[]; version: number; hidden: boolean };

export const EditableContext: React.FC<{section: Section; title: string; lines: string[]; summary?: boolean}> = ({section, title, lines, summary = false}) => {
  const context = useContext(Context)!;
  const item = context.items.find((entry) => entry.section === section && entry.semantic_key === 'display');
  const archived = context.items.filter((entry) => entry.section === section && entry.semantic_key.startsWith('display-archive:') && entry.deleted_by);
  const legacyArchive = item?.deleted_by && item.staff_text ? [item] : [];
  const archiveRows = [...archived, ...legacyArchive];
  const [draft, setDraft] = useState<LineDraft | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [expanded, setExpanded] = useState(false);
  const pending = useRef(false);
  const effective = item?.deleted_by ? [] : item?.staff_text != null ? item.staff_text.split('\n').filter(line => line.trim()) : [...new Set(lines.flatMap(bulletLines))];
  const visible = summary && !expanded ? effective.slice(0, 4) : effective;
  const overflow = summary && effective.length > 4;
  const disabled = busy || !context.ready;
  const run = async (operation: () => Promise<unknown>) => {
    if (pending.current || !context.ready) return;
    pending.current = true; setBusy(true); setError('');
    try { await operation(); setDraft(null); }
    catch (reason) { setError(reason instanceof Error ? reason.message : '변경 내용을 저장하지 못했습니다.'); }
    finally { pending.current = false; setBusy(false); }
  };
  const begin = (index: number | null) => {
    setDraft({index, text: index === null ? '' : effective[index], lines: [...effective], version: item?.item_version ?? 0, hidden: Boolean(item?.deleted_by)});
    setError('');
  };
  const commit = async () => {
    if (!draft?.text.trim()) return;
    const next = [...draft.lines];
    if (draft.index === null) next.push(draft.text.trim()); else next[draft.index] = draft.text.trim();
    const text = next.join('\n');
    if (text.length > 4000) { setError('이 영역은 4,000자까지 저장할 수 있습니다.'); return; }
    await run(async () => {
      let version = draft.version;
      if (draft.hidden) {
        const restored = await context.save(section, 'RESTORE', version);
        version = restored.item_version;
        setDraft(current => current ? {...current, hidden: false, version} : current);
      }
      await context.save(section, 'EDIT', version, text);
    });
  };
  const remove = (index: number) => {
    const next = effective.filter((_, position) => position !== index);
    void run(() => context.archiveLine(section, item?.item_version ?? 0, next.length ? next.join('\n') : undefined, effective[index], index));
  };
  const restore = (archive: Item) => void run(() => archive.semantic_key === 'display'
    ? context.save(section, 'RESTORE', archive.item_version)
    : context.restoreArchive(section, item?.item_version ?? 0, archive));
  const editor = <form className="context-line-editor" onSubmit={event => { event.preventDefault(); void commit(); }}>
    <textarea aria-label={`${title} 내용`} autoFocus rows={2} maxLength={4000} value={draft?.text ?? ''} disabled={disabled} onChange={e => setDraft(current => current ? {...current, text: e.target.value} : current)}/>
    <span className="context-line-tools">
      <button type="submit" className="context-icon" aria-label="저장" title="저장" disabled={disabled || !draft?.text.trim()}><Check size={14}/></button>
      <button type="button" className="context-icon" aria-label="취소" title="취소" disabled={busy} onClick={() => setDraft(null)}><X size={14}/></button>
    </span>
  </form>;
  return <section className="context-section context-simple-section">
    <h3>{title}<span className="context-line-tools">
      <button type="button" className="context-icon" disabled={disabled || draft !== null} title={summary ? '항목 추가·수정' : '추가'} aria-label={`${title} 추가`} onClick={() => begin(null)}><Plus size={14}/></button>
    </span></h3>
    <ul className="context-lines">{visible.map((line, index) => <li className="context-line" key={index}>
      {draft?.index === index ? editor : <><span className="context-line-text">{line}</span><span className="context-line-tools">
        <button type="button" className="context-icon" disabled={disabled || draft !== null} title="수정" aria-label={`${title} ${index + 1}번째 항목 수정`} onClick={() => begin(index)}><Pencil size={13}/></button>
        <button type="button" className="context-icon" disabled={disabled || draft !== null} title={summary ? '숨기기' : '제외'} aria-label={`${title} ${index + 1}번째 항목 제외`} onClick={() => remove(index)}><X size={14}/></button>
      </span></>}
    </li>)}</ul>
    {overflow && <button type="button" className="context-more" onClick={() => setExpanded(!expanded)}>{expanded ? '간단히 보기' : '전체 내용 보기'}</button>}
    {draft?.index === null && editor}
    {archiveRows.length > 0 && <details className="context-quiet-details"><summary>완료·제외</summary><ul className="context-lines">{archiveRows.map((archive) => <li className="context-line is-archived" key={`archive-${archive.item_id}`}>
      <span className="context-line-text">{archive.staff_text?.split('\n').filter(Boolean).join(' · ')}</span>
      <span className="context-line-tools"><button type="button" className="context-icon" title="복원" aria-label={`${title} 제외 항목 복원`} disabled={disabled || draft !== null} onClick={() => restore(archive)}><RotateCcw size={14}/></button></span>
    </li>)}</ul></details>}
    {error && <p className="context-edit-error" role="alert">{error}</p>}
  </section>;
};
