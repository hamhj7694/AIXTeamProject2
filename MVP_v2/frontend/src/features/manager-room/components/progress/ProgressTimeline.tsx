import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { Badge } from '../../../../components/ui/Badge';
import { Card } from '../../../../components/ui/Card';
import { cn } from '../../../../utils/helpers';
import {
  ManagerRoomProgressEvent,
  ManagerRoomProgressPhase,
} from '../../types';

interface ProgressTimelineProps {
  events: ManagerRoomProgressEvent[];
  selectedPhase: ManagerRoomProgressPhase;
  selectedStepTitle: string;
  embedded?: boolean;
  scrollable?: boolean;
}

type EventFilter = 'key' | 'all';

const phaseStyle: Record<
  ManagerRoomProgressPhase,
  { dotClassName: string; description: string }
> = {
  past: {
    dotClassName: 'bg-emerald-500',
    description: '완료된 탐지·생성 이벤트를 확인합니다.',
  },
  current: {
    dotClassName: 'bg-blue-600 ring-4 ring-blue-100',
    description: '현재 담당자가 조사 중인 이벤트를 확인합니다.',
  },
  next: {
    dotClassName: 'bg-slate-300',
    description: '고객 확인 이후 예정된 이벤트를 확인합니다.',
  },
};

export const ProgressTimeline: React.FC<ProgressTimelineProps> = ({
  events,
  selectedPhase,
  selectedStepTitle,
  embedded = false,
  scrollable = false,
}) => {
  const [eventFilter, setEventFilter] = useState<EventFilter>('key');
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);
  const stepEvents = events.filter((event) => event.phase === selectedPhase);
  const visibleEvents =
    eventFilter === 'key'
      ? stepEvents.filter((event) => event.isKey)
      : stepEvents;
  const emptyMessage = stepEvents.length
    ? '이 단계에 표시할 핵심 이벤트가 없습니다. 전체 이벤트를 확인해 주세요.'
    : selectedPhase === 'next'
      ? '이 단계는 아직 시작되지 않았습니다.'
      : '이 단계에서 아직 기록된 사건 이벤트가 없습니다.';

  const content = (
    <section aria-labelledby="progress-timeline-title">
      <div className="flex flex-col gap-3 border-b border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2
              id="progress-timeline-title"
              className="text-base font-extrabold text-slate-950"
            >
              {selectedStepTitle} Timeline
            </h2>
            <Badge variant="default">Case Event API</Badge>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {phaseStyle[selectedPhase].description}
          </p>
        </div>

        <div
          className="inline-flex w-fit rounded-lg border border-slate-200 bg-slate-50 p-1"
          aria-label="Timeline 이벤트 필터"
        >
          {([
            ['key', '핵심 이벤트'],
            ['all', '전체 이벤트'],
          ] as const).map(([filter, label]) => {
            const active = eventFilter === filter;

            return (
              <button
                key={filter}
                type="button"
                onClick={() => setEventFilter(filter)}
                aria-pressed={active}
                className={cn(
                  'rounded-md px-3 py-1.5 text-xs font-bold transition',
                  active
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-500 hover:bg-white hover:text-slate-900'
                )}
              >
                {label}
              </button>
            );
          })}
        </div>
      </div>

      <div
        className={cn(
          'px-4 py-4 sm:px-5',
          scrollable &&
            'max-h-[420px] overflow-y-auto overscroll-contain [scrollbar-width:thin]'
        )}
      >
        {visibleEvents.length ? (
          <div className="divide-y divide-slate-200/80">
            {visibleEvents.map((event) => {
              const expanded = expandedEventId === event.id;

              return (
                <div key={event.id} className="py-3 first:pt-1 last:pb-1">
                  <div className="flex items-start gap-3">
                    <span
                      aria-hidden="true"
                      className={cn(
                        'mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full',
                        phaseStyle[selectedPhase].dotClassName
                      )}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:justify-between">
                        <div className="flex flex-wrap items-center gap-2">
                          <p
                            className={cn(
                              'text-sm text-slate-900',
                              event.isKey ? 'font-extrabold' : 'font-semibold'
                            )}
                          >
                            {event.title}
                          </p>
                          <span className="text-[11px] font-semibold text-slate-400">
                            {event.label}
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() =>
                            setExpandedEventId(expanded ? null : event.id)
                          }
                          aria-expanded={expanded}
                          className="inline-flex w-fit items-center gap-1 text-xs font-bold text-slate-500 hover:text-blue-700"
                        >
                          세부 보기
                          <ChevronDown
                            size={14}
                            className={cn(
                              'transition-transform',
                              expanded && 'rotate-180'
                            )}
                          />
                        </button>
                      </div>
                      {expanded && (
                        <p className="mt-2 border-l-2 border-slate-200 pl-3 text-xs leading-5 text-slate-600">
                          {event.description}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-center">
            <p className="text-sm leading-6 text-slate-500">{emptyMessage}</p>
          </div>
        )}
      </div>
    </section>
  );

  return embedded ? (
    content
  ) : (
    <Card className="rounded-xl border-slate-200 p-0 shadow-sm">
      {content}
    </Card>
  );
};
