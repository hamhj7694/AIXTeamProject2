import React from 'react';
import { Badge } from '../../../../components/ui/Badge';
import { Card } from '../../../../components/ui/Card';
import { managerRoomProgressMock } from '../../data/managerRoomMock';
import { ManagerRoomChecklistItem, ManagerRoomMemoItem } from '../../types';
import { CaseMemo } from './CaseMemo';
import { InvestigationChecklist } from './InvestigationChecklist';
import { ProgressTimeline } from './ProgressTimeline';

const progressSummary = [
  {
    label: '현재 단계',
    value: managerRoomProgressMock.currentStage,
    rowClassName: 'border-blue-100 bg-blue-50/70',
    labelClassName: 'text-blue-600',
    valueClassName: 'text-blue-950',
  },
  {
    label: '현재 확인 중',
    value: managerRoomProgressMock.currentFocus,
    rowClassName: 'border-slate-200 bg-white',
    labelClassName: 'text-slate-500',
    valueClassName: 'text-slate-950',
  },
  {
    label: '다음 단계',
    value: managerRoomProgressMock.nextStage,
    rowClassName: 'border-slate-100 bg-slate-50',
    labelClassName: 'text-slate-400',
    valueClassName: 'text-slate-700',
  },
];

interface CaseProgressProps {
  checklistItems: ManagerRoomChecklistItem[];
  onChecklistItemsChange: React.Dispatch<
    React.SetStateAction<ManagerRoomChecklistItem[]>
  >;
  memos: ManagerRoomMemoItem[];
  onMemosChange: React.Dispatch<React.SetStateAction<ManagerRoomMemoItem[]>>;
}

export const CaseProgress: React.FC<CaseProgressProps> = ({
  checklistItems,
  onChecklistItemsChange,
  memos,
  onMemosChange,
}) => {
  return (
    <div className="grid gap-4 lg:grid-cols-2 lg:items-stretch">
      <Card className="min-w-0 overflow-hidden rounded-xl border-slate-200 p-0 shadow-sm">
        <section aria-labelledby="case-progress-status-title">
          <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 px-4 py-4 sm:px-5">
            <h2
              id="case-progress-status-title"
              className="text-lg font-black text-slate-950"
            >
              사건 진행 현황
            </h2>
            <Badge variant="default">MVP Mock</Badge>
          </div>

          <div className="p-4 sm:p-5">
            <h3 className="text-sm font-extrabold text-slate-900">
              사건 진행 요약
            </h3>
            <div className="mt-3 space-y-2">
              {progressSummary.map((summary) => (
                <div
                  key={summary.label}
                  className={`rounded-lg border px-3 py-2.5 ${summary.rowClassName}`}
                >
                  <p className={`text-[11px] font-bold ${summary.labelClassName}`}>
                    {summary.label}
                  </p>
                  <p className={`mt-1 text-sm font-extrabold leading-5 ${summary.valueClassName}`}>
                    {summary.value}
                  </p>
                </div>
              ))}
            </div>
            <p className="mt-3 text-[11px] leading-5 text-slate-500">
              조사 체크와 최종 판단은 담당자가 직접 수행합니다.
            </p>
          </div>

          <div className="border-t border-slate-200">
            <ProgressTimeline
              events={managerRoomProgressMock.events}
              embedded
              scrollable
            />
          </div>
        </section>
      </Card>

      <Card className="min-w-0 rounded-xl border-slate-200 p-0 shadow-sm">
        <section aria-labelledby="investigation-and-memo-title">
          <div className="border-b border-slate-200 px-4 py-4 sm:px-5">
            <h2
              id="investigation-and-memo-title"
              className="text-lg font-black text-slate-950"
            >
              조사 및 메모
            </h2>
          </div>

          <div className="p-4 sm:p-5">
            <InvestigationChecklist
              items={checklistItems}
              onItemsChange={onChecklistItemsChange}
              embedded
            />
          </div>

          <div className="border-t border-slate-200 p-4 sm:p-5">
            <CaseMemo
              memos={memos}
              onMemosChange={onMemosChange}
              embedded
              scrollableList
            />
          </div>
        </section>
      </Card>
    </div>
  );
};
