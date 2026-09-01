import React from 'react';
import { Badge } from '../../../../components/ui/Badge';
import { Card } from '../../../../components/ui/Card';
import { managerRoomProgressMock } from '../../data/managerRoomMock';
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

export const CaseProgress: React.FC = () => {
  return (
    <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,0.72fr)_minmax(0,1.28fr)]">
      <div className="min-w-0 space-y-4">
        <Card className="rounded-xl border-blue-100 p-4 shadow-sm">
          <section aria-labelledby="case-progress-summary-title">
            <div className="flex flex-wrap items-center gap-2">
              <h2
                id="case-progress-summary-title"
                className="text-base font-extrabold text-slate-950"
              >
                사건 진행 요약
              </h2>
              <Badge variant="default">MVP Mock</Badge>
            </div>

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

            <p className="mt-3 border-t border-slate-100 pt-3 text-[11px] leading-5 text-slate-500">
              조사 체크와 최종 판단은 담당자가 직접 수행합니다.
            </p>
          </section>
        </Card>

        <InvestigationChecklist
          initialItems={managerRoomProgressMock.checklist}
        />
        <CaseMemo />
      </div>

      <div className="min-w-0">
        <ProgressTimeline events={managerRoomProgressMock.events} />
      </div>
    </div>
  );
};
