import React, { useEffect, useMemo, useState } from 'react';
import { ArrowDownUp, CalendarDays, Search, Trash2, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import { caseApi, type CaseRecord } from '../services/caseApi';

type SortKey = 'id' | 'transferred' | 'type' | 'amount' | 'status' | 'assignee' | 'createdAtRaw' | 'updatedAtRaw';
type VictimFilter = 'ALL' | 'UNKNOWN' | 'TRANSFERRED' | 'NOT_TRANSFERRED';

const displayId = (id: string) => `#${id.replace(/^VP-/, '')}`;
const workflowStatusLabel: Record<string, string> = {
  TRIAGE: '진행중', OPEN: '진행중', IN_PROGRESS: '진행중',
  PREVENT: '예방 진행중', RECOVERY: '피해 복구중',
  CLOSED: '처리완료', RESOLVED: '처리완료',
};
const displayWorkflowStatus = (status: string) => workflowStatusLabel[status] ?? '확인중';
const displayAmount = (amount?: string) => amount ?? '확인안됨';

export const CasesTablePage: React.FC = () => {
  const navigate = useNavigate();
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [query, setQuery] = useState('');
  const [victimFilter, setVictimFilter] = useState<VictimFilter>('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [updatedDate, setUpdatedDate] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('updatedAtRaw');
  const [descending, setDescending] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<CaseRecord | null>(null);
  const [deletePassword, setDeletePassword] = useState('');
  const [deleteConfirmed, setDeleteConfirmed] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  const [trashOpen, setTrashOpen] = useState(false);
  const [trashedCases, setTrashedCases] = useState<CaseRecord[]>([]);

  const load = () => {
    setLoading(true); setError('');
    caseApi.list()
      .then(setCases)
      .catch((reason) => setError(reason instanceof Error ? reason.message : 'Case 목록을 불러오지 못했습니다.'))
      .finally(() => setLoading(false));
  };
  useEffect(() => { load(); const timer = window.setInterval(load, 15_000); return () => window.clearInterval(timer); }, []);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setDescending((current) => !current);
    else { setSortKey(key); setDescending(key === 'createdAtRaw'); }
  };

  const availableStatuses = useMemo(
    () => Array.from(new Set(cases.map((item) => item.status))).sort(),
    [cases],
  );
  const rows = useMemo(() => cases.filter((item) => {
    const matchesQuery = [item.id, item.type, item.status, displayWorkflowStatus(item.status), item.assignee ?? '', item.summary]
      .join(' ').toLowerCase().includes(query.toLowerCase().trim());
    const matchesVictim = victimFilter === 'ALL'
      || (victimFilter === 'TRANSFERRED' && item.transferred === true)
      || (victimFilter === 'NOT_TRANSFERRED' && item.transferred === false)
      || (victimFilter === 'UNKNOWN' && item.transferred === null);
    const matchesStatus = statusFilter === 'ALL' || item.status === statusFilter;
    const itemDate = new Date(item.updatedAtRaw).toLocaleDateString('sv-SE');
    return matchesQuery && matchesVictim && matchesStatus && (!updatedDate || itemDate === updatedDate);
  }).sort((a, b) => {
    const value = (item: CaseRecord) => {
      if (sortKey === 'id') return Number(item.id.replace(/^VP-/, ''));
      if (sortKey === 'transferred') return item.transferred === true ? 2 : item.transferred === false ? 1 : 0;
      if (sortKey === 'amount') return Number(item.amount?.replace(/[^0-9]/g, '') ?? 0);
      return String(item[sortKey] ?? '');
    };
    const left = value(a); const right = value(b);
    const order = typeof left === 'number' && typeof right === 'number'
      ? left - right
      : String(left).localeCompare(String(right), 'ko');
    return descending ? -order : order;
  }), [cases, descending, query, sortKey, statusFilter, updatedDate, victimFilter]);

  const header = (label: string, key: SortKey, width = '') => (
    <th className={`whitespace-nowrap px-2 py-2.5 ${width}`}>
      <button onClick={() => toggleSort(key)} className="inline-flex items-center gap-1 font-bold hover:text-slate-900">
        {label}<ArrowDownUp size={12} className={sortKey === key ? 'text-blue-600' : ''} />
      </button>
    </th>
  );
  const confirmDelete = async () => {
    if (!deleteTarget) return;
    if (!deleteConfirmed) {
      try { await caseApi.verifyAdministratorPassword(deletePassword); setDeleteError(''); setDeleteConfirmed(true); }
      catch (reason) { setDeleteError(reason instanceof Error ? reason.message : '관리자 비밀번호가 올바르지 않습니다.'); }
      return;
    }
    try { await caseApi.permanentlyDelete(deleteTarget.id, deletePassword); setDeleteTarget(null); setDeletePassword(''); setDeleteConfirmed(false); load(); }
    catch (reason) { setDeleteError(reason instanceof Error ? reason.message : 'Case를 삭제하지 못했습니다.'); }
  };
  const openTrash = async () => { try { setTrashedCases(await caseApi.listTrash()); setTrashOpen(true); } catch (reason) { setError(reason instanceof Error ? reason.message : '휴지통을 불러오지 못했습니다.'); } };
  const restoreCase = async (caseId: string) => { try { await caseApi.restoreFromTrash(caseId); setTrashedCases(await caseApi.listTrash()); load(); } catch (reason) { setError(reason instanceof Error ? reason.message : 'Case를 복구하지 못했습니다.'); } };

  return (
    <AppLayout>
      <div className="mx-auto max-w-6xl py-8 lg:ml-64">
        <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="mb-2 text-xs font-bold text-blue-600">02 / SHARED CASE</p>
            <h1 className="text-2xl font-black">보이스피싱 Case 목록</h1>
            <p className="mt-2 text-sm text-slate-500">로컬 DB에서 실제로 생성된 보이스피싱 Case만 표시합니다.</p>
          </div>
          <div className="flex gap-2"><button onClick={openTrash} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-slate-700">🗑️ 휴지통</button><button onClick={() => navigate('/')} className="rounded-lg bg-slate-900 px-3 py-2 text-xs font-bold text-white">통화 진단</button></div>
        </div>

        <div className="overflow-hidden rounded-xl border border-slate-300 bg-white shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 p-3">
            <div className="flex flex-wrap items-center gap-3">
              <label className="flex items-center gap-2 text-xs font-bold text-slate-600">
                피해 여부
                <select value={victimFilter} onChange={(event) => setVictimFilter(event.target.value as VictimFilter)} className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium outline-none focus:border-blue-500">
                  <option value="ALL">전체</option><option value="UNKNOWN">확인안됨</option><option value="TRANSFERRED">피해 발생</option><option value="NOT_TRANSFERRED">피해 없음</option>
                </select>
              </label>
              <label className="flex items-center gap-2 text-xs font-bold text-slate-600">
                업무 진행 상태
                <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium outline-none focus:border-blue-500">
                  <option value="ALL">전체</option>
                  {availableStatuses.map((status) => <option key={status} value={status}>{displayWorkflowStatus(status)}</option>)}
                </select>
              </label>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {(query || victimFilter !== 'ALL' || statusFilter !== 'ALL' || updatedDate) && <button onClick={() => { setQuery(''); setVictimFilter('ALL'); setStatusFilter('ALL'); setUpdatedDate(''); }} className="rounded-md px-2 py-1.5 text-xs font-bold text-blue-700 hover:bg-blue-50">필터 초기화</button>}
              <label className="relative"><Search size={14} className="absolute left-2.5 top-2 text-slate-400" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="검색" className="w-28 rounded-md border border-slate-200 py-1.5 pl-7 pr-2 text-xs outline-none focus:border-blue-500" /></label>
              <label className="relative"><CalendarDays size={14} className="pointer-events-none absolute left-2.5 top-2 text-slate-400" /><input type="date" value={updatedDate} onChange={(event) => setUpdatedDate(event.target.value)} aria-label="최근 업데이트 날짜" className="w-40 rounded-md border border-slate-200 py-1.5 pl-7 pr-2 text-xs outline-none focus:border-blue-500" /></label>
            </div>
          </div>
          <div className="border-b border-slate-100 px-4 py-2 text-xs font-semibold text-slate-500">검색 결과 {rows.length}건 · 15초마다 자동 갱신</div>

          <div className="overflow-x-auto">
            <table className="min-w-[1000px] w-full table-fixed text-left text-xs">
              <colgroup>
                <col className="w-[5%]" />
                <col className="w-[8%]" />
                <col className="w-[9%]" />
                <col className="w-[10%]" />
                <col className="w-[12%]" />
                <col className="w-[12%]" />
                <col className="w-[11%]" />
                <col className="w-[13%]" />
                <col className="w-[17%]" />
                <col className="w-[3%]" />
              </colgroup>
              <thead className="bg-slate-50 text-[11px] text-slate-500">
                <tr>
                  {header('ID', 'id', 'w-10')}
                  {header('담당자', 'assignee', 'w-24')}
                  {header('피해 여부', 'transferred', 'w-28')}
                  {header('피해 금액', 'amount', 'w-32')}
                  {header('사기 유형', 'type', 'w-40')}
                  {header('업무 진행 상태', 'status', 'w-36')}
                  {header('최초 생성일', 'createdAtRaw', 'w-32')}
                  {header('최근 업데이트', 'updatedAtRaw', 'w-40')}
                  <th className="px-2 py-2.5 font-bold">사건 요약</th>
                  <th className="px-2 py-2.5"><span className="sr-only">삭제</span></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((item) => (
                  <tr key={item.id} onClick={() => navigate(`/cases/${item.id}`)} className="cursor-pointer border-t border-slate-100 transition hover:bg-blue-50/60">
                    <td className="px-2 py-2.5 font-black text-slate-900">{displayId(item.id)}</td>
                    <td className="truncate px-2 py-2.5 font-semibold text-slate-700" title={item.assignee ?? '미배정'}>{item.assignee ?? '미배정'}</td>
                    <td className="px-2 py-2.5 font-semibold">{item.transferred === true ? '피해 발생' : item.transferred === false ? '피해 없음' : '확인안됨'}</td>
                    <td className="px-2 py-2.5 font-semibold text-slate-700">{displayAmount(item.amount)}</td>
                    <td className="truncate px-2 py-2.5 font-semibold text-slate-700" title={item.type || '확인안됨'}>{item.type || '확인안됨'}</td>
                    <td className="px-2 py-2.5"><span className="rounded-md bg-blue-50 px-1.5 py-0.5 font-bold text-blue-700">{displayWorkflowStatus(item.status)}</span></td>
                    <td className="px-2 py-2.5 text-slate-500">{item.createdAt}</td>
                    <td className="px-2 py-2.5 text-slate-500">{item.updatedAt}</td>
                    <td className="truncate px-2 py-2.5 text-slate-600" title={item.summary}>{item.summary}</td>
                    <td className="px-1.5 py-2.5"><button aria-label={`${displayId(item.id)} 삭제`} onClick={(event) => { event.stopPropagation(); setDeleteTarget(item); setDeletePassword(''); setDeleteError(''); setDeleteConfirmed(false); }} className="rounded-lg p-1 text-slate-400 hover:bg-rose-50 hover:text-rose-700"><Trash2 size={15}/></button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {loading && <div className="p-10 text-center text-sm text-slate-500">생성된 Case를 불러오는 중입니다.</div>}
          {!loading && error && <div className="p-10 text-center text-sm text-rose-600">{error}</div>}
          {!loading && !error && rows.length === 0 && <div className="p-10 text-center text-sm text-slate-500">조건에 맞는 보이스피싱 Case가 없습니다.</div>}
        </div>
      </div>
      {deleteTarget && <div className="fixed inset-0 z-50 grid place-items-center bg-slate-900/35 p-4"><section className="w-full max-w-sm rounded-2xl bg-white p-5 shadow-xl"><div className="flex items-center justify-between"><h2 className="font-black">총괄관리자 Case 삭제</h2><button onClick={() => setDeleteTarget(null)}><X size={18}/></button></div>{deleteConfirmed ? <><p className="mt-3 text-sm leading-6 text-rose-700">정말 {displayId(deleteTarget.id)} Case를 휴지통으로 이동하겠습니까?</p>{deleteError && <p className="mt-3 rounded-lg bg-rose-50 p-2.5 text-xs font-semibold text-rose-700">{deleteError}</p>}<div className="mt-5 flex justify-end gap-2"><button onClick={() => setDeleteConfirmed(false)} className="rounded-xl border px-4 py-2 text-sm font-bold">취소</button><button onClick={confirmDelete} className="rounded-xl bg-rose-600 px-4 py-2 text-sm font-bold text-white">삭제</button></div></> : <><p className="mt-3 text-sm text-slate-600">총괄관리자 비밀번호를 입력하면 다음 확인 단계로 이동합니다.</p><input type="password" autoFocus value={deletePassword} onChange={(event) => { setDeletePassword(event.target.value); setDeleteError(''); }} placeholder="관리자 비밀번호" className="mt-4 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm"/>{deleteError && <p className="mt-3 rounded-lg bg-rose-50 p-2.5 text-xs font-semibold text-rose-700">{deleteError}</p>}<div className="mt-5 flex justify-end gap-2"><button onClick={() => setDeleteTarget(null)} className="rounded-xl border px-4 py-2 text-sm font-bold">취소</button><button disabled={!deletePassword} onClick={confirmDelete} className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-bold text-white disabled:opacity-40">삭제</button></div></>}</section></div>}
      {trashOpen && <div className="fixed inset-0 z-50 grid place-items-center bg-slate-900/35 p-4"><section className="w-full max-w-lg rounded-2xl bg-white p-5 shadow-xl"><div className="flex items-center justify-between"><h2 className="font-black">🗑️ Case 휴지통</h2><button onClick={() => setTrashOpen(false)}><X size={18}/></button></div><p className="mt-2 text-xs text-slate-500">휴지통의 Case는 복구할 수 있습니다.</p><div className="mt-4 max-h-80 space-y-2 overflow-y-auto">{trashedCases.length ? trashedCases.map((item) => <div key={item.id} className="flex items-center gap-3 rounded-xl border p-3"><div className="min-w-0 flex-1"><p className="font-bold">{displayId(item.id)} · {item.type}</p><p className="mt-1 truncate text-xs text-slate-500">{item.summary}</p></div><button onClick={() => restoreCase(item.id)} className="rounded-lg border px-3 py-2 text-xs font-bold">복구</button></div>) : <p className="rounded-xl bg-slate-50 p-8 text-center text-sm text-slate-500">휴지통이 비어 있습니다.</p>}</div></section></div>}
    </AppLayout>
  );
};
