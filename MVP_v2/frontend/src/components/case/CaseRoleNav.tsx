import React from 'react';
import { BadgeCheck, Building2, ClipboardList, UserRound } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

interface CaseRoleNavProps { caseId: string; compact?: boolean; }

const items = [
  { key: '', label: 'Case 개요', icon: ClipboardList },
  { key: 'bank', label: '은행 화면', icon: Building2 },
  { key: 'customer', label: '소비자 화면', icon: UserRound },
  { key: 'verify', label: '기타 / 검증', icon: BadgeCheck },
];

export const CaseRoleNav: React.FC<CaseRoleNavProps> = ({ caseId, compact = false }) => {
  const location = useLocation();
  return <nav aria-label="Case 전용 화면 이동" className={compact ? 'grid w-full grid-cols-4 gap-1 border-t border-slate-200 pt-2 lg:grid-cols-1' : 'mb-6 flex flex-wrap gap-2 rounded-2xl border border-slate-200 bg-white p-2 shadow-sm'}>
    {items.map(({ key, label, icon: Icon }) => {
      const path = key ? `/cases/${caseId}/${key}` : `/cases/${caseId}`;
      const active = location.pathname === path;
      return <Link key={key} to={path} className={`inline-flex ${compact ? 'justify-center lg:justify-start' : 'flex-1 justify-center'} items-center gap-1 rounded-xl px-2 py-2.5 text-[10px] font-bold transition sm:text-xs ${active ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-100'}`}><Icon size={15}/>{label}</Link>;
    })}
  </nav>;
};
