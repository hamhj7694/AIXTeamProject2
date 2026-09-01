import React from 'react';
import { ArrowLeft, PhoneCall, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Badge } from '../../../components/ui/Badge';
import { Button } from '../../../components/ui/Button';
import { ManagerRoomCase } from '../types';

interface ManagerRoomHeaderProps {
  caseInfo: ManagerRoomCase;
  isClosed: boolean;
  onCallCustomer: () => void;
  onCloseCase: () => void;
}

export const ManagerRoomHeader: React.FC<ManagerRoomHeaderProps> = ({
  caseInfo,
  isClosed,
  onCallCustomer,
  onCloseCase,
}) => {
  return (
    <header className="rounded-t-xl border border-slate-200 bg-white shadow-sm">
      <div className="p-4 sm:p-5">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div className="min-w-0">
            <div className="mb-2.5 flex flex-wrap items-center gap-2">
              <Link
                to="/cases"
                className="inline-flex items-center gap-1 text-xs font-bold text-slate-500 transition hover:text-blue-600"
              >
                <ArrowLeft size={15} />
                Case로 돌아가기
              </Link>
              <span aria-hidden="true" className="text-slate-300">·</span>
              <span className="text-xs font-bold text-slate-400">
                CASE #{caseInfo.caseId}
              </span>
              <Badge variant="default">{caseInfo.dataSource}</Badge>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <h1 className="mr-1 truncate text-2xl font-black tracking-tight text-slate-950">
                {caseInfo.title}
              </h1>
              <Badge variant="danger">위험 {caseInfo.risk}</Badge>
              <Badge variant="warning">{caseInfo.status}</Badge>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 sm:justify-end">
            <Button
              type="button"
              variant="success"
              onClick={onCallCustomer}
              className="inline-flex items-center justify-center gap-1.5"
            >
              <PhoneCall size={16} />
              고객 통화하기
            </Button>
            <Button
              type="button"
              variant="danger"
              onClick={onCloseCase}
              className="inline-flex items-center justify-center gap-1.5"
            >
              {isClosed ? <RefreshCw size={16} /> : null}
              {isClosed ? '최종 리포트 갱신' : '사건 종료하기'}
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
};
