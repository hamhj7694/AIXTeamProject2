import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Sparkles } from 'lucide-react';
import { Header } from './Header';
import { CaseRoleNav } from '../case/CaseRoleNav';
import { BankPersonalMemo } from '../../features/mvp-chat/BankPersonalMemo';
import { BankBookmarks } from '../../features/mvp-chat/BankBookmarks';

interface AppLayoutProps { children: React.ReactNode; }
const navItems = [{ label: '통화 진단', path: '/', icon: Sparkles }, { label: '보이스피싱 Case 목록', path: '/cases', icon: LayoutDashboard }];
export const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const location = useLocation(); const caseId = location.pathname.match(/^\/cases\/([^/]+)(?:\/|$)/)?.[1]; const bankView = Boolean(caseId && location.pathname.endsWith('/bank'));
  return <div className="min-h-screen bg-[#f5f7fb] text-slate-900"><Header/><main className="mx-auto w-full max-w-[1440px] px-4 pb-24 sm:px-6 lg:px-8 lg:pb-14">{children}</main>{bankView && caseId && <><BankBookmarks caseId={caseId}/><BankPersonalMemo caseId={caseId}/></>}<nav className="fixed bottom-0 left-0 right-0 z-40 border-t border-slate-200 bg-white/95 backdrop-blur lg:bottom-auto lg:left-6 lg:top-[88px] lg:w-56 lg:rounded-2xl lg:border lg:shadow-sm"><div className="mx-auto flex max-w-3xl justify-around gap-1 p-2 lg:block lg:max-w-none">{navItems.map(({ label, path, icon: Icon }) => { const active = path === '/' ? location.pathname === '/' : location.pathname.startsWith(path); return <Link key={path} to={path} className={`flex flex-1 items-center justify-center gap-2 rounded-xl px-3 py-2.5 text-xs font-semibold transition lg:mb-1 lg:justify-start lg:text-sm ${active ? 'bg-slate-900 text-white shadow-sm' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900'}`}><Icon size={17}/><span>{label}</span></Link>; })}</div>{caseId && <div className="hidden border-t border-slate-200 px-2 pb-2 lg:block"><CaseRoleNav caseId={caseId} compact/></div>}</nav></div>;
};
