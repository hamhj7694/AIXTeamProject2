import { useEffect, useRef, useState } from 'react';
import { readJson, type CaseEvent } from '../api/cases.ts';
import { createUuid } from '../shared/uuid.ts';
import { projectEvent } from '../shared/conversation.ts';
import { displayTime } from '../shared/caseList.ts';

interface PersonalBookmark { id: string; target_entity_id: string; target_entity_type: 'EVENT'; active: boolean; available: boolean; version: number; }
interface PersonalNote { id: string; content: string; version: number; created_at: string; }
interface PersonalState { actor_id: string; notes: PersonalNote[]; bookmarks: PersonalBookmark[]; }

export function usePersonalWorkspace(caseId: string | null) {
  const [data, setData] = useState<{ caseId: string; value: PersonalState } | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [retry, setRetry] = useState(0);
  const generation = useRef(0);
  const noteRetry = useRef<{ caseId: string; content: string; id: string } | null>(null);
  const current = data?.caseId === caseId ? data.value : null;
  useEffect(() => {
    const epoch = ++generation.current;
    const controller = new AbortController();
    setBusy(false); setError('');
    if (caseId) readJson(`/api/v4/cases/${caseId}/personal`, controller.signal).then(value => {
      if (epoch === generation.current && !controller.signal.aborted) setData({ caseId, value: value as PersonalState });
    }).catch(() => { if (!controller.signal.aborted) setError('개인 기록을 불러오지 못했습니다.'); });
    return () => { controller.abort(); generation.current++; };
  }, [caseId, retry]);
  const write = async (route: string, body: unknown) => {
    if (!caseId || !current || busy) return false;
    const epoch = generation.current;
    setBusy(true); setError('');
    try {
      const result = await readJson(`/api/v4/cases/${caseId}/personal/${route}`, undefined, body) as PersonalState;
      if (epoch === generation.current) setData({ caseId, value: result });
      return true;
    } catch (reason) {
      if (epoch === generation.current) setError(reason instanceof Error && reason.message === 'CASE_VERSION_CONFLICT' ? '다른 창에서 기록이 변경되었습니다. 새로고침 후 다시 시도해 주세요.' : '개인 기록을 저장하지 못했습니다. 초안은 유지됩니다.');
      return false;
    } finally { if (epoch === generation.current) setBusy(false); }
  };
  const addNote = async (content: string) => {
    if (!caseId) return false;
    if (noteRetry.current?.content !== content || noteRetry.current?.caseId !== caseId) noteRetry.current = { caseId, content, id: createUuid() };
    const success = await write('notes', { client_request_id: noteRetry.current.id, content });
    if (success) noteRetry.current = null;
    return success;
  };
  const toggle = async (target: string) => {
    const existing = current?.bookmarks.find(item => item.target_entity_id === target);
    return write('bookmarks', { client_request_id: createUuid(), target_entity_type: 'EVENT', target_entity_id: target,
      expected_version: existing?.version ?? 0, active: !existing?.active });
  };
  return { current, error, busy, addNote, toggle, refresh: () => setRetry(value => value + 1) };
}

export type PersonalController = ReturnType<typeof usePersonalWorkspace>;
export function BookmarkButton({ id, personal }: { id: string; personal: PersonalController }) {
  const active = personal.current?.bookmarks.some(item => item.target_entity_id === id && item.active) ?? false;
  return <button className="bookmark-toggle" aria-label={active ? '북마크 취소' : '북마크 추가'} aria-pressed={active} disabled={personal.busy || !personal.current} onClick={() => void personal.toggle(id)}>{active ? '★' : '☆'}</button>;
}

