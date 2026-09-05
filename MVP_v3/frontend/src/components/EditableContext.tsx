import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { Pencil, RotateCcw, X } from 'lucide-react';
import { request } from '../api/client';
import { CURRENT_BANK_USER } from '../api/cases';
import { bulletLines } from '../userText';

type Section = 'SUMMARY' | 'SIGNAL' | 'CLAIM' | 'DEMAND' | 'TACTIC' | 'NEXT_STEP' | 'EXPOSURE';
type Item = { section: Section; item_version: number; staff_text: string | null; deleted_by: string | null };
type Operation = 'EDIT' | 'DELETE' | 'RESTORE' | 'RESET';
const Context = createContext<{items: Item[]; save: (section: Section, operation: Operation, version: number, text?: string) => Promise<void>} | null>(null);

export const ContextEditing: React.FC<{caseId: string; children: React.ReactNode}> = ({ caseId, children }) => {
  const [items, setItems] = useState<Item[]>([]);
  const [error, setError] = useState('');
  const serial = useRef(0);
  const url = `/api/cases/${encodeURIComponent(caseId)}/context-display`;
  const actor = `actor_user_id=${encodeURIComponent(CURRENT_BANK_USER.user_id)}`;
  useEffect(() => {
    let active = true;
    const load = async () => {
      const id = ++serial.current;
      try { const data = await request<Item[]>(`${url}?${actor}`); if (active && id === serial.current) { setItems(data); setError(''); } }
      catch { if (active && id === serial.current) setError('직원 편집 내용을 불러오지 못했습니다. 연결과 사건 참여 권한을 확인해 주세요.'); }
    };
    setItems([]); void load();
    const timer = window.setInterval(() => void load(), 5000);
    return () => { active = false; ++serial.current; window.clearInterval(timer); };
  }, [url, actor]);
  const save = async (section: Section, operation: Operation, version: number, text?: string) => {
    const item = await request<Item>(`${url}/${section}?${actor}`, {method: 'PATCH', body: JSON.stringify({operation, expected_version: version, ...(text === undefined ? {} : {text})})});
    ++serial.current;
    setItems((current) => [...current.filter((entry) => entry.section !== section), item]);
    setError('');
  };
  return <Context.Provider value={{items, save}}>{error && <p className="context-edit-error" role="status">{error}</p>}{children}</Context.Provider>;
};

export const EditableContext: React.FC<{section: Section; title: string; lines: string[]; summary?: boolean}> = ({section, title, lines, summary = false}) => {
  const context = useContext(Context)!;
  const item = context.items.find((entry) => entry.section === section);
  const [draft, setDraft] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [expanded, setExpanded] = useState(false);
  const effective = item?.staff_text != null ? bulletLines(item.staff_text) : [...new Set(lines.flatMap(bulletLines))];
  const visible = expanded ? effective : effective.slice(0, summary ? 4 : 3);
  const overflow = effective.length > (summary ? 4 : 3) || effective.some((line) => line.length > 150);
  const save = async (operation: Operation) => {
    setBusy(true); setError('');
    try { await context.save(section, operation, operation === 'EDIT' ? version : item?.item_version ?? 0, operation === 'EDIT' ? draft ?? '' : undefined); setDraft(null); }
    catch (reason) { setError(reason instanceof Error ? reason.message : '변경 내용을 저장하지 못했습니다.'); }
    finally { setBusy(false); }
  };
  return <section className={`context-section editable-context ${summary ? 'context-overview' : ''}`}>
    <h3>{title}<span className="context-edit-tools">
      {item?.deleted_by ? <button type="button" onClick={() => void save('RESTORE')} disabled={busy} title="숨김 해제"><RotateCcw size={13}/><span className="sr-only">{title} 숨김 해제</span></button> : <>
        <button type="button" disabled={busy} title="항목 추가·수정" onClick={() => {setDraft(effective.join('\n')); setVersion(item?.item_version ?? 0); setError('');}}><Pencil size={13}/><span className="sr-only">{title} 항목 추가·수정</span></button>
        <button type="button" disabled={busy} title="숨기기" onClick={() => void save('DELETE')}><X size={13}/><span className="sr-only">{title} 숨기기</span></button>
      </>}
      {item?.staff_text != null && <button type="button" disabled={busy} title="직원 수정 해제 · 최신 자동 내용 사용" onClick={() => void save('RESET')}><RotateCcw size={13}/><span className="sr-only">직원 수정 해제</span></button>}
    </span></h3>
    {item?.deleted_by ? <p className="context-empty">직원이 숨긴 영역입니다. 숨김 해제로 다시 볼 수 있습니다.</p> : draft !== null ? <form onSubmit={(event) => {event.preventDefault(); void save('EDIT');}}>
      <label>한 줄에 한 항목씩 작성하세요. 표시 문구 편집이며 사실 확정이나 업무 처리는 아닙니다.<textarea autoFocus rows={6} maxLength={4000} value={draft} disabled={busy} onChange={(e) => setDraft(e.target.value)}/></label>
      <button className="secondary-action" type="button" disabled={busy} onClick={() => setDraft(null)}>취소</button> <button className="primary-action" disabled={busy || !draft.trim()}>저장</button>
    </form> : <>
      {effective.length ? <ul className="context-summary-points">{visible.map((line, index) => <li key={index}>{!expanded && line.length > 150 ? `${line.slice(0, 150)}…` : line}</li>)}</ul> : <p className="context-empty">등록된 내용이 없습니다. 연필 버튼으로 추가할 수 있습니다.</p>}
      {overflow && <button type="button" className="context-more" onClick={() => setExpanded(!expanded)}>{expanded ? '간단히 보기' : '전체 내용 보기'}</button>}
      {item?.staff_text != null && <small>직원 수정본 · 자동 갱신으로 덮어쓰지 않습니다.</small>}
    </>}
    {error && <p className="context-edit-error" role="alert">{error}</p>}
  </section>;
};
