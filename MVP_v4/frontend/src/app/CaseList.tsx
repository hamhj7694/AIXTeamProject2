import { useEffect, useRef, useState } from 'react';
import { getCaseList, readJson, type CaseListItem } from '../api/cases.ts';
import { caseTitle, displayTime, selectCases, userStatus, type SortKey } from '../shared/caseList.ts';
import { createUuid } from '../shared/uuid.ts';

export function CaseList({ selectedId, onSelect }: { selectedId: string | null; onSelect: (id: string | null) => void }) {
  const [items, setItems] = useState<CaseListItem[]>([]);
  const [trash, setTrash] = useState(false);
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('');
  const [sort, setSort] = useState<SortKey>('updated_at');
  const [ascending, setAscending] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [target, setTarget] = useState<CaseListItem | null>(null);
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [adminError, setAdminError] = useState('');
  const requestId = useRef('');
  useEffect(() => {
    const controller = new AbortController();
    let pending = false;
    const refresh = async () => {
      if (pending) return;
      pending = true;
      try {
        const next = await getCaseList(controller.signal, trash);
        if (!controller.signal.aborted) { setItems(next); setError(''); }
      } catch { if (!controller.signal.aborted) setError('사건 목록을 불러오지 못했습니다. 다시 시도해 주세요.'); }
      finally { pending = false; if (!controller.signal.aborted) setLoading(false); }
    };
    setLoading(true); void refresh();
    const timer = window.setInterval(refresh, 5000);
    return () => { controller.abort(); window.clearInterval(timer); };
  }, [trash, attempt]);
  const visible = selectCases(items, query, filter, sort, ascending);
  const openAdmin = (item: CaseListItem) => { requestId.current = createUuid(); setPassword(''); setAdminError(''); setTarget(item); };
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); if (!target || busy) return;
    setBusy(true); setAdminError('');
    try {
      await readJson(`/api/v4/cases/${target.id}/trash`, undefined, {
        client_request_id: requestId.current, expected_version: target.version, deleted: !trash, admin_password: password,
      });
      if (selectedId === target.id) onSelect(null);
      setTarget(null); setPassword(''); setAttempt(value => value + 1);
    } catch (reason) {
      const code = reason instanceof Error ? reason.message : '';
      setAdminError(code === 'ADMIN_PASSWORD_INVALID' ? '관리자 암호가 올바르지 않습니다.' : code === 'CASE_VERSION_CONFLICT' ?
        '사건이 변경되었습니다. 창을 닫고 최신 목록에서 다시 시도해 주세요.' : '요청을 처리하지 못했습니다. 관리자 설정과 접근 권한을 확인해 주세요.');
      setPassword('');
    } finally { setBusy(false); }
  };
  return <aside className="case-list compact" aria-label="사건 목록">
    <div className="panel-heading"><h1>{trash ? '휴지통' : '사건'}</h1><button onClick={() => setAttempt(value => value + 1)}>새로고침</button></div>
    <input className="case-search" aria-label="사건 검색" placeholder="사건 검색" value={query} onChange={event => setQuery(event.target.value)} />
    <div className="case-filters" aria-label="상태 필터">{[['', '전체'], ['피해 발생', '피해 발생'], ['의심', '의심'], ['해결 및 종결', '해결']].map(([value, label]) =>
      <button key={value} aria-pressed={filter === value} onClick={() => setFilter(value)}>{label}</button>)}</div>
    <div className="case-sort"><select aria-label="정렬 기준" value={sort} onChange={e => setSort(e.target.value as SortKey)}>
      <option value="id">ID 순서</option><option value="created_at">최초 생성 시간</option><option value="updated_at">최신 업데이트 시간</option>
    </select><button aria-label="정렬 방향" onClick={() => setAscending(value => !value)}>{ascending ? '↑ 오름차순' : '↓ 내림차순'}</button></div>
    {loading && <p role="status" className="state">사건 목록을 불러오는 중입니다.</p>}
    {error && <p role="alert" className="error">{error}</p>}
    {!loading && !error && !visible.length && <p className="state">{trash ? '삭제된 사건이 없습니다.' : '표시할 사건이 없습니다.'}</p>}
    <ul className="case-items">{visible.map(item => <li key={item.id} className="compact-row">
      <button className={selectedId === item.id && !trash ? 'case-item selected' : 'case-item'} onClick={() => !trash && onSelect(item.id)} aria-pressed={!trash && selectedId === item.id}>
        <span className="row-heading"><strong title={item.id}>{item.case_number}</strong><span className="user-status">{userStatus(item)}</span></span>
        <span className="row-title" title={item.summary || caseTitle(item)}>{caseTitle(item)}</span><small>{displayTime(item.updated_at)}</small>
      </button><button className="trash-action" aria-label={`${item.case_number} ${trash ? '복구' : '삭제'}`} onClick={() => openAdmin(item)}>{trash ? '복구' : '삭제'}</button>
    </li>)}</ul>
    <button className="trash-entry" onClick={() => { setTrash(value => !value); setItems([]); onSelect(null); }}>{trash ? '사건 목록으로' : '휴지통'}</button>
    {target && <div className="modal-backdrop"><form className="utility-dialog" role="dialog" aria-modal="true" aria-label={trash ? '사건 복구' : '사건 삭제'} onSubmit={submit}>
      <h2>{trash ? '사건 복구' : '사건 삭제'}</h2><p>{target.case_number} · {trash ? '사건 목록으로 복구합니다.' : '휴지통으로 이동합니다. 이후 복구할 수 있습니다.'}</p>
      <label>관리자 암호<input autoFocus type="password" autoComplete="off" required maxLength={128} value={password} onChange={e => setPassword(e.target.value)} /></label>
      {adminError && <p role="alert" className="error">{adminError}</p>}<div className="dialog-actions"><button type="button" disabled={busy} onClick={() => { setTarget(null); setPassword(''); }}>취소</button><button disabled={busy}>{busy ? '처리 중' : trash ? '복구' : '삭제'}</button></div>
    </form></div>}
  </aside>;
}
