import React from 'react';
import { LockKeyhole, ShieldCheck } from 'lucide-react';
import { useLocation } from 'react-router-dom';
import { CustomerBookmarks } from '../../features/mvp-chat/CustomerBookmarks';

interface CustomerLayoutProps { children: React.ReactNode; }

/**
 * Customer-facing shell. It deliberately omits bank navigation, Case facts,
 * verification tools, and staff identity controls.
 */
export const CustomerLayout: React.FC<CustomerLayoutProps> = ({ children }) => {
  const location = useLocation();
  const caseId = location.pathname.match(/^\/cases\/([^/]+)\/customer$/)?.[1];

  return <div className="min-h-screen bg-[#f5f7fb] text-slate-900">
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-[1280px] items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-2.5">
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-blue-600 text-white"><ShieldCheck size={20}/></div>
          <div><p className="text-sm font-extrabold tracking-tight">보이스피싱 안전 상담</p><p className="text-[10px] font-medium text-slate-400">은행 상담팀과 연결된 고객 전용 화면</p></div>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1.5 text-[11px] font-bold text-emerald-700"><LockKeyhole size={13}/> 고객 정보 보호 중</span>
      </div>
    </header>
    <main className="mx-auto w-full max-w-[1280px] px-4 pb-24 sm:px-6 lg:px-8">{children}</main>
    {caseId && <CustomerBookmarks caseId={caseId}/>} 
  </div>;
};
