import React from 'react';
import { ArrowLeft, Construction } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';

export const FutureBankPage: React.FC = () => {
  const { caseId = 'VP-014' } = useParams();

  return (
    <AppLayout>
      <div className="mx-auto max-w-3xl py-8 lg:ml-64">
        <Link to={`/cases/${caseId}`} className="inline-flex items-center gap-1 text-sm font-bold text-slate-500">
          <ArrowLeft size={16} /> Case로 돌아가기
        </Link>
        <div className="mt-8 rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center shadow-sm">
          <div className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-slate-100 text-slate-600">
            <Construction size={22} />
          </div>
          <p className="mt-5 text-xs font-bold text-blue-600">FUTURE INTEGRATION</p>
          <h1 className="mt-2 text-2xl font-black">은행 Workspace 연결 예정</h1>
          <p className="mt-3 text-sm leading-6 text-slate-500">
            FE-05 화면은 현재 구현 범위에서 제외했습니다. 추후 같은 caseId를 사용해 Bank API와 Workspace를 연결할 수 있습니다.
          </p>
        </div>
      </div>
    </AppLayout>
  );
};