export function PersonalUtilities({ caseId, events, personal }: { caseId: string; events: CaseEvent[]; personal: PersonalController }) {
  const [panel, setPanel] = useState<'notes' | 'bookmarks' | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [navigationError, setNavigationError] = useState('');
  const highlightTimer = useRef<number | null>(null);
  useEffect(() => () => { if (highlightTimer.current) window.clearTimeout(highlightTimer.current); }, []);
  const save = async () => {
    const value = (drafts[caseId] ?? '').trim();
    if (value && await personal.addNote(value)) setDrafts(current => current[caseId]?.trim() === value ? { ...current, [caseId]: '' } : current);
  };
  const navigate = (id: string) => {
    const target = document.getElementById(`conversation-${id}`);
    if (!target) { setNavigationError('원본 항목을 확인할 수 없습니다.'); return; }
    setPanel(null); setNavigationError('');
    window.requestAnimationFrame(() => {
      target.scrollIntoView({ behavior: 'smooth', block: 'center' }); target.focus({ preventScroll: true });
      document.querySelectorAll('.bookmark-highlight').forEach(item => item.classList.remove('bookmark-highlight'));
      target.classList.add('bookmark-highlight');
      if (highlightTimer.current) window.clearTimeout(highlightTimer.current);
      highlightTimer.current = window.setTimeout(() => target.classList.remove('bookmark-highlight'), 2500);
    });
  };
  const bookmarks = personal.current?.bookmarks.filter(item => item.active) ?? [];
  return <>
    <button onClick={() => { setPanel('notes'); setNavigationError(''); }}>개인 메모</button>
    <button onClick={() => { setPanel('bookmarks'); setNavigationError(''); }}>내 북마크{bookmarks.length ? ` (${bookmarks.length})` : ''}</button>
    {personal.error && <span className="error" role="alert">{personal.error}<button onClick={personal.refresh}>새로고침</button></span>}
    {panel && <div className="modal-backdrop"><section className="utility-dialog personal-panel" role="dialog" aria-modal="true" aria-label={panel === 'notes' ? '개인 메모' : '내 북마크'}>
      <div className="panel-heading"><h2>{panel === 'notes' ? '개인 메모' : '내 북마크'}</h2><button autoFocus onClick={() => setPanel(null)}>닫기</button></div>
      {!personal.current && <p role="status">개인 기록을 불러오는 중입니다.</p>}
      {panel === 'notes' ? <>
        <p>나만 보는 업무 기록입니다. 고객에게 공개되거나 사건의 공식 사실로 반영되지 않습니다.</p>
        <textarea aria-label="개인 메모 내용" placeholder="기억할 내용이나 다음 확인 사항을 적어두세요." rows={4} maxLength={4000} value={drafts[caseId] ?? ''} onChange={event => setDrafts(value => ({ ...value, [caseId]: event.target.value }))} />
        <button disabled={personal.busy || !personal.current || !(drafts[caseId] ?? '').trim()} onClick={() => void save()}>메모 추가</button>
        <ul className="personal-notes">{personal.current?.notes.map(note => <li key={note.id}><time>{displayTime(note.created_at)}</time><p>{note.content}</p></li>)}</ul>
        {personal.current && !personal.current.notes.length && <p>작성한 메모가 없습니다.</p>}
      </> : <>
        {navigationError && <p role="alert">{navigationError}</p>}
        {!bookmarks.length && <p>이 사건에 저장한 북마크가 없습니다.</p>}
        <ul className="personal-bookmarks">{bookmarks.map(bookmark => {
          const event = events.find(item => item.id === bookmark.target_entity_id);
          const projected = event ? projectEvent(event) : null;
          return <li key={bookmark.id}><button disabled={!bookmark.available || !projected} onClick={() => navigate(bookmark.target_entity_id)}>{bookmark.available && projected ? projected.title : '원본 항목을 확인할 수 없습니다.'}</button>
            <button aria-label="북마크 취소" disabled={personal.busy} onClick={() => void personal.toggle(bookmark.target_entity_id)}>취소</button></li>;
        })}</ul>
      </>}
    </section></div>}
  </>;
}
