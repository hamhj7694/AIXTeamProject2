import React, { useMemo, useState } from 'react';
import { CalendarDays, Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import { CaseRecord, MOCK_CASES } from '../data/mock/caseData';

const displayId = (id: string) => id.replace(/^VP-/, '');
const victimNames: Record<string, string> = { 'VP-099': '테스트', 'VP-014': '엄정희', 'VP-013': '김민수', 'VP-012': '이서윤' };
const maskName = (name: string) => name.length >= 3 ? `${name[0]}${'*'.repeat(name.length - 2)}${name[name.length - 1]}` : name;
const normalizeSearch = (value: string) => value.toLowerCase().replace(/[\s,._-]/g, '');
const searchText = (item: CaseRecord) => normalizeSearch([item.id, displayId(item.id), victimNames[item.id], maskName(victimNames[item.id] ?? ''), item.type, item.risk, item.status, item.transferred ? '송금 Y 피해 Y' : '송금 N 피해 N', item.amount || '-', item.summary, item.createdAt, item.updatedAt].join(' '));
const matchesDate = (createdAt: string, date: string) => {
  if (!date) return true;
  const selected = new Date(`${date}T00:00:00`);
  const today = new Date();
  const difference = Math.round((new Date(today.toDateString()).getTime() - selected.getTime()) / 86400000);
  return difference === 0 ? createdAt.includes('오늘') : difference === 1 ? createdAt.includes('어제') : false;
};

const TableStatus: React.FC<{ status: CaseRecord['status'] }> = ({ status }) => (
  <span className="inline-flex rounded-md bg-blue-50 px-2 py-1 text-[11px] font-bold text-blue-700">{status}</span>
);

export const CasesTablePage: React.FC = () => {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [transferFilter, setTransferFilter] = useState('전체');
  const [statusFilter, setStatusFilter] = useState('전체');
  const [date, setDate] = useState('');
  const statusOptions: CaseRecord['status'][] = ['확인중', '해결 완료', '후속조치'];
  const rows = useMemo(() => MOCK_CASES.filter((item) => {
    const transferMatch = transferFilter === '전체' || (transferFilter === '송금 Y' ? item.transferred : !item.transferred);
    const statusMatch = statusFilter === '전체' || item.status === statusFilter;
    return searchText(item).includes(normalizeSearch(query)) && transferMatch && statusMatch && matchesDate(item.createdAt, date);
  }), [date, query, statusFilter, transferFilter]);

  return <AppLayout><div className="mx-auto max-w-6xl py-8 lg:ml-64">
    <div className="mb-5 flex items-end justify-between gap-4"><div><p className="mb-2 text-xs font-bold text-blue-600">02 / SHARED CASE</p><h1 className="text-2xl font-black">Cases</h1><p className="mt-2 text-sm text-slate-500">표에서 사건 정보를 확인하고 행을 누르면 사건 요약 페이지로 이동합니다.</p></div><button onClick={() => navigate('/')} className="rounded-lg bg-slate-900 px-3 py-2 text-xs font-bold text-white">통화 진단</button></div>
    <div className="overflow-hidden rounded-xl border border-slate-300 bg-white shadow-sm">
      <div className="flex flex-col gap-3 border-b border-slate-200 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"><div className="flex flex-wrap items-center gap-2"><span className="text-xs font-extrabold text-slate-600">피해 여부</span><select value={transferFilter} onChange={(e) => setTransferFilter(e.target.value)} className="rounded-md border border-slate-200 px-2 py-1.5 text-xs font-semibold outline-none"><option>전체</option><option>송금 Y</option><option>송금 N</option></select><span className="ml-1 text-xs font-extrabold text-slate-600">진행 상태</span><select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="rounded-md border border-slate-200 px-2 py-1.5 text-xs font-semibold outline-none"><option>전체</option>{statusOptions.map((status) => <option key={status}>{status}</option>)}</select></div><div className="flex flex-wrap gap-2"><label className="relative"><Search size={13} className="absolute left-2.5 top-2 text-slate-400"/><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="검색" className="w-32 rounded-md border border-slate-200 py-1.5 pl-7 pr-2 text-xs outline-none focus:border-blue-500"/></label><label className="relative"><CalendarDays size={13} className="absolute left-2.5 top-2 text-slate-400"/><input type="date" value={date} onChange={(e) => setDate(e.target.value)} aria-label="날짜 검색" className="w-36 rounded-md border border-slate-200 py-1.5 pl-7 pr-1 text-xs outline-none focus:border-blue-500"/></label></div></div>
      <div className="overflow-x-auto"><table className="min-w-[1160px] w-full table-fixed text-left text-xs"><thead className="bg-slate-50 text-[11px] font-bold text-slate-500"><tr><th className="w-[7%] px-3 py-3">ID</th><th className="w-[10%] px-3 py-3">피해자 이름</th><th className="w-[9%] px-3 py-3">피해 여부</th><th className="w-[11%] px-3 py-3">유형</th><th className="w-[10%] px-3 py-3">피해 금액</th><th className="w-[12%] px-3 py-3">업무진행상태</th><th className="w-[11%] px-3 py-3">최초 생성시간</th><th className="w-[11%] px-3 py-3">최근 업데이트</th><th className="w-[19%] px-3 py-3">사건 요약</th></tr></thead><tbody>{rows.map((item) => <tr key={item.id} tabIndex={0} onClick={() => navigate(`/cases/${item.id}`)} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') navigate(`/cases/${item.id}`); }} className="cursor-pointer border-t border-slate-100 transition hover:bg-blue-50/60 focus:bg-blue-50 focus:outline-none"><td className="px-3 py-3 font-bold">{displayId(item.id)}</td><td className="px-3 py-3 font-semibold text-slate-700">{maskName(victimNames[item.id] ?? '이름 없음')}</td><td className={`px-3 py-3 font-semibold ${item.transferred ? 'text-rose-600' : 'text-slate-600'}`}>{item.transferred ? '송금 Y' : '송금 N'}</td><td className="px-3 py-3 font-semibold">{item.type}</td><td className="px-3 py-3">{item.amount || '-'}</td><td className="px-3 py-3"><TableStatus status={item.status}/></td><td className="px-3 py-3 text-slate-500">{item.createdAt}</td><td className="px-3 py-3 text-slate-500">{item.updatedAt}</td><td className="max-w-xs truncate px-3 py-3 text-slate-600" title={item.summary}>{item.summary}</td></tr>)}</tbody></table></div>
      {rows.length === 0 && <div className="p-10 text-center text-sm text-slate-500">조건에 맞는 Case가 없습니다.</div>}
    </div><p className="mt-3 text-xs text-slate-400">Case 행을 선택하면 해당 사건의 요약 페이지로 이동합니다.</p>
  </div></AppLayout>;
};
