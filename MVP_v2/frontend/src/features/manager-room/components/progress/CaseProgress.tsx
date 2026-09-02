import React, { useState } from 'react';
import { Badge } from '../../../../components/ui/Badge';
import { Card } from '../../../../components/ui/Card';
import { cn } from '../../../../utils/helpers';
import {
  ManagerRoomChecklistItem,
  ManagerRoomMemoItem,
  ManagerRoomProgressPhase,
  ManagerRoomProgressMock,
} from '../../types';
import { CaseMemo } from './CaseMemo';
import { InvestigationChecklist } from './InvestigationChecklist';
import { ProgressTimeline } from './ProgressTimeline';

const progressSteps: Array<{
  id: ManagerRoomProgressPhase;
  number: number;
  title: string;
  status: string;
  badgeVariant: 'success' | 'primary' | 'default';
}> = [
  {
    id: 'past',
    number: 1,
    title: '사건 탐지 및 생성',
    status: '완료',
    badgeVariant: 'success',
  },
  {
    id: 'current',
    number: 2,
    title: '담당자 조사',
    status: '진행 중',
    badgeVariant: 'primary',
  },
  {
    id: 'next',
    number: 3,
    title: '고객 확인 및 최종 판단',
    status: '예정',
    badgeVariant: 'default',
  },
];

interface CaseProgressProps {
  progress: ManagerRoomProgressMock;
  checklistItems: ManagerRoomChecklistItem[];
  onChecklistItemsChange: React.Dispatch<
    React.SetStateAction<ManagerRoomChecklistItem[]>
  >;
  memos: ManagerRoomMemoItem[];
  onMemosChange: React.Dispatch<React.SetStateAction<ManagerRoomMemoItem[]>>;
}

export const CaseProgress: React.FC<CaseProgressProps> = ({
  progress,
  checklistItems,
  onChecklistItemsChange,
  memos,
  onMemosChange,
}) => {
  const [selectedProgressStep, setSelectedProgressStep] =
    useState<ManagerRoomProgressPhase>('current');
  const selectedStep = progressSteps.find(
    (step) => step.id === selectedProgressStep
  ) ?? progressSteps[1];

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
            <Badge variant="default">General API</Badge>
          </div>

          <div className="p-4 sm:p-5">
            <h3 className="text-sm font-extrabold text-slate-900">
              단계 선택
            </h3>
            <div
              role="tablist"
              aria-label="사건 진행 단계"
              className="mt-3 grid gap-2 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3"
            >
              {progressSteps.map((step) => {
                const selected = step.id === selectedProgressStep;

                return (
                  <button
                    key={step.id}
                    type="button"
                    role="tab"
                    id={`progress-step-${step.id}`}
                    aria-selected={selected}
                    aria-controls="selected-progress-timeline"
                    onClick={() => setSelectedProgressStep(step.id)}
                    className={cn(
                      'min-w-0 rounded-lg border px-3 py-3 text-left transition-colors focus:outline-none focus:ring-2 focus:ring-blue-200',
                      selected
                        ? 'border-blue-300 bg-blue-50 shadow-sm'
                        : 'border-slate-200 bg-white hover:border-blue-200 hover:bg-slate-50'
                    )}
                  >
                    <span
                      className={cn(
                        'block text-[11px] font-bold',
                        selected ? 'text-blue-700' : 'text-slate-500'
                      )}
                    >
                      {step.number}단계
                    </span>
                    <span
                      className={cn(
                        'mt-1 block text-sm font-extrabold leading-5',
                        selected ? 'text-blue-950' : 'text-slate-900'
                      )}
                    >
                      {step.title}
                    </span>
                    <Badge variant={step.badgeVariant} className="mt-2">
                      {step.status}
                    </Badge>
                  </button>
                );
              })}
            </div>
            <p className="mt-3 text-[11px] leading-5 text-slate-500">
              조사 체크와 최종 판단은 담당자가 직접 수행합니다.
            </p>
          </div>

          <div
            id="selected-progress-timeline"
            role="tabpanel"
            aria-labelledby={`progress-step-${selectedProgressStep}`}
            className="border-t border-slate-200"
          >
            <ProgressTimeline
              events={progress.events}
              selectedPhase={selectedProgressStep}
              selectedStepTitle={selectedStep.title}
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
