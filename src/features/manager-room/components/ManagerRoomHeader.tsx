import React from 'react';
import { Badge } from '../../../components/ui/Badge';
import { Button } from '../../../components/ui/Button';
import { ManagerRoomCase } from '../types';

interface ManagerRoomHeaderProps {
  caseInfo: ManagerRoomCase;
  customerViewActive: boolean;
  onOpenCustomerView: () => void;
}

export const ManagerRoomHeader: React.FC<ManagerRoomHeaderProps> = ({
  caseInfo,
  customerViewActive,
  onOpenCustomerView,
}) => {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto max-w-7xl px-4 py-5 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex min-w-0 flex-col gap-4 sm:flex-row sm:items-center">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled
              title="사건 목록 Route가 연결되면 사용할 수 있습니다."
              className="shrink-0"
            >
              ← 사건 목록
            </Button>

            <div className="min-w-0 border-slate-200 sm:border-l sm:pl-5">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <span className="text-sm font-semibold text-slate-500">
                  {caseInfo.caseId}
                </span>
                <Badge variant="default">{caseInfo.dataSource}</Badge>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="mr-1 truncate text-xl font-bold text-slate-950">
                  {caseInfo.title}
                </h1>
                <Badge variant="danger" size="md">
                  위험 {caseInfo.risk}
                </Badge>
                <Badge variant="warning" size="md">
                  {caseInfo.status}
                </Badge>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 sm:justify-end">
            <Button
              type="button"
              variant={customerViewActive ? 'primary' : 'secondary'}
              onClick={onOpenCustomerView}
              aria-pressed={customerViewActive}
            >
              고객 ROOM 보기
            </Button>
            <Button
              type="button"
              variant="danger"
              disabled
              title="사건 종료 기능은 STEP 6에서 구현합니다."
            >
              사건 종료하기
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
};
